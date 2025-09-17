# procesos_mapeo/csv_transformer.py
import pandas as pd
import tempfile
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from procesos_mapeo.accounting_data_processor import AccountingDataProcessor

logger = logging.getLogger(__name__)

class CSVTransformer:
    """Clean CSV transformer working only with local files"""
    
    def __init__(self, output_prefix: str = "transformed", sort_by_journal_id: bool = True,
                 apply_numeric_processing: bool = True):
        self.output_prefix = output_prefix
        self.sort_by_journal_id = sort_by_journal_id
        self.apply_numeric_processing = apply_numeric_processing
        
        self.accounting_processor = AccountingDataProcessor()
        
        self.transformation_stats = {
            'original_columns': 0,
            'transformed_columns': 0,
            'header_columns': 0,
            'detail_columns': 0,
            'rows_processed': 0,
            'numeric_processing_applied': False,
            'numeric_fields_processed': 0
        }
    
    def create_header_detail_csvs(self, df: pd.DataFrame, user_decisions: Dict, 
                                 standard_fields: List[str]) -> Dict[str, Any]:
        """Creates separate header and detail CSV files with integrated numeric processing"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            self.transformation_stats['original_columns'] = len(df.columns)
            self.transformation_stats['rows_processed'] = len(df)
            
            transformed_df = df.copy()
            column_mapping = {}
            
            for column_name, decision in user_decisions.items():
                standard_field = decision['field_type']
                column_mapping[column_name] = standard_field
            
            transformed_df = transformed_df.rename(columns=column_mapping)
            
            if self.apply_numeric_processing:
                transformed_df, numeric_stats = self._apply_numeric_processing(transformed_df)
                self.transformation_stats['numeric_processing_applied'] = True
                self.transformation_stats['numeric_fields_processed'] = numeric_stats.get('fields_cleaned', 0)
            
            transformed_df = self.accounting_processor.separate_datetime_fields(transformed_df)
            
            if self.sort_by_journal_id and 'journal_entry_id' in transformed_df.columns:
                try:
                    transformed_df = transformed_df.sort_values('journal_entry_id', ascending=True)
                except TypeError:
                    transformed_df['journal_entry_id'] = transformed_df['journal_entry_id'].astype(str)
                    transformed_df = transformed_df.sort_values('journal_entry_id', ascending=True)
            
            header_field_definitions = [
                'journal_entry_id', 'posting_date', 'fiscal_year', 'period_number', 
                'prepared_by', 'entry_date', 'entry_time', 'description'
            ]
            
            detail_field_definitions = [
                'journal_entry_id', 'line_number', 'line_description', 
                'gl_account_number', 'gl_account_name', 'amount', 'debit_amount', 
                'credit_amount', 'debit_credit_indicator', 'vendor_id'
            ]
            
            available_header_fields = [field for field in header_field_definitions 
                                     if field in transformed_df.columns]
            available_detail_fields = [field for field in detail_field_definitions 
                                     if field in transformed_df.columns]
            
            header_file = self._create_header_csv(transformed_df, available_header_fields, timestamp)
            detail_file = self._create_detail_csv(transformed_df, available_detail_fields, timestamp)
            
            self.transformation_stats['transformed_columns'] = len(column_mapping)
            self.transformation_stats['header_columns'] = len(available_header_fields)
            self.transformation_stats['detail_columns'] = len(available_detail_fields)
            
            result = {
                'success': True,
                'header_file': header_file,
                'detail_file': detail_file,
                'header_columns': available_header_fields,
                'detail_columns': available_detail_fields,
                'transformation_stats': self.transformation_stats,
                'total_standard_fields_mapped': len(user_decisions),
                'unmapped_standard_fields': [
                    f for f in standard_fields 
                    if f not in [d['field_type'] for d in user_decisions.values()]
                ],
                'numeric_processing_stats': getattr(self, '_last_numeric_stats', {})
            }
            
            self._show_transformation_summary(result)
            return result
            
        except Exception as e:
            logger.error(f"Error in CSV transformation: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_header_csv(self, df: pd.DataFrame, header_fields: List[str], timestamp: str) -> Optional[str]:
        """Creates header CSV file"""
        if not header_fields:
            return None
        
        if 'journal_entry_id' in header_fields and 'journal_entry_id' in df.columns:
            header_df = df[header_fields].drop_duplicates(subset=['journal_entry_id'])
            
            if self.sort_by_journal_id:
                header_df = header_df.sort_values('journal_entry_id', ascending=True)
        else:
            header_df = df[header_fields].copy()
        
        header_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv').name
        header_df.to_csv(header_file, index=False, encoding='utf-8')
        
        logger.info(f"Header CSV created: {header_file}")
        return header_file
    
    def _create_detail_csv(self, df: pd.DataFrame, detail_fields: List[str], timestamp: str) -> Optional[str]:
        """Creates detail CSV file"""
        if not detail_fields:
            return None
        
        detail_df = df[detail_fields].copy()
        
        if self.sort_by_journal_id and 'journal_entry_id' in detail_df.columns:
            detail_df = detail_df.sort_values('journal_entry_id', ascending=True)
        
        detail_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv').name
        detail_df.to_csv(detail_file, index=False, encoding='utf-8')
        
        logger.info(f"Detail CSV created: {detail_file}")
        return detail_file
    
    def _apply_numeric_processing(self, df: pd.DataFrame):
        """Applies numeric processing using AccountingDataProcessor"""
        potential_numeric_fields = [
            'amount', 'debit_amount', 'credit_amount', 'line_number',
            'fiscal_year', 'period_number', 'gl_account_number'
        ]
        
        available_numeric_fields = [field for field in potential_numeric_fields 
                                  if field in df.columns]
        
        if not available_numeric_fields:
            return df, {}
        
        processed_df, processing_stats = self.accounting_processor.process_numeric_fields_and_calculate_amounts(df)
        
        self._last_numeric_stats = processing_stats
        
        return processed_df, processing_stats
    
    def _show_transformation_summary(self, result: Dict[str, Any]):
        """Shows transformation summary with numeric statistics"""
        stats = result['transformation_stats']
        
        if stats['numeric_processing_applied']:
            numeric_stats = result.get('numeric_processing_stats', {})
        
        files_created = 0
        if result.get('header_file'):
            files_created += 1
        if result.get('detail_file'):
            files_created += 1
        
        logger.info(f"Transformation completed: {files_created} files created")
    
    def create_single_transformed_csv(self, df: pd.DataFrame, user_decisions: Dict, 
                                    suffix: str = "transformed", execution_id: str = None) -> Dict[str, Any]:
        """Creates a single transformed CSV with numeric cleaning"""
        try:
            column_mapping = {col: decision['field_type'] for col, decision in user_decisions.items()}
            
            transformed_df = df.rename(columns=column_mapping)
            
            if self.apply_numeric_processing:
                transformed_df, numeric_stats = self._apply_numeric_processing(transformed_df)
                numeric_processing_applied = True
            else:
                numeric_stats = {}
                numeric_processing_applied = False
            
            if self.sort_by_journal_id and 'journal_entry_id' in transformed_df.columns:
                transformed_df = transformed_df.sort_values('journal_entry_id').reset_index(drop=True)
            
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv').name
            transformed_df.to_csv(output_file, index=False, encoding='utf-8')
            
            result = {
                'success': True,
                'output_file': output_file,
                'rows': len(transformed_df),
                'columns': len(transformed_df.columns),
                'mapped_fields': len(user_decisions),
                'numeric_processing_applied': numeric_processing_applied,
                'numeric_processing_stats': numeric_stats
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating single transformed CSV: {e}")
            return {'success': False, 'error': str(e)}