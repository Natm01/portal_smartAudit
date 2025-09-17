import pandas as pd
import os
import logging
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime

from procesos_mapeo.accounting_data_processor import AccountingDataProcessor
from procesos_mapeo.balance_validator import BalanceValidator
from procesos_mapeo.csv_transformer import CSVTransformer
from procesos_mapeo.comprehensive_reporter import get_comprehensive_reporter

logger = logging.getLogger(__name__)


class AutomaticMapeoSession:
    """Clean automatic mapeo session working only with local files"""
    
    def __init__(self, local_csv_file: str, erp_hint: str = None, execution_id: str = None):
        self.csv_file = local_csv_file
        self.erp_hint = erp_hint
        self.execution_id = execution_id
        self.df = None
        self.mapper = None
        self.detector = None
        
        # Standard accounting fields
        self.standard_fields = [
            'journal_entry_id', 'line_number', 'description', 'line_description',
            'posting_date', 'fiscal_year', 'period_number', 'gl_account_number',
            'amount', 'debit_amount', 'credit_amount', 'debit_credit_indicator',
            'prepared_by', 'entry_date', 'entry_time', 'gl_account_name', 'vendor_id'
        ]
        
        # Initialize statistics
        self.mapeo_stats = {
            'columns_processed': 0,
            'automatic_mappings': 0,
            'conflicts_resolved': 0,
            'high_confidence_mappings': 0,
            'low_confidence_mappings': 0,
            'rejected_low_confidence': 0,
            'unmapped_columns': 0,
            'manual_mappings': 0
        }
        
        # Confidence threshold
        self.confidence_threshold = 0.75
        
        # Results storage
        self.user_decisions = {}
        self.conflict_resolutions = {}
        
        # Initialize components
        self.data_processor = AccountingDataProcessor()
        self.balance_validator = BalanceValidator()
        self.csv_transformer = CSVTransformer(output_prefix="automatic_mapeo")
        self.reporter = get_comprehensive_reporter()
    
    def initialize(self) -> bool:
        """Initialize the mapeo session"""
        try:
            if not os.path.exists(self.csv_file):
                logger.error(f"CSV file not found: {self.csv_file}")
                return False
            
            # Load CSV data
            self.df = pd.read_csv(self.csv_file)
            logger.info(f"Loaded CSV with {len(self.df.columns)} columns")
            
            # Initialize field mapper and detector
            try:
                from procesos_mapeo.field_mapper import FieldMapper
                from procesos_mapeo.field_detector import FieldDetector
                
                self.mapper = FieldMapper()
                self.mapper.set_sample_dataframe(self.df)
                self.detector = FieldDetector()
                
                # Enable balance validation if available
                if hasattr(self.mapper, 'set_dataframe_for_balance_validation'):
                    self.mapper.set_dataframe_for_balance_validation(self.df)
                    self.mapeo_stats['balance_validation_enabled'] = True
                
            except ImportError as e:
                logger.error(f"Error importing mapper modules: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing mapeo session: {e}")
            return False
    
    def run_automatic_mapeo(self) -> Dict:
        """Run automatic mapeo process with comprehensive reporting"""
        try:
            logger.info(f"Starting automatic mapeo for {len(self.df.columns)} columns")
            
            # Step 1: Perform field detection
            field_analysis = self._perform_field_detection()
            if not field_analysis['success']:
                return {
                    'success': False,
                    'error': field_analysis.get('error'),
                    'manual_mapping_required': True,
                    'unmapped_fields_count': len(self.df.columns)
                }
            
            initial_mappings = field_analysis['mappings']
            logger.info(f"Initial field detection found {len(initial_mappings)} mappings")
            
            # Step 2: Apply confidence filtering with tracking
            accepted_mappings, rejected_mappings = self._apply_confidence_filter_with_tracking(initial_mappings)
            logger.info(f"Confidence filter - Accepted: {len(accepted_mappings)}, Rejected: {len(rejected_mappings)}")
            
            # Step 3: Update user decisions
            self._update_user_decisions_from_mappings(accepted_mappings)
            
            # Step 4: Calculate comprehensive statistics
            self._calculate_comprehensive_statistics()
            
            # Step 5: Apply additional validations
            self._apply_additional_validations()
            
            # Step 6: Process numeric fields and calculate amounts
            processing_stats = self._process_numeric_fields()
            self.mapeo_stats.update(processing_stats)
            
            # Step 7: Perform balance validation
            balance_report = self._perform_balance_validation()
            
            # Step 8: Create output files
            csv_result = self._create_output_files()
            
            # Step 9: Generate comprehensive report
            report_content = self._generate_comprehensive_report(csv_result, balance_report, rejected_mappings)
            
            # Step 10: Prepare final result
            result = self._prepare_final_result(csv_result, report_content, balance_report, rejected_mappings)
            
            logger.info(f"Mapeo completed - Manual mapping required: {result.get('manual_mapping_required')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in automatic mapeo: {e}")
            return {
                'success': False,
                'error': str(e),
                'manual_mapping_required': True,
                'unmapped_fields_count': len(self.df.columns) if self.df is not None else 0
            }
    
    def _perform_field_detection(self) -> Dict:
        """Perform automatic field detection"""
        try:
            final_mappings = self.mapper.map_all_columns_with_conflict_resolution(
                df=self.df,
                erp_hint=self.erp_hint,
                balance_validator=self.balance_validator
            )
            
            return {
                'success': True,
                'mappings': final_mappings
            }
            
        except Exception as e:
            logger.error(f"Error in field detection: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _apply_confidence_filter_with_tracking(self, mappings: Dict):
        """Apply confidence threshold filtering with detailed tracking"""
        accepted = {}
        rejected = {}
        
        for column, mapping_info in mappings.items():
            confidence = mapping_info.get('confidence', 0.0)
            
            if confidence >= self.confidence_threshold:
                accepted[column] = mapping_info
            else:
                rejected[column] = mapping_info
                logger.debug(f"Rejected mapping - {column} -> {mapping_info.get('field_type')} (confidence: {confidence:.3f})")
        
        return accepted, rejected
    
    def _update_user_decisions_from_mappings(self, mappings: Dict):
        """Update user decisions from accepted mappings"""
        conflicts_count = 0
        
        for column_name, mapping_info in mappings.items():
            field_type = mapping_info.get('field_type')
            confidence = mapping_info.get('confidence', 0.0)
            resolution_type = mapping_info.get('resolution_type', 'no_conflict')
            
            # Determine decision type
            if resolution_type == 'no_conflict':
                decision_type = 'automatic_no_conflict'
            else:
                decision_type = f'automatic_{resolution_type}'
                conflicts_count += 1
                
                # Store conflict resolution details
                self.conflict_resolutions[field_type] = {
                    'winner': column_name,
                    'resolution_type': resolution_type,
                    'all_candidates': [column_name]
                }
            
            # Store decision
            self.user_decisions[column_name] = {
                'field_type': field_type,
                'confidence': confidence,
                'decision_type': decision_type,
                'resolution_type': resolution_type
            }
        
        self.mapeo_stats['conflicts_resolved'] = conflicts_count
        logger.info(f"Created {len(self.user_decisions)} user decisions")
    
    def _calculate_comprehensive_statistics(self):
        """Calculate comprehensive mapping statistics"""
        total_columns = len(self.df.columns)
        mapped_columns = len(self.user_decisions)
        unmapped_columns = total_columns - mapped_columns
        
        # Update basic stats
        self.mapeo_stats.update({
            'columns_processed': total_columns,
            'automatic_mappings': mapped_columns,
            'unmapped_columns': unmapped_columns
        })
        
        # Calculate confidence distribution
        high_confidence = 0
        low_confidence = 0
        
        for decision in self.user_decisions.values():
            confidence = decision.get('confidence', 0.0)
            if confidence > 0.8:
                high_confidence += 1
            else:
                low_confidence += 1
        
        self.mapeo_stats.update({
            'high_confidence_mappings': high_confidence,
            'low_confidence_mappings': low_confidence,
            'rejected_low_confidence': total_columns - mapped_columns
        })
        
        logger.info(f"Statistics - Total: {total_columns}, Mapped: {mapped_columns}, Unmapped: {unmapped_columns}")
    
    def _apply_additional_validations(self):
        """Apply additional validation rules"""
        try:
            try:
                from config.custom_field_validators import check_single_date_same_year_pattern
                
                original_count = len(self.user_decisions)
                self.user_decisions = check_single_date_same_year_pattern(
                    self.user_decisions, 
                    self.df
                )
                
                changes = len(self.user_decisions) - original_count
                if changes > 0:
                    self.mapeo_stats['date_pattern_updates'] = changes
                    
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Error in additional validations: {e}")
                
        except Exception as e:
            logger.warning(f"Error applying additional validations: {e}")
    
    def _process_numeric_fields(self) -> Dict:
        """Process numeric fields and calculate amounts"""
        try:
            # Apply column mapping to get transformed DataFrame
            transformed_df = self.df.copy()
            column_mapping = {col: decision['field_type'] for col, decision in self.user_decisions.items()}
            transformed_df = transformed_df.rename(columns=column_mapping)
            
            # Process numeric fields
            if hasattr(self.data_processor, 'process_numeric_fields_and_calculate_amounts'):
                processed_df, processing_stats = self.data_processor.process_numeric_fields_and_calculate_amounts(transformed_df)
                return processing_stats
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error processing numeric fields: {e}")
            return {}
    
    def _perform_balance_validation(self) -> Dict:
        """Perform comprehensive balance validation"""
        try:
            # Apply column mapping
            transformed_df = self.df.copy()
            column_mapping = {col: decision['field_type'] for col, decision in self.user_decisions.items()}
            transformed_df = transformed_df.rename(columns=column_mapping)
            
            # Process numeric fields first
            if hasattr(self.data_processor, 'process_numeric_fields_and_calculate_amounts'):
                transformed_df, _ = self.data_processor.process_numeric_fields_and_calculate_amounts(transformed_df)
            
            # Perform balance validation if we have the required fields
            if self.balance_validator and 'journal_entry_id' in transformed_df.columns:
                balance_report = self.balance_validator.perform_comprehensive_balance_validation(transformed_df)
                return balance_report
            else:
                return {
                    'is_balanced': True,
                    'total_debit_sum': 0.0,
                    'total_credit_sum': 0.0,
                    'entries_count': 0,
                    'balanced_entries_count': 0,
                    'note': 'Balance validation not available - missing required fields'
                }
                
        except Exception as e:
            logger.error(f"Error in balance validation: {e}")
            return {
                'is_balanced': False,
                'error': str(e)
            }
    
    def _create_output_files(self) -> Dict:
        """Create output files using the CSV transformer"""
        try:
            result = self.csv_transformer.create_header_detail_csvs(
                self.df, 
                self.user_decisions, 
                self.standard_fields
            )
            
            if result.get('success'):
                return result
            else:
                return self._create_basic_csv_fallback()
            
        except Exception as e:
            logger.error(f"Error creating output files: {e}")
            return self._create_basic_csv_fallback()
    
    def _create_basic_csv_fallback(self) -> Dict:
        """Create basic CSV output as fallback"""
        try:
            file_suffix = self.execution_id if self.execution_id else datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Apply column mapping
            transformed_df = self.df.copy()
            column_mapping = {col: decision['field_type'] for col, decision in self.user_decisions.items()}
            transformed_df = transformed_df.rename(columns=column_mapping)
            
            # Create temporary files
            header_file = None
            detail_file = None
            
            # Define field groups
            header_fields = ['journal_entry_id', 'description', 'posting_date', 'fiscal_year', 'period_number']
            detail_fields = ['journal_entry_id', 'line_number', 'line_description', 'gl_account_number', 'amount', 'debit_amount', 'credit_amount']
            
            # Create header file
            available_header_cols = [col for col in header_fields if col in transformed_df.columns]
            if available_header_cols:
                header_df = transformed_df[available_header_cols].drop_duplicates()
                header_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv').name
                header_df.to_csv(header_file, index=False, encoding='utf-8')
            
            # Create detail file
            available_detail_cols = [col for col in detail_fields if col in transformed_df.columns]
            if available_detail_cols:
                detail_df = transformed_df[available_detail_cols]
                detail_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv').name
                detail_df.to_csv(detail_file, index=False, encoding='utf-8')
            
            return {
                'success': True,
                'header_file': header_file,
                'detail_file': detail_file,
                'header_columns': available_header_cols,
                'detail_columns': available_detail_cols
            }
            
        except Exception as e:
            logger.error(f"Error creating basic CSV: {e}")
            return {
                'success': False,
                'header_file': None,
                'detail_file': None
            }
    
    def _generate_comprehensive_report(self, csv_result: Dict, balance_report: Dict, 
                                     rejected_mappings: Dict) -> str:
        """Generate comprehensive report content"""
        try:
            logger.info("Generating comprehensive report")
            
            # Prepare mapeo data for the reporter
            mapeo_data = {
                'csv_file': self.csv_file,
                'erp_hint': self.erp_hint,
                'execution_id': self.execution_id,
                'mapeo_stats': self.mapeo_stats,
                'user_decisions': self.user_decisions,
                'conflict_resolutions': self.conflict_resolutions,
                'balance_report': balance_report,
                'mapeo_mode': 'automatic',
                'standard_fields': self.standard_fields,
                'confidence_threshold': self.confidence_threshold,
                'rejected_mappings': rejected_mappings,
                **csv_result
            }
            
            # Generate report content
            report_content = self.reporter.generate_mapeo_report(mapeo_data)
            
            # Save report to temporary file
            report_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8')
            report_file.write(report_content)
            report_file.close()
            
            logger.info(f"Report generated: {report_file.name}")
            return report_file.name
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return ""
    
    def _prepare_final_result(self, csv_result: Dict, report_file: str, 
                            balance_report: Dict, rejected_mappings: Dict) -> Dict:
        """Prepare comprehensive final result"""
        try:
            # Calculate unmapped statistics
            total_columns = len(self.df.columns)
            mapped_columns = len(self.user_decisions)
            unmapped_columns = total_columns - mapped_columns
            
            # Determine if manual mapping is required
            manual_mapping_required = unmapped_columns > 0
            
            # Check for missing critical fields
            mapped_fields = set(decision['field_type'] for decision in self.user_decisions.values())
            critical_fields = {'journal_entry_id', 'amount', 'posting_date'}
            missing_critical = critical_fields - mapped_fields
            
            if missing_critical:
                manual_mapping_required = True
                logger.info(f"Missing critical fields: {missing_critical}")
            
            # Check average confidence
            avg_confidence = 0.0
            if self.user_decisions:
                avg_confidence = sum(d['confidence'] for d in self.user_decisions.values()) / len(self.user_decisions)
                if avg_confidence < 0.6:
                    manual_mapping_required = True
                    logger.info(f"Low average confidence: {avg_confidence:.3f}")
            
            # Build comprehensive result
            result = {
                'success': True,
                'mapeo_stats': self.mapeo_stats,
                'user_decisions': self.user_decisions,
                'conflict_resolutions': self.conflict_resolutions,
                'balance_report': balance_report,
                'report_file': report_file,
                'manual_mapping_required': manual_mapping_required,
                'unmapped_fields_count': unmapped_columns,
                'average_confidence': avg_confidence,
                'missing_critical_fields': list(missing_critical),
                'rejected_mappings': rejected_mappings,
                'trainer_type': 'automatic'
            }
            
            # Add CSV file information
            result.update(csv_result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error preparing final result: {e}")
            return {
                'success': False,
                'error': str(e),
                'manual_mapping_required': True,
                'unmapped_fields_count': len(self.df.columns) if self.df is not None else 0
            }


def run_automatic_mapeo_clean(local_csv_file: str, erp_hint: str = None, 
                            execution_id: str = None) -> Dict:
    """Run automatic mapeo process with clean local file processing"""
    try:
        logger.info(f"Starting clean automatic mapeo for {local_csv_file}")
        
        # Create and initialize session
        session = AutomaticMapeoSession(local_csv_file, erp_hint, execution_id)
        
        if not session.initialize():
            return {
                'success': False,
                'error': 'Could not initialize automatic mapeo session',
                'manual_mapping_required': True,
                'unmapped_fields_count': 0
            }
        
        # Run mapeo process
        result = session.run_automatic_mapeo()
        
        logger.info(f"Clean mapeo completed - Success: {result.get('success')}")
        logger.info(f"Manual mapping required: {result.get('manual_mapping_required')}")
        logger.info(f"Unmapped fields count: {result.get('unmapped_fields_count')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Clean automatic mapeo failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'manual_mapping_required': True,
            'unmapped_fields_count': 0
        }