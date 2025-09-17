import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ComprehensiveReporter:
    """Single comprehensive report generator for mapeo processes"""
    
    def __init__(self):
        self.report_sections = []
    
    def generate_mapeo_report(self, mapeo_data: Dict[str, Any]) -> str:
        """Generate comprehensive mapeo report content"""
        try:
            self.report_sections = []
            content_parts = []
            
            content_parts.append(self._create_report_header(mapeo_data))
            self.report_sections.append("Header")
            
            content_parts.append(self._create_session_info_section(mapeo_data))
            self.report_sections.append("Session Info")
            
            content_parts.append(self._create_statistics_section(mapeo_data))
            self.report_sections.append("Statistics")
            
            content_parts.append(self._create_automatic_conflict_resolution_section(mapeo_data))
            self.report_sections.append("Automatic Conflict Resolution")
            
            content_parts.append(self._create_confidence_filter_section(mapeo_data))
            self.report_sections.append("Confidence Filter")
            
            content_parts.append(self._create_datetime_validations_section(mapeo_data))
            self.report_sections.append("Date/Time Validations")
            
            content_parts.append(self._create_numeric_processing_section(mapeo_data))
            self.report_sections.append("Numeric Processing")
            
            content_parts.append(self._create_mapping_table_section(mapeo_data))
            self.report_sections.append("Final Mapping Table")
            
            content_parts.append(self._create_decisions_section(mapeo_data))
            self.report_sections.append("Decisions")
            
            if mapeo_data.get('conflict_resolutions'):
                content_parts.append(self._create_conflicts_section(mapeo_data))
                self.report_sections.append("Conflict Resolutions")
            
            if mapeo_data.get('balance_report'):
                content_parts.append(self._create_balance_section(mapeo_data))
                self.report_sections.append("Balance Validation")
                
                unbalanced_section = self._create_unbalanced_entries_section(mapeo_data)
                if unbalanced_section:
                    content_parts.append(unbalanced_section)
                    self.report_sections.append("Unbalanced Entries Sample")
            
            if mapeo_data.get('csv_info') or (mapeo_data.get('header_file') and mapeo_data.get('detail_file')):
                content_parts.append(self._create_csv_files_section(mapeo_data))
                self.report_sections.append("Output Files")
            
            return "\n\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return f"Error generating report: {str(e)}"
    
    def _create_report_header(self, data: Dict[str, Any]) -> str:
        mapeo_mode = self._detect_mapeo_mode(data)
        return f"""FIELD TRAINING SESSION REPORT - {mapeo_mode.upper()}
{'=' * 60}

Generated: {datetime.now().isoformat()}
Mapeo Mode: {mapeo_mode}"""
    
    def _create_session_info_section(self, data: Dict[str, Any]) -> str:
        lines = ["SESSION INFORMATION:"]
        lines.append(f"  CSV File: {data.get('csv_file', 'N/A')}")
        lines.append(f"  ERP Hint: {data.get('erp_hint', 'Auto-detect')}")
        
        standard_fields_count = 17
        if 'mapeo_stats' in data and 'standard_fields_count' in data['mapeo_stats']:
            standard_fields_count = data['mapeo_stats']['standard_fields_count']
        elif 'user_decisions' in data:
            unique_fields = set(d['field_type'] for d in data['user_decisions'].values())
            standard_fields_count = len(unique_fields)
        
        lines.append(f"  Standard Fields: {standard_fields_count}")
        lines.append(f"  Timestamp: {datetime.now().isoformat()}")
        
        return "\n".join(lines)
    
    def _create_statistics_section(self, data: Dict[str, Any]) -> str:
        lines = ["TRAINING STATISTICS:"]
        
        stats = data.get('mapeo_stats', {})
        for key, value in stats.items():
            formatted_key = key.replace('_', ' ').title()
            lines.append(f"  {formatted_key}: {value}")
        
        return "\n".join(lines)
    
    def _create_automatic_conflict_resolution_section(self, data: Dict[str, Any]) -> str:
        lines = ["AUTOMATIC CONFLICT RESOLUTION:"]
        lines.append("-" * 35)
        
        decisions = data.get('user_decisions', {})
        if not decisions:
            lines.append("  No mapping decisions recorded")
            return "\n".join(lines)
        
        for column_name, decision in decisions.items():
            field_type = decision.get('field_type', 'Unknown')
            resolution_type = decision.get('resolution_type', 'unknown')
            
            if resolution_type == 'no_conflict':
                lines.append(f"   {field_type}: {column_name} (no conflict)")
            else:
                lines.append(f"   {field_type}: {column_name} (conflict resolved - {resolution_type})")
        
        return "\n".join(lines)
    
    def _create_confidence_filter_section(self, data: Dict[str, Any]) -> str:
        lines = ["APPLYING CONFIDENCE FILTER:"]
        
        threshold = 0.75
        if 'confidence_threshold' in data:
            threshold = data['confidence_threshold']
        
        lines.append(f"Threshold: {threshold}")
        lines.append("-" * 40)
        
        decisions = data.get('user_decisions', {})
        if not decisions:
            lines.append("  No decisions to filter")
            return "\n".join(lines)
        
        accepted_count = 0
        rejected_count = 0
        
        for column_name, decision in decisions.items():
            field_type = decision.get('field_type', 'Unknown')
            confidence = decision.get('confidence', 0.0)
            
            if confidence >= threshold:
                status = "ACCEPTED"
                accepted_count += 1
            else:
                status = "REJECTED (low confidence)"
                rejected_count += 1
            
            lines.append(f"   {column_name}: {field_type} ({confidence:.3f}) - {status}")
        
        lines.append(f"\n   Final: {accepted_count} accepted, {rejected_count} rejected")
        
        return "\n".join(lines)
    
    def _create_datetime_validations_section(self, data: Dict[str, Any]) -> str:
        lines = ["DATE/TIME FIELD VALIDATIONS:"]
        lines.append("=" * 35)
        
        decisions = data.get('user_decisions', {})
        
        datetime_fields = []
        for column_name, decision in decisions.items():
            field_type = decision.get('field_type', '')
            if field_type in ['posting_date', 'entry_date', 'entry_time']:
                datetime_fields.append((field_type, column_name))
        
        if not datetime_fields:
            lines.append("  No date/time fields detected")
            return "\n".join(lines)
        
        for field_type, column_name in datetime_fields:
            lines.append(f"  {field_type}: {column_name} - Validated")
        
        if any(ft == 'entry_time' for ft, _ in datetime_fields):
            lines.append("  DateTime separation: Time extracted from combined fields")
        elif any(ft == 'posting_date' for ft, _ in datetime_fields):
            lines.append("  DateTime handling: Pure date format detected")
        
        return "\n".join(lines)
    
    def _create_numeric_processing_section(self, data: Dict[str, Any]) -> str:
        lines = ["NUMERIC FIELDS PROCESSING:"]
        lines.append("=" * 30)
        
        mapeo_stats = data.get('mapeo_stats', {})
        decisions = data.get('user_decisions', {})
        
        numeric_fields = []
        for column_name, decision in decisions.items():
            field_type = decision.get('field_type', '')
            if field_type in ['debit_amount', 'credit_amount', 'amount', 'gl_account_number']:
                numeric_fields.append(field_type)
        
        if not numeric_fields:
            lines.append("  No numeric fields detected")
            return "\n".join(lines)
        
        lines.append(f"  Numeric fields found: {numeric_fields}")
        
        fields_cleaned = mapeo_stats.get('fields_cleaned', 0)
        zero_filled = mapeo_stats.get('zero_filled_fields', 0)
        
        if fields_cleaned > 0:
            lines.append(f"  Fields cleaned: {fields_cleaned}")
        
        if zero_filled > 0:
            lines.append(f"  Zero-filled values: {zero_filled}")
        
        if 'debit_amount' in numeric_fields and 'credit_amount' in numeric_fields:
            lines.append(f"  Amount calculation: amount = debit_amount - credit_amount")
        
        return "\n".join(lines)
    
    def _create_decisions_section(self, data: Dict[str, Any]) -> str:
        lines = ["MAPPING DECISIONS:"]
        
        decisions = data.get('user_decisions', {})
        if not decisions:
            lines.append("  No decisions recorded")
            return "\n".join(lines)
        
        automatic_decisions = []
        manual_decisions = []
        conflict_decisions = []
        
        for column, decision in decisions.items():
            decision_type = decision.get('decision_type', 'unknown')
            confidence = decision.get('confidence', 0.0)
            field_type = decision.get('field_type', 'unknown')
            
            decision_line = f"  {column} -> {field_type} (confidence: {confidence:.3f}, type: {decision_type})"
            
            if 'automatic' in decision_type.lower():
                automatic_decisions.append(decision_line)
            elif 'manual' in decision_type.lower():
                manual_decisions.append(decision_line)
            elif 'conflict' in decision_type.lower():
                conflict_decisions.append(decision_line)
            else:
                lines.append(decision_line)
        
        if automatic_decisions:
            lines.append("  Automatic Decisions:")
            lines.extend(f"    {line[2:]}" for line in automatic_decisions)
        
        if manual_decisions:
            lines.append("  Manual Decisions:")
            lines.extend(f"    {line[2:]}" for line in manual_decisions)
        
        if conflict_decisions:
            lines.append("  Conflict Resolutions:")
            lines.extend(f"    {line[2:]}" for line in conflict_decisions)
        
        return "\n".join(lines)
    
    def _create_conflicts_section(self, data: Dict[str, Any]) -> str:
        lines = ["CONFLICT RESOLUTIONS:"]
        
        conflicts = data.get('conflict_resolutions', {})
        if not conflicts:
            lines.append("  No conflicts to resolve")
            return "\n".join(lines)
        
        for field_type, resolution in conflicts.items():
            lines.append(f"  {field_type}:")
            lines.append(f"    Winner: {resolution.get('winner', 'N/A')}")
            lines.append(f"    Resolution type: {resolution.get('resolution_type', 'N/A')}")
            
            all_candidates = resolution.get('all_candidates', [])
            if all_candidates:
                lines.append(f"    All candidates: {all_candidates}")
        
        return "\n".join(lines)
    
    def _create_mapping_table_section(self, data: Dict[str, Any]) -> str:
        lines = ["FINAL MAPPING TABLE:"]
        lines.append(f"{'Standard Field':<25} | {'Mapped Column':<30} | {'Confidence':<10}")
        lines.append(f"{'-'*25} | {'-'*30} | {'-'*10}")
        
        standard_fields = self._get_standard_fields_list(data)
        decisions = data.get('user_decisions', {})
        
        for standard_field in standard_fields:
            mapped_column = "No mapeado"
            confidence = "0.000"
            
            for column_name, decision in decisions.items():
                if decision['field_type'] == standard_field:
                    mapped_column = column_name
                    confidence = f"{decision['confidence']:.3f}"
                    break
            
            lines.append(f"{standard_field:<25} | {mapped_column:<30} | {confidence:<10}")
        
        return "\n".join(lines)
    
    def _create_balance_section(self, data: Dict[str, Any]) -> str:
        lines = ["BALANCE VALIDATION RESULTS:"]
        
        balance = data.get('balance_report', {})
        if not balance:
            lines.append("  No balance validation performed")
            return "\n".join(lines)
        
        entries_count = balance.get('entries_count', 0)
        balanced_count = balance.get('balanced_entries_count', 0)
        
        if entries_count > 0:
            unbalanced_count = entries_count - balanced_count
            lines.append(f"  ENTRY-LEVEL BALANCE CHECK:")
            lines.append(f"  Total Entries: {entries_count}")
            lines.append(f"  Balanced: {balanced_count}")
            lines.append(f"  Unbalanced: {unbalanced_count}")
            
            if unbalanced_count == 0:
                lines.append(f"  Status: All entries are balanced!")
            else:
                balance_rate = (balanced_count / entries_count) * 100
                lines.append(f"  Balance Rate: {balance_rate:.1f}%")
        
        cross_validation = balance.get('cross_validation', {})
        if cross_validation:
            total_rows = cross_validation.get('total_rows', 0)
            matching_rows = cross_validation.get('matching_rows', 0)
            match_rate = cross_validation.get('match_rate', 0)
            discrepancies = cross_validation.get('discrepancies', 0)
            
            lines.append(f"  ")
            lines.append(f"  CROSS-VALIDATION WITH AMOUNT FIELD:")
            lines.append(f"  Amount field matches debit-credit: {matching_rows}/{total_rows}")
            lines.append(f"  Match rate: {match_rate * 100:.1f}%")
            
            if discrepancies > 0:
                lines.append(f"  Significant discrepancies found: {discrepancies}")
        
        total_debit = balance.get('total_debit_sum', 0)
        total_credit = balance.get('total_credit_sum', 0)
        is_balanced = balance.get('is_balanced', False)
        
        if total_debit > 0 or total_credit > 0:
            difference = balance.get('total_balance_difference', 0)
            lines.append(f"  ")
            lines.append(f"  OVERALL TOTALS:")
            lines.append(f"  Total Balance: {'BALANCED' if is_balanced else 'UNBALANCED'}")
            lines.append(f"  Total Debit: {total_debit:,.2f}")
            lines.append(f"  Total Credit: {total_credit:,.2f}")
            lines.append(f"  Difference: {difference:,.2f}")
        
        return "\n".join(lines)
    
    def _create_unbalanced_entries_section(self, data: Dict[str, Any]) -> str:
        balance = data.get('balance_report', {})
        unbalanced_entries = balance.get('unbalanced_entries', [])
        
        if not unbalanced_entries or len(unbalanced_entries) == 0:
            return None
        
        lines = ["UNBALANCED ENTRIES SAMPLE:"]
        lines.append("=" * 30)
        
        sample_size = min(10, len(unbalanced_entries))
        lines.append(f"Showing {sample_size} of {len(unbalanced_entries)} unbalanced entries:")
        lines.append("")
        
        lines.append(f"{'Entry ID':<15} | {'Debit':<12} | {'Credit':<12} | {'Difference':<12}")
        lines.append(f"{'-'*15} | {'-'*12} | {'-'*12} | {'-'*12}")
        
        for i, entry in enumerate(unbalanced_entries[:sample_size]):
            entry_id = str(entry.get('journal_entry_id', 'N/A'))[:14]
            debit = entry.get('debit_amount', 0)
            credit = entry.get('credit_amount', 0)
            diff = entry.get('balance_difference', 0)
            
            lines.append(f"{entry_id:<15} | {debit:>12.2f} | {credit:>12.2f} | {diff:>12.2f}")
        
        if len(unbalanced_entries) > sample_size:
            remaining = len(unbalanced_entries) - sample_size
            lines.append(f"... and {remaining} more unbalanced entries")
        
        return "\n".join(lines)
    
    def _create_csv_files_section(self, data: Dict[str, Any]) -> str:
        lines = ["OUTPUT FILES CREATED:"]
        
        if data.get('header_file'):
            lines.append(f"  Header CSV: {data['header_file']}")
        
        if data.get('detail_file'):
            lines.append(f"  Detail CSV: {data['detail_file']}")
        
        csv_info = data.get('csv_info', {})
        if csv_info:
            if csv_info.get('header_columns'):
                lines.append(f"  Header columns: {', '.join(csv_info['header_columns'])}")
            
            if csv_info.get('detail_columns'):
                lines.append(f"  Detail columns: {', '.join(csv_info['detail_columns'])}")
        
        return "\n".join(lines)
    
    def _detect_mapeo_mode(self, data: Dict[str, Any]) -> str:
        if 'mapeo_mode' in data:
            return data['mapeo_mode']
        
        decisions = data.get('user_decisions', {})
        if not decisions:
            return "Unknown"
        
        decision_types = [d.get('decision_type', '') for d in decisions.values()]
        
        if any('automatic' in dt.lower() for dt in decision_types):
            return "Automatic"
        elif any('manual' in dt.lower() for dt in decision_types):
            return "Manual Confirmation"
        else:
            return "Interactive"
    
    def _get_standard_fields_list(self, data: Dict[str, Any]) -> List[str]:
        default_fields = [
            'journal_entry_id', 'line_number', 'description', 'line_description',
            'posting_date', 'fiscal_year', 'period_number', 'gl_account_number',
            'amount', 'debit_amount', 'credit_amount', 'debit_credit_indicator',
            'prepared_by', 'entry_date', 'entry_time', 'gl_account_name', 'vendor_id'
        ]
        
        if 'standard_fields' in data:
            return data['standard_fields']
        
        decisions = data.get('user_decisions', {})
        if decisions:
            mapped_fields = set(d['field_type'] for d in decisions.values())
            all_fields = set(default_fields) | mapped_fields
            return sorted(all_fields)
        
        return default_fields


def get_comprehensive_reporter() -> ComprehensiveReporter:
    """Get comprehensive reporter instance"""
    return ComprehensiveReporter()