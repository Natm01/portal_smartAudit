# procesos_mapeo/balance_validator.py
import pandas as pd
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BalanceValidator:
    """Reusable validator for accounting balances"""
    
    def __init__(self, tolerance: float = 0.01):
        self.tolerance = tolerance
        self.validation_stats = {
            'balance_checks_performed': 0,
            'total_entries_checked': 0,
            'balanced_entries': 0,
            'unbalanced_entries': 0
        }
    
    def perform_comprehensive_balance_validation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Performs complete balance validation by entry and totals"""
        try:
            self.validation_stats = {key: 0 for key in self.validation_stats.keys()}
            
            balance_report = {
                'total_debit_sum': 0.0,
                'total_credit_sum': 0.0,
                'total_balance_difference': 0.0,
                'is_balanced': False,
                'entry_balance_check': [],
                'unbalanced_entries': [],
                'entries_count': 0,
                'balanced_entries_count': 0,
                'validation_details': {},
                'tolerance_used': self.tolerance
            }
            
            required_fields = self._check_required_fields(df)
            if not required_fields['has_required_fields']:
                balance_report['validation_details'] = required_fields
                return balance_report
            
            total_validation = self._validate_total_balance(df)
            balance_report.update(total_validation)
            
            if 'journal_entry_id' in df.columns:
                entry_validation = self._validate_entry_level_balance(df)
                balance_report.update(entry_validation)
            
            if 'amount' in df.columns:
                cross_validation = self._validate_cross_balance(df)
                balance_report['cross_validation'] = cross_validation
            
            self.validation_stats['balance_checks_performed'] = 1
            balance_report['validation_stats'] = self.validation_stats.copy()
            
            return balance_report
            
        except Exception as e:
            logger.error(f"Error in balance validation: {e}")
            return balance_report
    
    def evaluate_journal_entry_id_candidate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Evaluates how good the current journal_entry_id is for grouping accounting data"""
        try:
            if 'journal_entry_id' not in df.columns:
                return {'quality_score': 0.0, 'error': 'No journal_entry_id column found'}
            
            # Handle different naming conventions
            rename_map = {}
            if 'amount_numeric' in df.columns and 'amount' not in df.columns:
                rename_map['amount_numeric'] = 'amount'
            if 'debit_amount_numeric' in df.columns and 'debit_amount' not in df.columns:
                rename_map['debit_amount_numeric'] = 'debit_amount'
            if 'credit_amount_numeric' in df.columns and 'credit_amount' not in df.columns:
                rename_map['credit_amount_numeric'] = 'credit_amount'
            
            if rename_map:
                df = df.rename(columns=rename_map)

            if 'debit_amount' in df.columns and 'credit_amount' in df.columns:
                return self._evaluate_journal_id_with_debit_credit(df)
            elif 'amount' in df.columns:
                return self._evaluate_journal_id_with_amount_only(df)
            else:
                return {'quality_score': 0.0, 'error': 'No accounting fields found'}
                
        except Exception as e:
            return {'quality_score': 0.0, 'error': f'Evaluation failed: {e}'}
        
    def _evaluate_journal_id_with_debit_credit(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Complete evaluation using debit/credit + amount"""
        try:
            entry_validation = self._validate_entry_level_balance(df)
            
            entries_count = entry_validation.get('entries_count', 0)
            balanced_entries_count = entry_validation.get('balanced_entries_count', 0)
            balance_rate = balanced_entries_count / entries_count if entries_count > 0 else 0
            
            cross_validation_score = 1.0
            if 'amount' in df.columns:
                cross_validation = self._validate_cross_balance(df)
                cross_validation_score = cross_validation.get('match_rate', 1.0)
            
            quality_score = min(1.0, balance_rate * 0.6 + cross_validation_score * 0.4)
            
            return {
                'quality_score': quality_score,
                'balance_rate': balance_rate,
                'cross_validation_rate': cross_validation_score,
                'entries_count': entries_count,
                'validation_type': 'debit_credit'
            }
            
        except Exception as e:
            return {'quality_score': 0.0, 'error': f'Debit/credit validation failed: {e}'}

    def _evaluate_journal_id_with_amount_only(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Alternative evaluation: validates if amount per entry sums to zero"""
        try:
            grouped = df.groupby('journal_entry_id').agg({
                'amount': 'sum'
            }).reset_index()
            
            total_entries = len(grouped)
            if total_entries == 0:
                return {'quality_score': 0.0, 'error': 'No entries found'}

            balanced_entries = (grouped['amount'].round(2) == 0).sum()
            quality_score = balanced_entries / total_entries

            return {
                'quality_score': quality_score,
                'entries_count': total_entries,
                'balanced_entries': int(balanced_entries),
                'unbalanced_entries': int(total_entries - balanced_entries),
                'validation_type': 'amount_zero_check'
            }
            
        except Exception as e:
            return {'quality_score': 0.0, 'error': f'Amount-only validation failed: {e}'}
    
    def _check_required_fields(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Verifies that necessary fields exist for validation"""
        has_debit = 'debit_amount' in df.columns
        has_credit = 'credit_amount' in df.columns
        has_amount = 'amount' in df.columns
        has_journal_id = 'journal_entry_id' in df.columns
        
        if not (has_debit and has_credit):
            return {
                'has_required_fields': False,
                'missing_fields': [
                    field for field, exists in [
                        ('debit_amount', has_debit),
                        ('credit_amount', has_credit)
                    ] if not exists
                ],
                'available_fields': {
                    'debit_amount': has_debit,
                    'credit_amount': has_credit,
                    'amount': has_amount,
                    'journal_entry_id': has_journal_id
                }
            }
        
        return {
            'has_required_fields': True,
            'available_fields': {
                'debit_amount': has_debit,
                'credit_amount': has_credit,
                'amount': has_amount,
                'journal_entry_id': has_journal_id
            }
        }
    
    def _validate_total_balance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validates total balance of DataFrame"""
        total_debit = df['debit_amount'].sum()
        total_credit = df['credit_amount'].sum()
        total_difference = total_debit - total_credit
        is_balanced = abs(total_difference) < self.tolerance
        
        return {
            'total_debit_sum': total_debit,
            'total_credit_sum': total_credit,
            'total_balance_difference': total_difference,
            'is_balanced': is_balanced
        }
    
    def _validate_entry_level_balance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validates balance for each accounting entry"""
        grouped = df.groupby('journal_entry_id').agg({
            'debit_amount': 'sum',
            'credit_amount': 'sum'
        }).reset_index()
        
        grouped['balance_difference'] = grouped['debit_amount'] - grouped['credit_amount']
        grouped['is_balanced'] = abs(grouped['balance_difference']) < self.tolerance
        
        entries_count = len(grouped)
        balanced_count = grouped['is_balanced'].sum()
        unbalanced_entries = grouped[~grouped['is_balanced']]
        
        self.validation_stats['total_entries_checked'] = entries_count
        self.validation_stats['balanced_entries'] = balanced_count
        self.validation_stats['unbalanced_entries'] = len(unbalanced_entries)
        
        return {
            'entries_count': entries_count,
            'balanced_entries_count': balanced_count,
            'unbalanced_entries': unbalanced_entries.to_dict('records'),
            'entry_balance_check': grouped.to_dict('records')
        }
    
    def _validate_cross_balance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Cross-validation using amount field"""
        calculated_amount = df['debit_amount'] - df['credit_amount']
        actual_amount = df['amount']
        
        differences = abs(calculated_amount - actual_amount)
        matches = differences < self.tolerance
        match_count = matches.sum()
        
        significant_diffs = differences[~matches]
        
        return {
            'total_rows': len(df),
            'matching_rows': match_count,
            'match_rate': match_count/len(df),
            'discrepancies': len(significant_diffs),
            'max_difference': significant_diffs.max() if len(significant_diffs) > 0 else 0.0,
            'significant_differences': significant_diffs.head(10).tolist() if len(significant_diffs) > 0 else []
        }
    
    def generate_balance_summary_report(self, balance_report: Dict[str, Any]) -> str:
        """Generates textual summary of balance report"""
        lines = []
        lines.append("BALANCE VALIDATION SUMMARY")
        lines.append("=" * 35)
        
        is_balanced = balance_report.get('is_balanced', False)
        lines.append(f"Total Balance: {'BALANCED' if is_balanced else 'UNBALANCED'}")
        lines.append(f"Total Debit:   {balance_report.get('total_debit_sum', 0):,.2f}")
        lines.append(f"Total Credit:  {balance_report.get('total_credit_sum', 0):,.2f}")
        lines.append(f"Difference:    {balance_report.get('total_balance_difference', 0):,.2f}")
        
        entries_count = balance_report.get('entries_count', 0)
        if entries_count > 0:
            balanced_count = balance_report.get('balanced_entries_count', 0)
            unbalanced_count = entries_count - balanced_count
            lines.append("")
            lines.append("Entry-Level Analysis:")
            lines.append(f"Total Entries:     {entries_count}")
            lines.append(f"Balanced Entries:  {balanced_count}")
            lines.append(f"Unbalanced:        {unbalanced_count}")
            lines.append(f"Balance Rate:      {balanced_count/entries_count*100:.1f}%")
        
        cross_val = balance_report.get('cross_validation')
        if cross_val:
            lines.append("")
            lines.append("Cross-Validation:")
            lines.append(f"Amount field match rate: {cross_val['match_rate']*100:.1f}%")
            if cross_val['discrepancies'] > 0:
                lines.append(f"Discrepancies found:     {cross_val['discrepancies']}")
        
        return "\n".join(lines)

# Utility functions
def validate_dataframe_balance(df: pd.DataFrame, tolerance: float = 0.01) -> Dict[str, Any]:
    validator = BalanceValidator(tolerance=tolerance)
    return validator.perform_comprehensive_balance_validation(df)