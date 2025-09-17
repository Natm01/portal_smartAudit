# procesos_mapeo/accounting_data_processor.py
import pandas as pd
import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)

class AccountingDataProcessor:
    """Reusable processor for accounting data with numeric cleaning and calculations"""
    
    def __init__(self):
        self.stats = {
            'zero_filled_fields': 0,
            'debit_credit_calculated': 0,
            'debit_amounts_from_indicator': 0,
            'credit_amounts_from_indicator': 0,
            'amount_signs_adjusted': 0,
            'fields_cleaned': 0,
            'parentheses_negatives_processed': 0,
            'amount_calculated': 0,
            'indicators_created': 0
        }
    
    def separate_datetime_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Separates combined DateTime fields into separate date and time fields"""
        try:
            def separate_datetime_field(df, field_name):
                if field_name not in df.columns:
                    return df
                
                sample_values = df[field_name].dropna().head(10)
                if len(sample_values) == 0:
                    return False
                
                datetime_detected = False
                pure_date_count = 0
                pure_time_count = 0
                
                detected_format = None
                detected_dayfirst = True
                
                for value in sample_values:
                    str_value = str(value).strip()
                    
                    pure_date_patterns = [
                        r'^\d{1,2}\.\d{1,2}\.\d{4}$',
                        r'^\d{1,2}/\d{1,2}/\d{4}$',
                        r'^\d{1,2}-\d{1,2}-\d{4}$',
                        r'^\d{4}-\d{2}-\d{2}$',
                        r'^\d{4}/\d{2}/\d{2}$',
                        r'^\d{4}\.\d{2}\.\d{2}$',
                        r'^\d{8}$',
                    ]
                    
                    pure_time_patterns = [
                        r'^\d{1,2}:\d{2}:\d{2}$',
                        r'^\d{1,2}:\d{2}$',
                        r'^\d{1,2}:\d{2}:\d{2}\.\d+$',
                    ]
                    
                    if any(re.match(pattern, str_value) for pattern in pure_date_patterns):
                        pure_date_count += 1
                        if not detected_format:
                            if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', str_value):
                                detected_format = '%d.%m.%Y'
                                detected_dayfirst = True
                            elif re.match(r'^\d{4}-\d{2}-\d{2}$', str_value):
                                detected_format = '%Y-%m-%d'
                                detected_dayfirst = False
                            elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', str_value):
                                detected_dayfirst = True
                            else:
                                detected_dayfirst = '.' in str_value or not str_value.startswith(('20', '19'))
                        continue
                    elif any(re.match(pattern, str_value) for pattern in pure_time_patterns):
                        pure_time_count += 1
                        continue
                    
                    combined_datetime_patterns = [
                        r'\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}',
                        r'\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}',
                        r'\d{1,2}-\d{1,2}-\d{4}\s+\d{1,2}:\d{2}',
                        r'\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}',
                        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
                    ]
                    
                    for pattern in combined_datetime_patterns:
                        if re.search(pattern, str_value):
                            datetime_detected = True
                            if not detected_format:
                                if re.search(r'\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}', str_value):
                                    detected_format = '%d.%m.%Y %H:%M:%S'
                                    detected_dayfirst = True
                                elif re.search(r'\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}', str_value):
                                    detected_format = '%Y-%m-%d %H:%M:%S'
                                    detected_dayfirst = False
                                elif re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', str_value):
                                    detected_format = '%Y-%m-%dT%H:%M:%S'
                                    detected_dayfirst = False
                                else:
                                    detected_dayfirst = '.' in str_value or ('/' in str_value and not str_value.startswith(('20', '19')))
                            break
                    
                    if datetime_detected:
                        break
                
                total_samples = len(sample_values)
                if total_samples == 0:
                    return False
                    
                pure_date_ratio = pure_date_count / total_samples
                pure_time_ratio = pure_time_count / total_samples
                
                if pure_date_ratio >= 0.7:
                    return False
                elif pure_time_ratio >= 0.7:
                    return False
                elif not datetime_detected:
                    return False
                
                dates = []
                times = []
                
                for value in df[field_name]:
                    if pd.isna(value) or value == '':
                        dates.append('')
                        times.append('')
                        continue
                    
                    str_value = str(value).strip()
                    
                    if any(re.match(pattern, str_value) for pattern in pure_date_patterns):
                        dates.append(str_value)
                        times.append('')
                        continue
                    
                    if any(re.match(pattern, str_value) for pattern in pure_time_patterns):
                        dates.append('')
                        times.append(str_value)
                        continue
                    
                    has_space_and_colon = ' ' in str_value and ':' in str_value
                    has_t_separator = 'T' in str_value and ':' in str_value
                    
                    if has_space_and_colon or has_t_separator:
                        try:
                            if detected_format:
                                try:
                                    parsed_dt = pd.to_datetime(str_value, format=detected_format)
                                except:
                                    parsed_dt = pd.to_datetime(str_value, dayfirst=detected_dayfirst, errors='raise')
                            else:
                                parsed_dt = pd.to_datetime(str_value, dayfirst=detected_dayfirst, errors='raise')
                            
                            if '.' in str_value:
                                date_str = parsed_dt.strftime('%d.%m.%Y')
                            elif '/' in str_value:
                                date_str = parsed_dt.strftime('%d/%m/%Y')
                            else:
                                date_str = parsed_dt.strftime('%Y-%m-%d')
                            
                            time_str = parsed_dt.strftime('%H:%M:%S')
                            
                            dates.append(date_str)
                            times.append(time_str)
                            
                        except Exception as e:
                            dates.append(str_value)
                            times.append('')
                    else:
                        dates.append(str_value)
                        times.append('')
                
                if any(time for time in times if time):
                    if field_name == 'entry_date':
                        date_field = 'entry_date'
                        time_field = 'entry_time'
                    elif field_name == 'entry_time':
                        date_field = 'entry_date'
                        time_field = 'entry_time'
                    else:
                        date_field = field_name
                        time_field = field_name.replace('_date', '_time').replace('date', 'time')
                        if time_field == date_field:
                            time_field = f"{field_name}_time"
                    
                    df[date_field] = dates
                    
                    if time_field not in df.columns or df[time_field].isna().all():
                        df[time_field] = times
                    else:
                        counter = 1
                        new_time_field = f"{time_field}_{counter}"
                        while new_time_field in df.columns:
                            counter += 1
                            new_time_field = f"{time_field}_{counter}"
                        df[new_time_field] = times
                        time_field = new_time_field
                    
                    return True
                
                return False
            
            if 'entry_date' in df.columns:
                separate_datetime_field(df, 'entry_date')
                
            if 'entry_time' in df.columns:
                separate_datetime_field(df, 'entry_time')
            
            if 'posting_date' in df.columns:
                separate_datetime_field(df, 'posting_date')
                
        except Exception as e:
            pass

        return df

    def process_numeric_fields_and_calculate_amounts(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Main function that processes numeric fields and calculates amounts based on availability"""
        try:
            self.stats = {key: 0 for key in self.stats.keys()}
            
            df = self._clean_existing_numeric_fields(df)
            
            has_amount = 'amount' in df.columns
            has_debit = 'debit_amount' in df.columns
            has_credit = 'credit_amount' in df.columns
            has_indicator = 'debit_credit_indicator' in df.columns
            
            if not has_amount and has_debit and has_credit:
                df = self._calculate_amount_from_debit_credit(df)
            elif has_amount and has_indicator and not has_debit and not has_credit:
                df = self._calculate_debit_credit_from_amount_indicator(df)
            elif has_amount and not has_indicator and not has_debit and not has_credit:
                df = self._handle_amount_only_scenario(df)
            
            return df, self.stats.copy()
            
        except Exception as e:
            logger.error(f"Error in accounting data processing: {e}")
            return df, self.stats.copy()
    
    def _clean_existing_numeric_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        numeric_fields = ['amount', 'debit_amount', 'credit_amount']
        
        for field in numeric_fields:
            if field in df.columns:
                parentheses_count = df[field].astype(str).str.contains(r'\(', na=False).sum()
                
                df[field] = df[field].apply(self._clean_numeric_value_with_zero_fill)
                
                zero_count = (df[field] == 0.0).sum()
                self.stats['zero_filled_fields'] += zero_count
                self.stats['fields_cleaned'] += 1
                self.stats['parentheses_negatives_processed'] += parentheses_count
        
        return df
    
    def _calculate_amount_from_debit_credit(self, df: pd.DataFrame) -> pd.DataFrame:
        df['amount'] = df['debit_amount'] - df['credit_amount']
        self.stats['amount_calculated'] = len(df)
        return df
    
    def _calculate_debit_credit_from_amount_indicator(self, df: pd.DataFrame) -> pd.DataFrame:
        df['debit_amount'] = 0.0
        df['credit_amount'] = 0.0
        
        df['debit_credit_indicator'] = df['debit_credit_indicator'].fillna('').astype(str).str.strip().str.upper()
        
        debit_patterns = ['D', 'DEBE', 'DEBIT', 'DR', 'DB', '1', 'S']
        credit_patterns = ['C', 'H', 'HABER', 'CREDIT', 'CR', 'CD', '0', '-1', 'N']
        
        is_debit = df['debit_credit_indicator'].isin(debit_patterns)
        is_credit = df['debit_credit_indicator'].isin(credit_patterns)
        
        df.loc[is_debit, 'debit_amount'] = df.loc[is_debit, 'amount'].abs()
        df.loc[is_debit, 'credit_amount'] = 0.0
        
        df.loc[is_credit, 'debit_amount'] = 0.0
        df.loc[is_credit, 'credit_amount'] = df.loc[is_credit, 'amount'].abs()
        
        df.loc[is_credit, 'amount'] = -df.loc[is_credit, 'amount'].abs()
        df.loc[is_debit, 'amount'] = df.loc[is_debit, 'amount'].abs()
        
        debit_assigned = is_debit.sum()
        credit_assigned = is_credit.sum()
        
        self.stats['debit_credit_calculated'] = debit_assigned + credit_assigned
        self.stats['debit_amounts_from_indicator'] = debit_assigned
        self.stats['credit_amounts_from_indicator'] = credit_assigned
        self.stats['amount_signs_adjusted'] = debit_assigned + credit_assigned
        
        return df
    
    def _handle_amount_only_scenario(self, df: pd.DataFrame) -> pd.DataFrame:
        df['debit_amount'] = 0.0
        df['credit_amount'] = 0.0
        
        df['amount'] = df['amount'].apply(self._clean_numeric_value_with_zero_fill)
        
        positive_amounts = df['amount'] > 0
        negative_amounts = df['amount'] < 0
        zero_amounts = df['amount'] == 0
        
        df.loc[positive_amounts, 'debit_amount'] = df.loc[positive_amounts, 'amount'].abs()
        df.loc[positive_amounts, 'credit_amount'] = 0.0
        
        df.loc[negative_amounts, 'debit_amount'] = 0.0
        df.loc[negative_amounts, 'credit_amount'] = df.loc[negative_amounts, 'amount'].abs()
        
        df.loc[zero_amounts, 'debit_amount'] = 0.0
        df.loc[zero_amounts, 'credit_amount'] = 0.0
        
        positive_count = positive_amounts.sum()
        negative_count = negative_amounts.sum()
        
        self.stats['debit_amounts_from_indicator'] += positive_count
        self.stats['credit_amounts_from_indicator'] += negative_count
        
        return df
    
    def _clean_numeric_value_with_zero_fill(self, value) -> float:
        try:
            # Si ya es numérico, devolverlo tal como está (sin abs)
            if isinstance(value, (int, float)):
                return float(value)
           
            # Convertir a string para procesamiento
            str_value = str(value).strip()
            if str_value == '':
                return 0.0
           
            # Detectar si tiene paréntesis (indica negativo)
            is_parentheses_negative = bool(re.search(r'\([^)]*\d+[^)]*\)', str_value))
           
            # Limpiar: mantener solo dígitos, puntos, comas y signos menos
            cleaned = re.sub(r'[^\d.,\-]', '', str_value)
           
            if cleaned:
                # Manejar comas y puntos decimales
                if ',' in cleaned and '.' in cleaned:
                    # Formato como 1,234.56 vs 1.234,56
                    if cleaned.rfind(',') < cleaned.rfind('.'):
                        cleaned = cleaned.replace(',', '')
                    else:
                        # Formato como 1.234,56
                        last_comma = cleaned.rfind(',')
                        cleaned = cleaned[:last_comma].replace(',', '').replace('.', '') + '.' + cleaned[last_comma+1:]
                elif ',' in cleaned:
                    # Solo comas - asumir decimal si hay 2 dígitos después de la última coma
                    parts = cleaned.split(',')
                    if len(parts[-1]) <= 2:  # Cambio: <= 2 en lugar de == 2
                        cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
                    else:
                        cleaned = cleaned.replace(',', '')
                elif '.' in cleaned:
                    # NUEVA LÓGICA: Solo puntos - formato europeo
                    dot_parts = cleaned.split('.')
                    if len(dot_parts) >= 2:
                        last_part = dot_parts[-1]
                        # Si hay múltiples puntos Y la última parte tiene 1-2 dígitos → formato europeo
                        if len(dot_parts) > 2 and len(last_part) <= 2 and last_part.isdigit():
                            # 25.000.00 → 25000.00
                            integer_part = ''.join(dot_parts[:-1])
                            cleaned = f"{integer_part}.{last_part}"
                        elif len(dot_parts) == 2 and len(last_part) > 2:
                            # 1.234567 → separador de miles solamente
                            cleaned = cleaned.replace('.', '')
                        # Si len(dot_parts) == 2 and len(last_part) <= 2: mantener como decimal normal
               
                # Extraer el primer número (ahora debería ser el limpio)
                first_num = re.search(r'-?\d+\.?\d*', cleaned)
                if first_num:
                    result = float(first_num.group())
                    # Si había paréntesis, hacer negativo
                    if is_parentheses_negative:
                        result = -result
                    return result
                   
                return 0.0
        except:
            return 0.0


def clean_numeric_field(series: pd.Series, field_name: str = "field") -> pd.Series:
    processor = AccountingDataProcessor()
    return series.apply(processor._clean_numeric_value_with_zero_fill)

def calculate_amount_from_debit_credit(debit_series: pd.Series, credit_series: pd.Series) -> pd.Series:
    return debit_series - credit_series

def split_amount_by_indicator(amount_series: pd.Series, indicator_series: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
    processor = AccountingDataProcessor()
    df_temp = pd.DataFrame({
        'amount': amount_series,
        'debit_credit_indicator': indicator_series
    })
    
    df_processed = processor._calculate_debit_credit_from_amount_indicator(df_temp)
    
    return df_processed['debit_amount'], df_processed['credit_amount'], df_processed['amount']