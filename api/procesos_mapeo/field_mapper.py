# procesos_mapeo/field_mapper.py

import re
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime
from collections import Counter

from .dynamic_field_loader import DynamicFieldLoader
from procesos_mapeo.balance_validator import BalanceValidator

logger = logging.getLogger(__name__)

class FieldMapper:
    """Enhanced field mapper with advanced detection logic and UNIQUE MAPPING"""
    
    def __init__(self, config_source: Union[str, Path] = None):
        self.config_source = config_source
        self.field_loader = DynamicFieldLoader(config_source)
        
        self._normalization_cache = {}
        self._mapping_cache = {}
        self._erp_synonyms_cache = {}
        self._content_analysis_cache = {}

        self._dataframe_for_balance = None
        self._balance_validator = None
        self._numeric_fields_prepared = False

        try:
            self._balance_validator = BalanceValidator(tolerance=0.01)
        except ImportError:
            self._balance_validator = None
        
        self._used_field_mappings = {}  # {field_type: column_name}
        self._column_mappings = {}      # {column_name: field_type}
        self._confidence_by_column = {} # {column_name: confidence}
        
        self.mapping_stats = {
            'total_mappings_requested': 0,
            'cache_hits': 0,
            'successful_mappings': 0,
            'failed_mappings': 0,
            'conflicts_resolved': 0,
            'content_analysis_used': 0,
            'unique_mapping_conflicts': 0,
            'header_forced_mappings': 0,
            'smart_reassignments': 0
        }
        
        self.accent_map = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u',
            'ñ': 'n', 'ç': 'c', 'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u'
        }
        
        self.translation_map = {
            'datum': 'fecha', 'betrag': 'importe', 'konto': 'cuenta', 'soll': 'debe', 'haben': 'haber',
            'kostenstelle': 'centro_coste', 'projekt': 'proyecto', 'waehrung': 'moneda',
            'buchung': 'asiento', 'beleg': 'documento', 'periode': 'periodo',
            'lieferant': 'proveedor', 'kontoname': 'nombre_cuenta',
            
            'date': 'fecha', 'montant': 'importe', 'compte': 'cuenta', 'debit': 'debe', 'credit': 'haber',
            'centre': 'centro', 'projet': 'proyecto', 'devise': 'moneda',
            'ecriture': 'asiento', 'document': 'documento', 'periode': 'periodo',
            'fournisseur': 'proveedor', 'nomcompte': 'nombre_cuenta',
            
            'data': 'fecha', 'importo': 'importe', 'conto': 'cuenta', 'dare': 'debe', 'avere': 'haber',
            'centro': 'centro', 'progetto': 'proyecto', 'valuta': 'moneda',
            'scrittura': 'asiento', 'documento': 'documento', 'periodo': 'periodo',
            'fornitore': 'proveedor', 'nomeconto': 'nombre_cuenta',
            
            'data': 'fecha', 'valor': 'importe', 'conta': 'cuenta', 'debito': 'debe', 'credito': 'haber',
            'centro': 'centro', 'projeto': 'proyecto', 'moeda': 'moneda',
            'lancamento': 'asiento', 'documento': 'documento', 'periodo': 'periodo',
            'fornecedor': 'proveedor', 'nomeconta': 'nombre_cuenta'
        }
    
    def reload_and_update(self, force: bool = False) -> bool:
        if self.field_loader.reload_configuration(force):
            self._clear_caches()
            return True
        return False
    
    def reset_mappings(self):
        self._used_field_mappings.clear()
        self._column_mappings.clear()
        self._confidence_by_column.clear()
        self.mapping_stats['unique_mapping_conflicts'] = 0
        self.mapping_stats['header_forced_mappings'] = 0
        self.mapping_stats['smart_reassignments'] = 0
    
    def get_all_field_synonyms(self, field_type: str, erp_system: str = None) -> List[str]:
        cache_key = f"{field_type}_{erp_system or 'all'}"
        
        if cache_key in self._erp_synonyms_cache:
            self.mapping_stats['cache_hits'] += 1
            return self._erp_synonyms_cache[cache_key]
        
        synonyms = []
        field_def = self.field_loader.get_field_definition(field_type)
        
        if field_def:
            if erp_system:
                synonyms = field_def.get_synonyms_for_erp(erp_system)
            else:
                synonyms = field_def.get_all_synonyms()
        
        self._erp_synonyms_cache[cache_key] = synonyms
        return synonyms
    
    def set_dataframe_for_balance_validation(self, df: pd.DataFrame):
        self._dataframe_for_balance = df.copy()
        self._numeric_fields_prepared = False
        
    def find_field_mapping(self, field_name: str, erp_system: str = None, 
                      sample_data: pd.Series = None,
                      skip_conflict_resolution: bool = False) -> Optional[Tuple[str, float]]:
        """Enhanced mapping search with content analysis and INTELLIGENT UNIQUE MAPPING"""
        self.mapping_stats['total_mappings_requested'] += 1
        
        # Special rule: if description contains "Cabecera" or "header", force description
        field_name_lower = field_name.lower()
        if ('cabecera' in field_name_lower or 'header' in field_name_lower) and 'description' in field_name_lower:
            if 'description' not in self._used_field_mappings:
                self._used_field_mappings['description'] = field_name
                self._column_mappings[field_name] = 'description'
                self._confidence_by_column[field_name] = 0.95
                self.mapping_stats['header_forced_mappings'] += 1
                self.mapping_stats['successful_mappings'] += 1
                return ('description', 0.95)
        
        normalized_name = self._normalize_field_name(field_name)
        
        translated_name = self._try_translate_field_name(field_name)
        if translated_name != field_name:
            logger.debug(f"Translated '{field_name}' to '{translated_name}'")
        
        content_analysis = self._enhanced_content_analysis(field_name, sample_data) if sample_data is not None else {}
        
        exact_matches = self._find_exact_matches(field_name, erp_system)
        
        best_match = self._find_best_match_with_content(field_name, exact_matches, content_analysis, sample_data)
        
        if best_match:
            field_type, confidence = best_match
            if not skip_conflict_resolution:
                conflict_resolution = self._resolve_mapping_conflict(field_name, field_type, confidence, sample_data)
                
                if conflict_resolution:
                    final_field_type, final_confidence = conflict_resolution
                    
                    self._used_field_mappings[final_field_type] = field_name
                    self._column_mappings[field_name] = final_field_type
                    self._confidence_by_column[field_name] = final_confidence
                    
                    self.mapping_stats['successful_mappings'] += 1
                    return (final_field_type, final_confidence)
            else:
                return (field_type, confidence)
        
        self.mapping_stats['failed_mappings'] += 1
        return None
    
    def find_field_mapping_simple(self, field_name: str, erp_system: str = None, 
                              sample_data: pd.Series = None) -> Optional[Tuple[str, float]]:
        return self.find_field_mapping(field_name, erp_system, sample_data, skip_conflict_resolution=True)
    
    def _enhanced_content_analysis(self, field_name: str, sample_data: pd.Series) -> Dict[str, float]:
        """Enhanced content analysis with new fields"""
        if sample_data is None or len(sample_data) == 0:
            return {}
        
        analysis = {}
        clean_data = sample_data.dropna()
        
        if len(clean_data) == 0:
            return {}
        
        str_data = clean_data.astype(str)
        
        numeric_analysis = self._analyze_numeric_content(clean_data)
        analysis.update(numeric_analysis)
        
        text_analysis = self._analyze_text_content(str_data, field_name)
        analysis.update(text_analysis)
        
        date_analysis = self._analyze_date_content_improved(str_data)
        analysis.update(date_analysis)
        
        pattern_analysis = self._analyze_field_patterns(field_name, clean_data)
        analysis.update(pattern_analysis)
        
        vendor_analysis = self._analyze_vendor_id_content(field_name, str_data)
        analysis.update(vendor_analysis)
        
        account_name_analysis = self._analyze_gl_account_name_content(field_name, str_data)
        analysis.update(account_name_analysis)
        
        return analysis
    
    def _analyze_numeric_content(self, data: pd.Series) -> Dict[str, float]:
        """Enhanced numeric analysis with updated names"""
        analysis = {}
        
        try:
            numeric_data = pd.to_numeric(data, errors='coerce')
            non_null_numeric = numeric_data.dropna()
            
            if len(non_null_numeric) == 0:
                return analysis
            
            numeric_ratio = len(non_null_numeric) / len(data)
            
            if numeric_ratio < 0.7:
                return analysis
            
            zero_count = (non_null_numeric == 0).sum()
            positive_count = (non_null_numeric > 0).sum()
            negative_count = (non_null_numeric < 0).sum()
            total_count = len(non_null_numeric)
            
            min_val = non_null_numeric.min()
            max_val = non_null_numeric.max()
            mean_val = non_null_numeric.mean()
            std_val = non_null_numeric.std()
            
            if abs(mean_val) > 1 and std_val > 1:
                zero_ratio = zero_count / total_count
                
                if zero_ratio > 0.3:
                    if positive_count > negative_count:
                        analysis['debit_amount'] = 0.8
                    else:
                        analysis['credit_amount'] = 0.7
                else:
                    analysis['amount'] = 0.9
            
            elif max_val <= 1000 and std_val < 10:
                unique_ratio = len(non_null_numeric.unique()) / len(non_null_numeric)
                if unique_ratio < 0.2:
                    analysis['document_number'] = 0.7
            
            elif all(1900 <= val <= 2100 for val in non_null_numeric if pd.notna(val)):
                unique_years = len(non_null_numeric.unique())
                if unique_years <= 5:
                    analysis['fiscal_year'] = 0.9
            
            elif max_val <= 100 and min_val >= 1:
                consecutive_count = 0
                sorted_values = sorted(non_null_numeric)
                for i in range(1, min(len(sorted_values), 20)):
                    if sorted_values[i] == sorted_values[i-1] + 1:
                        consecutive_count += 1
                
                if consecutive_count > len(sorted_values) * 0.3:
                    analysis['line_number'] = 0.8
            
            elif len(non_null_numeric.unique()) < len(non_null_numeric) * 0.7:
                value_counts = non_null_numeric.value_counts()
                if (value_counts > 1).sum() > 0:
                    analysis['journal_entry_id'] = 0.7
            
            elif max_val <= 999999 and min_val >= 1:
                unique_ratio = len(non_null_numeric.unique()) / len(non_null_numeric)
                if unique_ratio > 0.8:
                    analysis['vendor_id'] = 0.6
            
        except Exception as e:
            logger.debug(f"Error in numeric analysis: {e}")
        
        return analysis
    
    def _analyze_text_content(self, str_data: pd.Series, field_name: str) -> Dict[str, float]:
        """Enhanced text content analysis with updated names"""
        analysis = {}
        
        try:
            numeric_like = 0
            for val in str_data.head(10):
                try:
                    float(val)
                    numeric_like += 1
                except:
                    pass
            
            if numeric_like > len(str_data.head(10)) * 0.8:
                return analysis
            
            unique_ratio = len(str_data.unique()) / len(str_data)
            avg_length = str_data.str.len().mean()
            
            field_lower = field_name.lower()
            
            if 'descripcion' in field_lower or 'description' in field_lower:
                if unique_ratio > 0.7:
                    analysis['line_description'] = 0.8
                else:
                    analysis['description'] = 0.7
            
            elif 'concepto' in field_lower or 'concept' in field_lower:
                analysis['description'] = 0.8
            
            elif avg_length > 10 and unique_ratio > 0.5:
                analysis['line_description'] = 0.6
            elif avg_length > 5 and unique_ratio < 0.3:
                analysis['description'] = 0.5
            
        except Exception as e:
            logger.debug(f"Error in text analysis: {e}")
        
        return analysis
    
    def _analyze_date_content_improved(self, str_data: pd.Series) -> Dict[str, float]:
        """Enhanced date analysis with updated names"""
        analysis = {}
        
        try:
            date_patterns = [
                r'^\d{4}-\d{2}-\d{2}$',
                r'^\d{4}-\d{1,2}-\d{1,2}$',
                r'^\d{2}/\d{2}/\d{4}$',
                r'^\d{1,2}/\d{1,2}/\d{4}$',
                r'^\d{4}/\d{2}/\d{2}$',
                r'^\d{4}/\d{1,2}/\d{1,2}$',
                r'^\d{2}-\d{2}-\d{4}$',
                r'^\d{1,2}-\d{1,2}-\d{4}$',
                r'^\d{2}\.\d{2}\.\d{4}$',
                r'^\d{1,2}\.\d{1,2}\.\d{4}$',
                r'^\d{4}\.\d{2}\.\d{2}$',
                r'^\d{4}\.\d{1,2}\.\d{1,2}$',
                r'^\d{8}$',
                r'^\d{2}/\d{2}/\d{2}$',
                r'^\d{1,2}/\d{1,2}/\d{2}$',
                r'^\d{2}-\d{2}-\d{2}$',
                r'^\d{1,2}-\d{1,2}-\d{2}$',
                r'^\d{2}\.\d{2}\.\d{2}$',
                r'^\d{1,2}\.\d{1,2}\.\d{2}$',
                r'^\d{6}$',
            ]
            
            date_like_count = 0
            total_checked = min(len(str_data), 20)
            
            for val in str_data.head(total_checked):
                val_str = str(val).strip()
                
                if any(re.match(pattern, val_str) for pattern in date_patterns):
                    date_like_count += 1
                    continue
                
                try:
                    parsed_date = pd.to_datetime(val_str, errors='coerce')
                    if pd.notna(parsed_date) and 1900 <= parsed_date.year <= 2100:
                        if not val_str.replace('.', '').replace('/', '').replace('-', '').isdigit() or len(val_str) > 6:
                            date_like_count += 1
                except:
                    pass
            
            if total_checked > 0:
                date_ratio = date_like_count / total_checked
                
                if date_ratio >= 0.8:
                    analysis['posting_date'] = 0.9
                    analysis['entry_date'] = 0.85
                elif date_ratio >= 0.6:
                    analysis['posting_date'] = 0.7
                    analysis['entry_date'] = 0.65
                elif date_ratio >= 0.4:
                    analysis['posting_date'] = 0.5
                    analysis['entry_date'] = 0.45
                
        except Exception as e:
            logger.debug(f"Error in date analysis: {e}")
        
        return analysis
    
    def _analyze_vendor_id_content(self, field_name: str, str_data: pd.Series) -> Dict[str, float]:
        """Specific analysis for vendor_id"""
        analysis = {}
        field_lower = field_name.lower()
        
        vendor_patterns = [
            'proveedor', 'vendor', 'supplier', 'fornecedor', 'fournisseur', 'fornitore', 'lieferant'
        ]
        
        if any(pattern in field_lower for pattern in vendor_patterns):
            if any(id_pattern in field_lower for id_pattern in ['id', 'codigo', 'code', 'num']):
                analysis['vendor_id'] = 0.9
            else:
                avg_length = str_data.str.len().mean()
                unique_ratio = len(str_data.unique()) / len(str_data)
                
                if avg_length <= 15 and unique_ratio > 0.8:
                    analysis['vendor_id'] = 0.7
        
        return analysis
    
    def _analyze_gl_account_name_content(self, field_name: str, str_data: pd.Series) -> Dict[str, float]:
        """Specific analysis for gl_account_name"""
        analysis = {}
        field_lower = field_name.lower()
        
        account_name_patterns = [
            'nombre', 'name', 'denominacion', 'description', 'desc', 'titel', 'titre', 'titolo'
        ]
        
        account_patterns = [
            'cuenta', 'account', 'conto', 'compte', 'konto'
        ]
        
        has_name_pattern = any(pattern in field_lower for pattern in account_name_patterns)
        has_account_pattern = any(pattern in field_lower for pattern in account_patterns)
        
        if has_name_pattern and has_account_pattern:
            analysis['gl_account_name'] = 0.9
        elif has_name_pattern and ('gl' in field_lower or 'mayor' in field_lower):
            analysis['gl_account_name'] = 0.8
        elif has_account_pattern and not any(num_pattern in field_lower for num_pattern in ['num', 'number', 'codigo', 'code']):
            avg_length = str_data.str.len().mean()
            if avg_length > 10:
                analysis['gl_account_name'] = 0.7
        
        return analysis
    
    def _analyze_field_patterns(self, field_name: str, data: pd.Series) -> Dict[str, float]:
        """Analysis based on field name patterns with updated names"""
        analysis = {}
        field_lower = field_name.lower()
        
        field_patterns = {
            'saldo': {'amount': 0.95},
            'balance': {'amount': 0.95},
            'importe': {'amount': 0.9},
            'total': {'amount': 0.85},
            'debe': {'debit_amount': 0.95},
            'haber': {'credit_amount': 0.95},
            'debit': {'debit_amount': 0.95},
            'credit': {'credit_amount': 0.95},
            'fecha': {'posting_date': 0.9},
            'date': {'posting_date': 0.9},
            'asiento': {'journal_entry_id': 0.9},
            'journal': {'journal_entry_id': 0.9},
            'cuenta': {'gl_account_number': 0.9},
            'account': {'gl_account_number': 0.9},
            'año': {'fiscal_year': 0.9},
            'year': {'fiscal_year': 0.9},
            'doc': {'document_number': 0.8},
            'documento': {'document_number': 0.8},
            'numero': {'document_number': 0.7},
            'num': {'document_number': 0.7},
            'periodo': {'period_number': 0.9},
            'period': {'period_number': 0.9},
            'preparado': {'prepared_by': 0.8},
            'prepared': {'prepared_by': 0.8},
            'entrada': {'entry_date': 0.8},
            'entry': {'entry_date': 0.8},
            'proveedor': {'vendor_id': 0.7},
            'vendor': {'vendor_id': 0.7},
            'supplier': {'vendor_id': 0.7},
        }
        
        for pattern, mappings in field_patterns.items():
            if pattern in field_lower:
                for field_type, confidence in mappings.items():
                    analysis[field_type] = confidence
                break
        
        return analysis
    
    def _find_best_match_with_content(self, field_name: str, exact_matches: List[Tuple[str, float]], 
                                    content_analysis: Dict[str, float], sample_data: pd.Series) -> Optional[Tuple[str, float]]:
        """Finds best mapping combining exact matches and content analysis"""
        
        if not exact_matches and not content_analysis:
            return None
        
        all_candidates = {}
        
        for field_type, confidence in exact_matches:
            all_candidates[field_type] = confidence
        
        internal_flags = {
            'is_date', 'is_numeric', 'is_text', 'is_monetary', 
            'is_repetitive', 'is_sequential', 'date_like', 'amount_like'
        }
        
        valid_field_types = {
            'journal_entry_id', 'line_number', 'description', 'line_description',
            'posting_date', 'fiscal_year', 'period_number', 'gl_account_number',
            'amount', 'debit_amount', 'credit_amount', 'debit_credit_indicator',
            'prepared_by', 'entry_date', 'entry_time', 'gl_account_name', 'vendor_id'
        }
        
        for field_type, content_confidence in content_analysis.items():
            if field_type in internal_flags:
                continue
                
            if field_type not in valid_field_types:
                continue
                
            if field_type in all_candidates:
                existing_conf = all_candidates[field_type]
                combined_conf = (existing_conf * 0.7) + (content_confidence * 0.3)
                all_candidates[field_type] = min(combined_conf, 1.0)
            else:
                all_candidates[field_type] = content_confidence * 0.8
        
        if not all_candidates:
            return None
        
        best_field_type = max(all_candidates.keys(), key=lambda x: all_candidates[x])
        best_confidence = all_candidates[best_field_type]
        
        if best_confidence < 0.3:
            return None
        
        return (best_field_type, best_confidence)
    
    def _resolve_mapping_conflict(self, field_name: str, field_type: str, confidence: float, 
                                sample_data: pd.Series) -> Optional[Tuple[str, float]]:
        """Enhanced conflict resolution with balance validation only for journal_entry_id"""
        
        if field_type not in self._used_field_mappings:
            return (field_type, confidence)
        
        existing_column = self._used_field_mappings[field_type]
        existing_confidence = self._confidence_by_column.get(existing_column, 0.0)
        
        if field_type == 'journal_entry_id':
            should_reassign, reason = self._resolve_journal_entry_id_conflict_with_balance_validation(
                field_name, existing_column, confidence, existing_confidence
            )
        else:
            should_reassign = False
            
            if confidence > existing_confidence + 0.2:
                should_reassign = True
                reason = f"higher confidence ({confidence:.3f} vs {existing_confidence:.3f})"
            elif field_type == 'amount' and sample_data is not None:
                if self._is_better_amount_candidate(field_name, sample_data):
                    should_reassign = True
                    reason = "better amount candidate based on content"
            elif self._has_better_field_name(field_name, existing_column, field_type):
                should_reassign = True
                reason = "more specific field name"
        
        if should_reassign:
            del self._used_field_mappings[field_type]
            del self._column_mappings[existing_column]
            if existing_column in self._confidence_by_column:
                del self._confidence_by_column[existing_column]
            
            self.mapping_stats['smart_reassignments'] += 1
            
            return (field_type, confidence)
        else:
            self.mapping_stats['unique_mapping_conflicts'] += 1
            return None

    def _resolve_journal_entry_id_conflict_with_balance_validation(self, new_column: str, existing_column: str, 
                                                                new_confidence: float, existing_confidence: float) -> Tuple[bool, str]:
        """Resolves journal_entry_id conflict using the existing BalanceValidator"""
        
        existing_balance_score = self._evaluate_journal_entry_id_balance_score(existing_column, existing_confidence)
        new_balance_score = self._evaluate_journal_entry_id_balance_score(new_column, new_confidence)
        
        existing_combined_score = existing_balance_score * 0.7 + existing_confidence * 0.3
        new_combined_score = new_balance_score * 0.7 + new_confidence * 0.3
        
        if new_combined_score > existing_combined_score:
            reason = f"better_balance_score_{new_balance_score:.3f}_vs_{existing_balance_score:.3f}"
            return True, reason
        else:
            reason = f"keeping_better_balance_score_{existing_balance_score:.3f}_vs_{new_balance_score:.3f}"
            return False, reason

    def _evaluate_journal_entry_id_balance_score(self, journal_column_name: str, confidence: float = None) -> float:
        """Evaluates the quality of a journal_entry_id candidate using existing BalanceValidator"""
        try:
            if not hasattr(self, 'sample_df') or self.sample_df is None:
                synonym_score = confidence if confidence is not None else 0.5
                return synonym_score
            
            df = self.sample_df
            
            if journal_column_name not in df.columns:
                return 0.0
            
            has_debit_credit = 'debit_amount' in df.columns and 'credit_amount' in df.columns
            has_amount = 'amount' in df.columns
            
            if not (has_debit_credit or has_amount):
                synonym_score = confidence if confidence is not None else 0.5
                return synonym_score
            
            try:
                df_temp = df.copy()
                
                backup_column = None
                if 'journal_entry_id' in df_temp.columns:
                    backup_column = df_temp['journal_entry_id'].copy()
                    
                df_temp['journal_entry_id'] = df_temp[journal_column_name]
                
                validator = BalanceValidator(tolerance=0.01)
                
                validation_result = validator.evaluate_journal_entry_id_candidate(df_temp)
                
                final_score = validation_result.get('quality_score', 0.0)
                
                if backup_column is not None:
                    df_temp['journal_entry_id'] = backup_column
                    
                return final_score
                
            except AttributeError as e:
                if 'evaluate_journal_entry_id_candidate' in str(e):
                    return confidence if confidence is not None else 0.5
                else:
                    raise e
                    
            except Exception as e:
                return 0.1
                
        except Exception as e:
            return 0.0

    def set_sample_dataframe(self, df: pd.DataFrame):
        """Sets sample DataFrame for balance validation of journal_entry_id"""
        self.sample_df = df

    def _is_better_amount_candidate(self, field_name: str, sample_data: pd.Series) -> bool:
        """Verifies if a column is a better candidate for amount"""
        try:
            field_lower = field_name.lower()
            amount_indicators = ['saldo', 'balance', 'importe', 'amount', 'total']
            
            if any(indicator in field_lower for indicator in amount_indicators):
                numeric_data = pd.to_numeric(sample_data, errors='coerce').dropna()
                if len(numeric_data) > 0:
                    std_val = numeric_data.std()
                    mean_val = abs(numeric_data.mean())
                    
                    if std_val > 1 and mean_val > 1:
                        return True
            
            return False
            
        except Exception:
            return False
    
    def _has_better_field_name(self, new_field_name: str, existing_field_name: str, field_type: str) -> bool:
        """Compares field names to determine which is more specific"""
        
        specificity_keywords = {
            'amount': ['saldo', 'balance', 'importe', 'amount'],
            'debit_amount': ['debe', 'debit'],
            'credit_amount': ['haber', 'credit'],
            'journal_entry_id': ['asiento', 'journal'],
            'posting_date': ['fecha', 'date'],
            'gl_account_number': ['cuenta', 'account'],
            'gl_account_name': ['nombre', 'name'],
            'vendor_id': ['proveedor', 'vendor', 'supplier']
        }
        
        if field_type not in specificity_keywords:
            return False
        
        keywords = specificity_keywords[field_type]
        new_score = sum(1 for kw in keywords if kw in new_field_name.lower())
        existing_score = sum(1 for kw in keywords if kw in existing_field_name.lower())
        
        return new_score > existing_score
    
    def _find_exact_matches(self, field_name: str, erp_system: str = None) -> List[Tuple[str, float]]:
        """Finds exact matches with ERP priority"""
        normalized_name = self._normalize_field_name(field_name)
        exact_matches = []
        
        field_definitions = self.field_loader.get_field_definitions()
        
        for field_type, field_def in field_definitions.items():
            if erp_system and erp_system in field_def.synonyms_by_erp:
                for synonym in field_def.synonyms_by_erp[erp_system]:
                    if normalized_name == self._normalize_field_name(synonym.name):
                        if not self._is_problematic_partial_match(field_name, synonym.name):
                            confidence = min(0.95 + (synonym.confidence_boost * 0.05), 1.0)
                            exact_matches.append((field_type, confidence))
            
            for erp_synonyms in field_def.synonyms_by_erp.values():
                for synonym in erp_synonyms:
                    if normalized_name == self._normalize_field_name(synonym.name):
                        if not self._is_problematic_partial_match(field_name, synonym.name):
                            confidence = min(0.85 + (synonym.confidence_boost * 0.1), 1.0)
                            exact_matches.append((field_type, confidence))
            
            if normalized_name == self._normalize_field_name(field_def.code):
                exact_matches.append((field_type, 0.90))
        
        unique_matches = {}
        for field_type, confidence in exact_matches:
            if field_type not in unique_matches or confidence > unique_matches[field_type]:
                unique_matches[field_type] = confidence
        
        return [(field_type, confidence) for field_type, confidence in unique_matches.items()]
    
    def _is_problematic_partial_match(self, field_name: str, synonym_name: str) -> bool:
        """Detects problematic partial matches"""
        field_lower = field_name.lower()
        synonym_lower = synonym_name.lower()
        
        if field_lower != synonym_lower:
            if synonym_lower in field_lower:
                problematic_prefixes = ['fecha', 'numero', 'codigo', 'tipo', 'descripcion']
                for prefix in problematic_prefixes:
                    if field_lower.startswith(prefix) and synonym_lower not in prefix:
                        return True
        
        return False
    
    def _try_translate_field_name(self, field_name: str) -> str:
        """Attempts to translate field names from other languages"""
        field_lower = field_name.lower()
        normalized = self._normalize_field_name(field_lower)
        
        for foreign_word, spanish_word in self.translation_map.items():
            if foreign_word in normalized:
                return field_name.replace(foreign_word, spanish_word)
        
        return field_name
    
    def get_confidence_boost(self, field_name: str, field_type: str, erp_system: str = None) -> float:
        """Gets confidence boost for a specific field"""
        field_def = self.field_loader.get_field_definition(field_type)
        if not field_def:
            return 0.0
        
        boost = 0.0
        
        if erp_system:
            boost = field_def.get_confidence_for_erp(erp_system)
        else:
            all_confidences = [
                field_def.get_confidence_for_erp(erp) 
                for erp in field_def.synonyms_by_erp.keys()
            ]
            boost = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        
        return self._normalize_confidence_score(boost)
    
    def add_dynamic_synonym(self, field_type: str, synonym_name: str, 
                           erp_system: str = "Custom", confidence_boost: float = 0.0) -> bool:
        """Adds a synonym dynamically"""
        field_def = self.field_loader.get_field_definition(field_type)
        
        if field_def:
            success = field_def.add_synonym(erp_system, synonym_name, confidence_boost)
            if success:
                self._clear_caches()
            return success
        else:
            return False
    
    def remove_dynamic_synonym(self, field_type: str, synonym_name: str, erp_system: str) -> bool:
        """Removes a synonym dynamically"""
        field_def = self.field_loader.get_field_definition(field_type)
        
        if field_def:
            success = field_def.remove_synonym(erp_system, synonym_name)
            if success:
                self._clear_caches()
            return success
        else:
            return False
    
    def get_all_erp_systems(self) -> List[str]:
        """Gets list of all configured ERP systems"""
        erp_systems = set()
        
        field_definitions = self.field_loader.get_field_definitions()
        for field_def in field_definitions.values():
            erp_systems.update(field_def.synonyms_by_erp.keys())
        
        return sorted(list(erp_systems))
    
    def get_all_field_types(self) -> List[str]:
        """Gets list of all configured field types"""
        return list(self.field_loader.get_field_definitions().keys())
    
    def _normalize_field_name(self, name: str) -> str:
        """Normalizes field name with cache for optimization"""
        if not name:
            return ""
        
        if name in self._normalization_cache:
            return self._normalization_cache[name]
        
        normalized = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
        
        for accented, plain in self.accent_map.items():
            normalized = normalized.replace(accented, plain)
        
        self._normalization_cache[name] = normalized
        
        return normalized
    
    def _clear_caches(self):
        """Clears all caches"""
        self._normalization_cache.clear()
        self._mapping_cache.clear()
        self._erp_synonyms_cache.clear()
        self._content_analysis_cache.clear()
        logger.debug("Enhanced field mapper caches cleared")
    
    def _normalize_confidence_score(self, raw_score: float) -> float:
        """Helper function to normalize any score to range 0-1"""
        if raw_score < 0:
            return 0.0
        elif raw_score > 1:
            return 1.0
        else:
            return raw_score
    
    def get_mapping_statistics(self) -> Dict:
        """Gets enhanced mapping statistics including unique mapping"""
        field_definitions = self.field_loader.get_field_definitions()
        
        total_synonyms = sum(
            len(field_def.get_all_synonyms()) 
            for field_def in field_definitions.values()
        )
        
        erp_systems = self.get_all_erp_systems()
        
        return {
            'total_field_types': len(field_definitions),
            'total_synonyms': total_synonyms,
            'erp_systems': len(erp_systems),
            'erp_systems_list': erp_systems,
            'unique_mappings': {
                'total_mapped_fields': len(self._used_field_mappings),
                'mapped_columns': len(self._column_mappings),
                'available_fields': len(field_definitions) - len(self._used_field_mappings)
            },
            'cache_sizes': {
                'normalization_cache': len(self._normalization_cache),
                'mapping_cache': len(self._mapping_cache),
                'erp_synonyms_cache': len(self._erp_synonyms_cache),
                'content_analysis_cache': len(self._content_analysis_cache)
            },
            'usage_stats': self.mapping_stats.copy(),
            'field_loader_stats': self.field_loader.get_statistics()
        }
    
    def analyze_dataframe_with_unique_mapping(self, df: pd.DataFrame, erp_system: str = None) -> Dict:
        """Enhanced DataFrame analysis with intelligent unique mapping"""
        self.reset_mappings()
        
        results = {
            'total_columns': len(df.columns),
            'erp_system': erp_system,
            'field_mappings': {},
            'conflicts_found': [],
            'suggestions': [],
            'confidence_scores': {},
            'unique_mapping_stats': {
                'successful_mappings': 0,
                'failed_mappings': 0,
                'forced_headers': 0,
                'smart_reassignments': 0
            }
        }
        
        column_priority = self._prioritize_columns(df.columns.tolist())
        
        for column in column_priority:
            sample_data = df[column].dropna().head(100)
            mapping_result = self.find_field_mapping(column, erp_system, sample_data)
            
            if mapping_result:
                field_type, confidence = mapping_result
                results['field_mappings'][column] = field_type
                results['confidence_scores'][column] = confidence
                results['unique_mapping_stats']['successful_mappings'] += 1
            else:
                results['unique_mapping_stats']['failed_mappings'] += 1
                results['suggestions'].append(
                    f"Column '{column}' could not be mapped (all suitable fields may be taken)."
                )
        
        results['unique_mapping_stats']['smart_reassignments'] = self.mapping_stats['smart_reassignments']
        results['unique_mapping_stats']['forced_headers'] = self.mapping_stats['header_forced_mappings']
        
        detection_rate = len(results['field_mappings']) / len(df.columns) * 100
        
        return results
    
    def _prioritize_columns(self, columns: List[str]) -> List[str]:
        """Prioritizes columns for analysis (most specific fields first)"""
        
        priority_patterns = [
            (['saldo', 'balance'], 1),
            (['debe', 'debit'], 1),
            (['haber', 'credit'], 1),
            (['fecha', 'date'], 2),
            (['asiento', 'journal'], 2),
            (['cuenta', 'account'], 2),
            (['cabecera', 'header'], 3),
            (['concepto', 'concept'], 3),
            (['descripcion', 'description'], 4),
            (['doc', 'documento', 'numero'], 5),
            (['proveedor', 'vendor', 'supplier'], 5),
            (['nombre', 'name'], 5),
            ([], 6)
        ]
        
        column_priorities = {}
        
        for column in columns:
            column_lower = column.lower()
            priority = 6
            
            for patterns, prio in priority_patterns:
                if any(pattern in column_lower for pattern in patterns):
                    priority = prio
                    break
            
            column_priorities[column] = priority
        
        return sorted(columns, key=lambda col: column_priorities[col])

    def map_all_columns_with_conflict_resolution(self, df: pd.DataFrame, erp_hint: str = None, 
                                            balance_validator=None) -> Dict[str, Dict]:
        """Maps all columns and resolves global conflicts"""
        
        initial_mappings = {}

        amount_priority = [col for col in df.columns if any(
            kw in col.lower() for kw in ['amount', 'importe', 'saldo','debe', 'haber', 'debit', 'credit']
        )]

        for column_name in amount_priority:
            sample_data = df[column_name].dropna().head(100)
            mapping_result = self.find_field_mapping(column_name, erp_hint, sample_data)
            
            if mapping_result:
                field_type, confidence = mapping_result
                initial_mappings[column_name] = {
                    'field_type': field_type,
                    'confidence': confidence
                }
        
        for column_name in df.columns:
            if column_name in initial_mappings:
                continue

            sample_data = df[column_name].dropna().head(100)
            mapping_result = self.find_field_mapping(column_name, erp_hint, sample_data)
            
            if mapping_result:
                field_type, confidence = mapping_result
                initial_mappings[column_name] = {
                    'field_type': field_type,
                    'confidence': confidence
                }
        
        final_mappings = self._resolve_global_field_conflicts(initial_mappings, df, balance_validator)
        
        return final_mappings

    def _resolve_global_field_conflicts(self, mappings: Dict[str, Dict], df: pd.DataFrame, 
                                    balance_validator=None) -> Dict[str, Dict]:
        """Global conflict resolution logic"""
        
        field_type_groups = {}
        for column, mapping in mappings.items():
            field_type = mapping['field_type']
            if field_type not in field_type_groups:
                field_type_groups[field_type] = []
            field_type_groups[field_type].append((column, mapping['confidence']))
        
        final_mappings = {}
        
        for field_type, candidates in field_type_groups.items():
            if len(candidates) == 1:
                column, confidence = candidates[0]
                final_mappings[column] = {
                    'field_type': field_type,
                    'confidence': confidence,
                    'resolution_type': 'no_conflict'
                }
            
            else:
                winner_column, winner_confidence, resolution_type = self._resolve_field_type_conflict(
                    field_type, candidates, df, balance_validator
                )
                
                final_mappings[winner_column] = {
                    'field_type': field_type,
                    'confidence': winner_confidence,
                    'resolution_type': resolution_type
                }
                
                self.mapping_stats['conflicts_resolved'] += 1
        
        return final_mappings

    def _resolve_field_type_conflict(self, field_type: str, candidates: List[Tuple[str, float]], 
                                df: pd.DataFrame, balance_validator=None) -> Tuple[str, float, str]:
        """Resolves conflict for a specific field_type"""
        
        if field_type == 'journal_entry_id' and balance_validator:
            return self._resolve_journal_entry_id_with_balance(candidates, df, balance_validator)
        
        if field_type == 'amount':
            for column, confidence in candidates:
                if any(x in column.lower() for x in ['local', 'loc.', 'ml', 'lm']):
                    return (column, confidence, 'amount_local_priority')
        
        candidates_sorted = sorted(candidates, key=lambda x: x[1], reverse=True)
        winner_column, winner_confidence = candidates_sorted[0]
        
        return (winner_column, winner_confidence, 'highest_confidence')

    def _resolve_journal_entry_id_with_balance(self, candidates: List[Tuple[str, float]], 
                                            df: pd.DataFrame, balance_validator) -> Tuple[str, float, str]:
        """Balance validation for journal_entry_id conflicts"""
        
        amount_fields_mapped = self._check_mapped_amount_fields()
        
        if len(amount_fields_mapped) < 1:
            candidates_sorted = sorted(candidates, key=lambda x: x[1], reverse=True)
            winner_column, winner_confidence = candidates_sorted[0]
            return (winner_column, winner_confidence, 'highest_confidence')
        
        balance_scores = {}
        
        for column_name, confidence in candidates:
            balance_score = self._calculate_balance_score_for_column(column_name, df, balance_validator)
            balance_scores[column_name] = balance_score
        
        winner_column = max(balance_scores.keys(), key=lambda col: balance_scores[col])
        winner_confidence = next(conf for col, conf in candidates if col == winner_column)
        winner_balance_score = balance_scores[winner_column]
        
        return (winner_column, winner_confidence, 'balance_validation_winner')

    def _check_mapped_amount_fields(self) -> List[str]:
        """Verifies which amount fields are already mapped with high confidence"""
        amount_fields = []
        
        for field_type in ['debit_amount', 'credit_amount', 'amount']:
            if field_type in self._used_field_mappings:
                mapped_column = self._used_field_mappings[field_type]
                confidence = self._confidence_by_column.get(mapped_column, 0.0)
                if confidence >= 0.75:
                    amount_fields.append(field_type)
        
        return amount_fields

    def _calculate_balance_score_for_column(self, column_name: str, df: pd.DataFrame, balance_validator) -> float:
        """Calculates balance_score for journal_entry_id candidate"""
        try:
            temp_df = df.copy()
            column_mapping = {mapped_col: ftype for ftype, mapped_col in self._used_field_mappings.items()}
            column_mapping[column_name] = 'journal_entry_id'
            temp_df = temp_df.rename(columns=column_mapping)

            for col in ('debit_amount', 'credit_amount', 'amount'):
                if col in temp_df.columns:
                    temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')

            result = balance_validator.evaluate_journal_entry_id_candidate(temp_df)
            return float(result.get('quality_score', 0.0))
        except Exception as e:
            return 0.0

def create_field_mapper(config_file: str = None) -> FieldMapper:
    return FieldMapper(config_source=config_file)