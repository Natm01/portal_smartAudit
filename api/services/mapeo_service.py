import logging
from typing import Dict, Any, Optional

from services.storage.temp_file_manager import get_temp_file_manager
from services.storage.azure_storage_service import get_azure_storage_service
from services.report_service import get_report_service
from utils.serialization import convert_numpy_types

logger = logging.getLogger(__name__)


class MapeoService:
    """Clean mapeo service orchestrating the mapping process"""
    
    def __init__(self):
        self.temp_manager = get_temp_file_manager()
        self.azure_service = get_azure_storage_service()
        self.report_service = get_report_service()
        
        self.standard_fields = [
            'journal_entry_id', 'line_number', 'description', 'line_description',
            'posting_date', 'fiscal_year', 'period_number', 'gl_account_number',
            'amount', 'debit_amount', 'credit_amount', 'debit_credit_indicator',
            'prepared_by', 'entry_date', 'entry_time', 'gl_account_name', 'vendor_id'
        ]
    
    async def run_mapeo(self, azure_file_path: str, execution_id: str, 
                       erp_hint: str = None) -> Dict[str, Any]:
        """Run complete mapeo process with clean separation"""
        try:
            logger.info(f"Starting mapeo for file: {azure_file_path}")
            
            with self.temp_manager.get_local_file(azure_file_path) as local_file:
                # Run automatic mapeo on local file
                mapeo_result = self._run_automatic_mapeo_process(local_file, erp_hint, execution_id)
                
                if not mapeo_result.get('success', False):
                    raise RuntimeError(f"Automatic mapeo failed: {mapeo_result.get('error', 'Unknown error')}")
                
                # Analyze mapping completeness
                completeness_analysis = self._analyze_mapping_completeness(local_file, mapeo_result)
                
                # Update result with completeness analysis
                mapeo_result.update({
                    'manual_mapping_required': completeness_analysis['manual_mapping_required'],
                    'unmapped_fields_count': completeness_analysis['unmapped_count'],
                    'unmapped_analysis': completeness_analysis
                })
                
                # Upload results to Azure
                azure_result = await self._upload_mapeo_results(mapeo_result, execution_id)
                
                logger.info(f"Mapeo completed - Manual mapping required: {azure_result['manual_mapping_required']}")
                
                return convert_numpy_types(azure_result)
                
        except Exception as e:
            logger.error(f"Error in mapeo process: {e}")
            return {
                'success': False,
                'error': str(e),
                'manual_mapping_required': False,
                'unmapped_fields_count': 0
            }
    
    def _run_automatic_mapeo_process(self, local_file_path: str, erp_hint: str, 
                                   execution_id: str) -> Dict[str, Any]:
        """Run automatic mapeo using clean process"""
        try:
            from procesos_mapeo.process_column import run_automatic_mapeo_clean
            
            result = run_automatic_mapeo_clean(local_file_path, erp_hint, execution_id)
            return result
            
        except Exception as e:
            logger.error(f"Error in automatic mapeo process: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_mapping_completeness(self, local_file_path: str, 
                                    mapeo_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze which fields are unmapped and require manual intervention"""
        try:
            import pandas as pd
            
            df = pd.read_csv(local_file_path)
            all_columns = set(df.columns)
            
            user_decisions = mapeo_result.get('user_decisions', {})
            mapped_columns = set(user_decisions.keys())
            
            unmapped_columns = all_columns - mapped_columns
            
            mapped_fields = set()
            for decision in user_decisions.values():
                mapped_fields.add(decision['field_type'])
            
            unmapped_standard_fields = set(self.standard_fields) - mapped_fields
            
            has_unmapped_fields = len(unmapped_columns) > 0
            
            confidence_stats = self._calculate_confidence_stats(user_decisions)
            
            critical_fields = {'journal_entry_id', 'amount', 'posting_date'}
            missing_critical = critical_fields - mapped_fields
            low_confidence = confidence_stats['average_confidence'] < 0.7
            
            manual_mapping_required = (
                has_unmapped_fields or 
                len(missing_critical) > 0 or
                low_confidence
            )
            
            analysis = {
                'has_unmapped_fields': has_unmapped_fields,
                'unmapped_count': len(unmapped_columns),
                'unmapped_columns': list(unmapped_columns),
                'unmapped_standard_fields': list(unmapped_standard_fields),
                'mapped_columns_count': len(mapped_columns),
                'mapped_fields_count': len(mapped_fields),
                'missing_critical_fields': list(missing_critical),
                'confidence_stats': confidence_stats,
                'manual_mapping_required': manual_mapping_required,
                'reasons_for_manual': []
            }
            
            if has_unmapped_fields:
                analysis['reasons_for_manual'].append(f"{len(unmapped_columns)} columns unmapped")
            if missing_critical:
                analysis['reasons_for_manual'].append(f"Missing critical fields: {missing_critical}")
            if low_confidence:
                analysis['reasons_for_manual'].append(f"Low average confidence: {confidence_stats['average_confidence']:.2f}")
            
            logger.info(f"Mapping analysis - Manual required: {manual_mapping_required}, Reasons: {analysis['reasons_for_manual']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing mapping completeness: {e}")
            return {
                'has_unmapped_fields': False,
                'unmapped_count': 0,
                'manual_mapping_required': False,
                'error': str(e)
            }
    
    def _calculate_confidence_stats(self, user_decisions: Dict) -> Dict[str, float]:
        """Calculate confidence statistics from user decisions"""
        if not user_decisions:
            return {
                'average_confidence': 0.0,
                'min_confidence': 0.0,
                'max_confidence': 0.0,
                'low_confidence_count': 0
            }
        
        confidences = [decision.get('confidence', 0.0) for decision in user_decisions.values()]
        
        return {
            'average_confidence': sum(confidences) / len(confidences),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences),
            'low_confidence_count': sum(1 for c in confidences if c < 0.7)
        }
    
    async def _upload_mapeo_results(self, mapeo_result: Dict[str, Any], 
                                  execution_id: str) -> Dict[str, Any]:
        """Upload mapeo result files to Azure Storage"""
        try:
            updated_result = mapeo_result.copy()
            
            # Upload header file if local
            if mapeo_result.get('header_file') and not mapeo_result['header_file'].startswith('azure://'):
                local_header = mapeo_result['header_file']
                try:
                    with open(local_header, 'rb') as f:
                        header_content = f.read()
                    
                    azure_header_path = self.azure_service.upload_from_memory(
                        header_content,
                        f"mapeo_header_{execution_id}.csv",
                        container_type="mapeos",
                        execution_id=execution_id
                    )
                    updated_result['header_file'] = azure_header_path
                    logger.info(f"Uploaded header to Azure: {azure_header_path}")
                except Exception as e:
                    logger.warning(f"Could not upload header file: {e}")
            
            # Upload detail file if local
            if mapeo_result.get('detail_file') and not mapeo_result['detail_file'].startswith('azure://'):
                local_detail = mapeo_result['detail_file']
                try:
                    with open(local_detail, 'rb') as f:
                        detail_content = f.read()
                    
                    azure_detail_path = self.azure_service.upload_from_memory(
                        detail_content,
                        f"mapeo_detail_{execution_id}.csv",
                        container_type="mapeos",
                        execution_id=execution_id
                    )
                    updated_result['detail_file'] = azure_detail_path
                    logger.info(f"Uploaded detail to Azure: {azure_detail_path}")
                except Exception as e:
                    logger.warning(f"Could not upload detail file: {e}")
            
            # Generate and upload report
            try:
                azure_report_path = await self.report_service.generate_mapeo_report(
                    updated_result, execution_id
                )
                updated_result['report_file'] = azure_report_path
            except Exception as e:
                logger.warning(f"Could not generate report: {e}")
            
            return updated_result
            
        except Exception as e:
            logger.error(f"Error uploading mapeo results to Azure: {e}")
            return mapeo_result
    
    def get_unmapped_fields_analysis(self, azure_file_path: str, 
                                   mapeo_results: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed analysis of unmapped fields for manual mapping"""
        try:
            logger.info(f"Getting unmapped fields analysis for: {azure_file_path}")
            
            with self.temp_manager.get_local_file(azure_file_path) as local_file:
                return self._analyze_unmapped_fields(local_file, mapeo_results)
                
        except Exception as e:
            logger.error(f"Error in unmapped fields analysis: {e}")
            return {
                'unmapped_fields': [],
                'available_standard_fields': [],
                'total_unmapped': 0,
                'total_available_fields': 0,
                'error': str(e)
            }
    
    def _analyze_unmapped_fields(self, local_file_path: str, 
                               mapeo_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze unmapped fields with suggestions"""
        import pandas as pd
        
        df = pd.read_csv(local_file_path)
        
        user_decisions = mapeo_results.get('user_decisions', {})
        mapped_columns = set(user_decisions.keys())
        mapped_fields = set(decision['field_type'] for decision in user_decisions.values())
        
        all_columns = set(df.columns)
        unmapped_columns = all_columns - mapped_columns
        
        unmapped_fields = []
        for column in unmapped_columns:
            sample_data = df[column].dropna().head(5).astype(str).tolist()
            data_type = self._analyze_column_type(df[column])
            suggestions = self._get_field_suggestions(column, df[column], mapped_fields)
            
            # Convert NumPy types to Python native types
            total_values = int(len(df[column]))
            non_null_values = int(df[column].count())
            unique_values = int(df[column].nunique())
            
            unmapped_fields.append({
                'column_name': column,
                'sample_data': sample_data,
                'data_type': data_type,
                'suggestions': suggestions,
                'total_values': total_values,
                'non_null_values': non_null_values,
                'unique_values': unique_values
            })
        
        available_fields = [field for field in self.standard_fields if field not in mapped_fields]
        
        analysis = {
            'unmapped_fields': unmapped_fields,
            'available_standard_fields': available_fields,
            'total_unmapped': len(unmapped_fields),
            'total_available_fields': len(available_fields)
        }
        
        logger.info(f"Analysis complete - {len(unmapped_fields)} unmapped fields found")
        return analysis
    
    def _analyze_column_type(self, series) -> str:
        """Analyze column data type for better suggestions"""
        import pandas as pd
        import re
        
        clean_series = series.dropna()
        if len(clean_series) == 0:
            return "empty"
        
        # Try to convert to numeric
        try:
            numeric_series = pd.to_numeric(clean_series, errors='coerce')
            numeric_ratio = len(numeric_series.dropna()) / len(clean_series)
            
            if numeric_ratio > 0.8:
                if numeric_series.std() > 1 and abs(numeric_series.mean()) > 1:
                    return "monetary"
                elif numeric_series.max() <= 1000 and numeric_series.min() >= 1:
                    return "sequential"
                else:
                    return "numeric"
        except:
            pass
        
        # Check for dates
        str_series = clean_series.astype(str)
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}\.\d{2}\.\d{4}',
        ]
        
        date_like_count = 0
        for value in str_series.head(10):
            if any(re.search(pattern, str(value)) for pattern in date_patterns):
                date_like_count += 1
        
        if date_like_count > len(str_series.head(10)) * 0.7:
            return "date"
        
        # Check average length
        avg_length = str_series.str.len().mean()
        if avg_length > 20:
            return "long_text"
        elif avg_length > 5:
            return "short_text"
        else:
            return "code"
    
    def _get_field_suggestions(self, column_name: str, series, mapped_fields: set):
        """Get field suggestions based on column name and data analysis"""
        available_fields = [field for field in self.standard_fields if field not in mapped_fields]
        
        column_lower = column_name.lower()
        data_type = self._analyze_column_type(series)
        suggestions = []
        
        # Name-based suggestions
        name_mapping = {
            'asiento': ['journal_entry_id'],
            'linea': ['line_number'],
            'descripcion': ['description', 'line_description'],
            'concepto': ['description', 'line_description'],
            'fecha': ['posting_date', 'entry_date'],
            'ano': ['fiscal_year'],
            'periodo': ['period_number'],
            'cuenta': ['gl_account_number'],
            'nombre': ['gl_account_name'],
            'importe': ['amount'],
            'debe': ['debit_amount'],
            'haber': ['credit_amount'],
            'saldo': ['amount'],
            'usuario': ['prepared_by'],
            'proveedor': ['vendor_id'],
            'tercero': ['vendor_id']
        }
        
        # Find name-based matches
        for pattern, fields in name_mapping.items():
            if pattern in column_lower:
                suggestions.extend([
                    {'field': f, 'reason': 'name_match', 'confidence': 0.8}
                    for f in fields if f in available_fields
                ])
        
        # Data type-based suggestions
        type_mapping = {
            'monetary': ['amount', 'debit_amount', 'credit_amount'],
            'sequential': ['line_number', 'period_number'],
            'numeric': ['journal_entry_id', 'fiscal_year', 'gl_account_number', 'vendor_id'],
            'date': ['posting_date', 'entry_date'],
            'long_text': ['description', 'line_description', 'gl_account_name'],
            'short_text': ['prepared_by', 'debit_credit_indicator'],
            'code': ['gl_account_number', 'vendor_id']
        }
        
        if data_type in type_mapping:
            suggestions.extend([
                {'field': f, 'reason': 'data_type_match', 'confidence': 0.6}
                for f in type_mapping[data_type] if f in available_fields
            ])
        
        # Remove duplicates and limit to top 3
        seen = set()
        unique_suggestions = []
        for item in suggestions:
            if item['field'] not in seen:
                seen.add(item['field'])
                unique_suggestions.append(item)
        
        return unique_suggestions[:3]


_mapeo_service = None

def get_mapeo_service() -> MapeoService:
    """Get global mapeo service instance"""
    global _mapeo_service
    if _mapeo_service is None:
        _mapeo_service = MapeoService()
    return _mapeo_service