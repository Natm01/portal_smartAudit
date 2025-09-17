import os
import pandas as pd
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from procesos_mapeo.csv_transformer import CSVTransformer
from procesos_mapeo.balance_validator import BalanceValidator
from procesos_mapeo.comprehensive_reporter import get_comprehensive_reporter
from services.storage.temp_file_manager import get_temp_file_manager
from services.storage.azure_storage_service import get_azure_storage_service
from services.report_service import get_report_service
from utils.serialization import convert_numpy_types

logger = logging.getLogger(__name__)


class ManualMappingService:
    """Clean manual mapping service with separated Azure operations"""
    
    def __init__(self):
        self.standard_fields = [
            'journal_entry_id', 'line_number', 'description', 'line_description',
            'posting_date', 'fiscal_year', 'period_number', 'gl_account_number',
            'amount', 'debit_amount', 'credit_amount', 'debit_credit_indicator',
            'prepared_by', 'entry_date', 'entry_time', 'gl_account_name', 'vendor_id'
        ]
        self.temp_manager = get_temp_file_manager()
        self.azure_service = get_azure_storage_service()
        self.report_service = get_report_service()
    
    def get_unmapped_fields_analysis(self, azure_csv_file: str, mapeo_results: Dict) -> Dict[str, Any]:
        """Analyze unmapped fields and provide suggestions"""
        try:
            logger.info(f"Getting unmapped fields analysis for: {azure_csv_file}")
            
            with self.temp_manager.get_local_file(azure_csv_file) as local_csv_path:
                return self._analyze_unmapped_fields_local(local_csv_path, mapeo_results)
                
        except Exception as e:
            logger.error(f"Error in unmapped fields analysis: {e}")
            return {
                'unmapped_fields': [],
                'available_standard_fields': [],
                'total_unmapped': 0,
                'total_available_fields': 0,
                'error': str(e)
            }
    
    async def apply_manual_mappings(self, execution_id: str, azure_csv_file: str, 
                            original_mapeo_results: Dict, manual_mappings: List[Dict]) -> Dict[str, Any]:
        """Apply manual mappings and regenerate reports"""
        try:
            logger.info(f"Applying manual mappings for execution: {execution_id}")
            
            with self.temp_manager.get_local_file(azure_csv_file) as local_csv_path:
                # Process mappings locally
                updated_results = self._process_manual_mappings_local(
                    local_csv_path, original_mapeo_results, manual_mappings
                )
                
                # Upload results to Azure
                azure_results = await self._upload_manual_mapping_results(
                    updated_results, execution_id
                )
                
                return convert_numpy_types(azure_results)
                
        except Exception as e:
            logger.error(f"Error applying manual mappings: {e}")
            raise Exception(f"Manual mapping failed: {str(e)}")
    
    def _analyze_unmapped_fields_local(self, local_csv_path: str, mapeo_results: Dict) -> Dict[str, Any]:
        """Analyze unmapped fields on local file"""
        df = pd.read_csv(local_csv_path)
        
        user_decisions = mapeo_results.get('user_decisions', {})
        mapped_columns = set(user_decisions.keys())
        mapped_fields = set(decision['field_type'] for decision in user_decisions.values())
        
        all_columns = set(df.columns)
        unmapped_columns = all_columns - mapped_columns
        
        unmapped_fields = []
        for column in unmapped_columns:
            analysis = self._analyze_unmapped_column(column, df[column], mapped_fields)
            unmapped_fields.append(analysis)
        
        available_fields = [field for field in self.standard_fields if field not in mapped_fields]
        
        return {
            'unmapped_fields': unmapped_fields,
            'available_standard_fields': available_fields,
            'total_unmapped': len(unmapped_columns),
            'total_available_fields': len(available_fields)
        }
    
    def _analyze_unmapped_column(self, column_name: str, series: pd.Series, 
                               mapped_fields: set) -> Dict[str, Any]:
        """Analyze a single unmapped column"""
        sample_data = series.dropna().head(5).astype(str).tolist()
        data_type = self._analyze_column_type(series)
        suggestions = self._get_field_suggestions(column_name, series, mapped_fields)
        
        suggestion_details = []
        for suggestion in suggestions[:3]:
            confidence = self._calculate_suggestion_confidence(column_name, series, suggestion)
            justification = self._get_suggestion_justification(column_name, series, suggestion, data_type)
            
            suggestion_details.append({
                'field_type': suggestion,
                'confidence': confidence,
                'justification': justification
            })
        
        # Convert NumPy types to Python native types
        total_values = int(len(series))
        non_null_values = int(series.count())
        unique_values = int(series.nunique())
        
        return {
            'column_name': column_name,
            'sample_data': sample_data,
            'data_type': data_type,
            'suggestions': suggestion_details,
            'total_values': total_values,
            'non_null_values': non_null_values,
            'unique_values': unique_values
        }
    
    def _process_manual_mappings_local(self, local_csv_path: str, 
                                     original_mapeo_results: Dict, 
                                     manual_mappings: List[Dict]) -> Dict[str, Any]:
        """Process manual mappings on local file"""
        updated_results = original_mapeo_results.copy()
        current_decisions = updated_results.get('user_decisions', {}).copy()
        
        applied_mappings = {}
        validation_errors = []
        
        # Get already used fields
        used_fields = set(decision['field_type'] for decision in current_decisions.values())
        
        for mapping in manual_mappings:
            column_name = mapping['column_name']
            selected_field = mapping['selected_field']
            confidence = mapping.get('confidence', 0.8)
            
            # Validate field is not already used
            if selected_field in used_fields:
                validation_errors.append(
                    f"Field '{selected_field}' is already mapped to another column"
                )
                continue
            
            # Add new mapping decision
            current_decisions[column_name] = {
                'field_type': selected_field,
                'confidence': confidence,
                'decision_type': 'manual_mapping',
                'resolution_type': 'manual_selection'
            }
            
            applied_mappings[column_name] = selected_field
            used_fields.add(selected_field)
        
        if validation_errors:
            raise ValueError(f"Validation errors: {'; '.join(validation_errors)}")
        
        # Update user decisions
        updated_results['user_decisions'] = current_decisions
        
        # Update statistics
        mapeo_stats = updated_results.get('mapeo_stats', {})
        mapeo_stats['manual_mappings'] = mapeo_stats.get('manual_mappings', 0) + len(applied_mappings)
        mapeo_stats['columns_processed'] = mapeo_stats.get('columns_processed', 0) + len(applied_mappings)
        updated_results['mapeo_stats'] = mapeo_stats
        
        # Regenerate CSV files and reports with updated mappings
        regenerated_results = self._regenerate_outputs_local(local_csv_path, updated_results)
        updated_results.update(regenerated_results)
        
        # Add information about applied mappings
        updated_results['manual_mappings_applied'] = applied_mappings
        updated_results['manual_mapping_timestamp'] = datetime.now().isoformat()
        
        return updated_results
    
    def _regenerate_outputs_local(self, local_csv_path: str, updated_mapeo_results: Dict) -> Dict[str, Any]:
        """Regenerate CSV files and reports locally"""
        try:
            df = pd.read_csv(local_csv_path)
            user_decisions = updated_mapeo_results.get('user_decisions', {})
            
            # Create CSV files using transformer
            csv_transformer = CSVTransformer(
                output_prefix="updated_mapeo",
                apply_numeric_processing=True
            )
            csv_result = csv_transformer.create_header_detail_csvs(
                df, user_decisions, self.standard_fields
            )
            
            # Validate balance if possible
            balance_report = {}
            if csv_result.get('success') and csv_result.get('detail_file'):
                try:
                    detail_df = pd.read_csv(csv_result['detail_file'])
                    balance_validator = BalanceValidator()
                    balance_report = balance_validator.perform_comprehensive_balance_validation(detail_df)
                except Exception as e:
                    logger.warning(f"Balance validation failed: {e}")
                    balance_report = {'error': str(e)}
            
            # Generate updated report
            report_file = self._generate_updated_report_local(updated_mapeo_results, csv_result, balance_report)
            
            return {
                'header_file': csv_result.get('header_file'),
                'detail_file': csv_result.get('detail_file'),
                'header_columns': csv_result.get('header_columns', []),
                'detail_columns': csv_result.get('detail_columns', []),
                'balance_report': balance_report,
                'report_file': report_file,
                'regeneration_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error regenerating outputs: {e}")
            return {'regeneration_error': str(e)}
    
    def _generate_updated_report_local(self, mapeo_data: Dict, csv_result: Dict, 
                                     balance_report: Dict) -> Optional[str]:
        """Generate updated report locally"""
        try:
            reporter = get_comprehensive_reporter()
            
            # Prepare complete mapeo data
            complete_mapeo_data = {
                'mapeo_stats': mapeo_data.get('mapeo_stats', {}),
                'user_decisions': mapeo_data.get('user_decisions', {}),
                'balance_report': balance_report,
                'mapeo_mode': 'automatic_with_manual_completion',
                'standard_fields': self.standard_fields,
                **csv_result
            }
            
            # Generate report content
            report_content = reporter.generate_mapeo_report(complete_mapeo_data)
            
            # Save to temporary file
            import tempfile
            report_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8')
            report_file.write(report_content)
            report_file.close()
            
            logger.info(f"Report generated locally: {report_file.name}")
            return report_file.name
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return None
    
    async def _upload_manual_mapping_results(self, updated_results: Dict, 
                                           execution_id: str) -> Dict[str, Any]:
        """Upload manual mapping results to Azure"""
        try:
            azure_results = updated_results.copy()
            
            # Upload header file
            if updated_results.get('header_file'):
                header_file = updated_results['header_file']
                if os.path.exists(header_file):
                    with open(header_file, 'rb') as f:
                        header_content = f.read()
                    
                    azure_header_path = self.azure_service.upload_from_memory(
                        header_content,
                        f"manual_mapeo_header_{execution_id}.csv",
                        container_type="mapeos",
                        execution_id=execution_id
                    )
                    azure_results['header_file'] = azure_header_path
                    logger.info(f"Uploaded header to Azure: {azure_header_path}")
            
            # Upload detail file
            if updated_results.get('detail_file'):
                detail_file = updated_results['detail_file']
                if os.path.exists(detail_file):
                    with open(detail_file, 'rb') as f:
                        detail_content = f.read()
                    
                    azure_detail_path = self.azure_service.upload_from_memory(
                        detail_content,
                        f"manual_mapeo_detail_{execution_id}.csv",
                        container_type="mapeos",
                        execution_id=execution_id
                    )
                    azure_results['detail_file'] = azure_detail_path
                    logger.info(f"Uploaded detail to Azure: {azure_detail_path}")
            
            # Upload report
            if updated_results.get('report_file'):
                report_file = updated_results['report_file']
                if os.path.exists(report_file):
                    with open(report_file, 'rb') as f:
                        report_content = f.read()
                    
                    azure_report_path = self.azure_service.upload_from_memory(
                        report_content,
                        f"manual_mapeo_report_{execution_id}.txt",
                        container_type="mapeos",
                        execution_id=execution_id
                    )
                    azure_results['report_file'] = azure_report_path
                    logger.info(f"Uploaded report to Azure: {azure_report_path}")
            
            return azure_results
            
        except Exception as e:
            logger.error(f"Error uploading manual mapping results: {e}")
            return updated_results
    
    def _analyze_column_type(self, series: pd.Series) -> str:
        """Analyze column data type for better suggestions"""
        clean_series = series.dropna()
        if len(clean_series) == 0:
            return "empty"
        
        # Try to convert to numeric
        try:
            numeric_series = pd.to_numeric(clean_series, errors='coerce')
            numeric_series = numeric_series.dropna()
            
            if len(numeric_series) == 0:
                numeric_ratio = 0
            else:
                numeric_ratio = len(numeric_series) / len(clean_series)
            
            if numeric_ratio > 0.8 and len(numeric_series) > 0:
                std_val = numeric_series.std()
                mean_val = numeric_series.mean()
                max_val = numeric_series.max()
                min_val = numeric_series.min()
                
                # Handle potential NaN values in statistics
                if pd.isna(std_val):
                    std_val = 0
                if pd.isna(mean_val):
                    mean_val = 0
                
                # Check if it's monetary (has decimals or large values)
                if std_val > 1 and abs(mean_val) > 1:
                    return "monetary"
                # Check if it's sequential (like line numbers)
                elif max_val <= 1000 and min_val >= 1:
                    return "sequential"
                else:
                    return "numeric"
        except Exception:
            pass
        
        # Check for dates
        str_series = clean_series.astype(str)
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}\.\d{2}\.\d{4}',
        ]
        
        date_like_count = 0
        sample_size = min(10, len(str_series))
        for value in str_series.head(sample_size):
            if any(re.search(pattern, str(value)) for pattern in date_patterns):
                date_like_count += 1
        
        if sample_size > 0 and date_like_count > sample_size * 0.7:
            return "date"
        
        # Check average length for text classification
        avg_length = str_series.str.len().mean()
        
        # Handle potential NaN in average length
        if pd.isna(avg_length):
            avg_length = 0
        
        if avg_length > 20:
            return "long_text"
        elif avg_length > 5:
            return "short_text"
        else:
            return "text"
    
    def _get_field_suggestions(self, column_name: str, series: pd.Series, mapped_fields: set):
        """Get field suggestions based on column name and data analysis"""
        available_fields = [field for field in self.standard_fields if field not in mapped_fields]
        
        column_lower = column_name.lower()
        data_type = self._analyze_column_type(series)
        suggestions = []
        
        # Name-based patterns
        name_patterns = {
            r'asiento|journal': ['journal_entry_id'],
            r'linea|line': ['line_number'],
            r'descripcion|description|concepto': ['description', 'line_description'],
            r'fecha|date': ['posting_date', 'entry_date'],
            r'ano|year': ['fiscal_year'],
            r'periodo|period': ['period_number'],
            r'cuenta|account': ['gl_account_number', 'gl_account_name'],
            r'nombre|name': ['gl_account_name'],
            r'importe|amount|saldo': ['amount'],
            r'debe|debit': ['debit_amount'],
            r'haber|credit': ['credit_amount'],
            r'usuario|user|prepared': ['prepared_by'],
            r'proveedor|vendor|tercero': ['vendor_id'],
            r'tiempo|time|hora': ['entry_time']
        }
        
        for pattern, fields in name_patterns.items():
            if re.search(pattern, column_lower):
                suggestions.extend([f for f in fields if f in available_fields])
        
        # Content-based suggestions
        type_suggestions = {
            'monetary': ['amount', 'debit_amount', 'credit_amount'],
            'sequential': ['line_number', 'period_number'],
            'numeric': ['journal_entry_id', 'fiscal_year', 'gl_account_number', 'vendor_id'],
            'date': ['posting_date', 'entry_date'],
            'long_text': ['description', 'line_description', 'gl_account_name'],
            'short_text': ['prepared_by', 'debit_credit_indicator'],
            'text': ['gl_account_number', 'vendor_id']
        }
        
        if data_type in type_suggestions:
            suggestions.extend([f for f in type_suggestions[data_type] if f in available_fields])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for item in suggestions:
            if item not in seen:
                seen.add(item)
                unique_suggestions.append(item)
        
        return unique_suggestions
    
    def _calculate_suggestion_confidence(self, column_name: str, series: pd.Series, 
                                       field_type: str) -> float:
        """Calculate confidence score for a field suggestion"""
        confidence = 0.5  # Base confidence
        
        column_lower = column_name.lower()
        data_type = self._analyze_column_type(series)
        
        # Name matching boost
        name_boosts = {
            'journal_entry_id': ['asiento', 'journal'],
            'line_number': ['linea', 'line'],
            'description': ['descripcion', 'description', 'concepto'],
            'posting_date': ['fecha', 'date'],
            'fiscal_year': ['ano', 'year'],
            'amount': ['importe', 'amount', 'saldo'],
            'debit_amount': ['debe', 'debit'],
            'credit_amount': ['haber', 'credit'],
            'gl_account_number': ['cuenta', 'account'],
            'gl_account_name': ['nombre', 'name'],
            'prepared_by': ['usuario', 'user', 'prepared'],
            'vendor_id': ['proveedor', 'vendor', 'tercero']
        }
        
        if field_type in name_boosts:
            for keyword in name_boosts[field_type]:
                if keyword in column_lower:
                    confidence += 0.3
                    break
        
        # Data type matching boost
        type_matches = {
            'monetary': ['amount', 'debit_amount', 'credit_amount'],
            'sequential': ['line_number'],
            'numeric': ['journal_entry_id', 'fiscal_year', 'gl_account_number'],
            'date': ['posting_date', 'entry_date'],
            'long_text': ['description', 'line_description', 'gl_account_name']
        }
        
        if data_type in type_matches and field_type in type_matches[data_type]:
            confidence += 0.2
        
        return min(confidence, 0.95)
    
    def _get_suggestion_justification(self, column_name: str, series: pd.Series, 
                                    field_type: str, data_type: str) -> str:
        """Get justification for a field suggestion"""
        sample_str = ', '.join(str(x) for x in series.dropna().head(3).tolist())
        
        justifications = {
            'journal_entry_id': f"Numeric pattern suitable for journal IDs: {sample_str}",
            'line_number': f"Sequential numeric pattern: {sample_str}",
            'description': f"Text content suitable for descriptions: {sample_str}",
            'line_description': f"Detailed text content: {sample_str}",
            'posting_date': f"Date format detected: {sample_str}",
            'entry_date': f"Date format detected: {sample_str}",
            'fiscal_year': f"Year format detected: {sample_str}",
            'period_number': f"Numeric period pattern: {sample_str}",
            'gl_account_number': f"Account code format: {sample_str}",
            'gl_account_name': f"Account description text: {sample_str}",
            'amount': f"Monetary values detected: {sample_str}",
            'debit_amount': f"Debit amount pattern: {sample_str}",
            'credit_amount': f"Credit amount pattern: {sample_str}",
            'prepared_by': f"User identifier format: {sample_str}",
            'vendor_id': f"Vendor code format: {sample_str}",
            'entry_time': f"Time format detected: {sample_str}"
        }
        
        base_justification = justifications.get(field_type, f"Content analysis: {sample_str}")
        
        # Add data type info
        if data_type != "empty":
            base_justification += f" ({data_type} data)"
        
        return base_justification


_manual_mapping_service: Optional[ManualMappingService] = None


def get_manual_mapping_service() -> ManualMappingService:
    """Get global manual mapping service instance"""
    global _manual_mapping_service
    if _manual_mapping_service is None:
        _manual_mapping_service = ManualMappingService()
    return _manual_mapping_service