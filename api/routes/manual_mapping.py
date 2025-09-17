# routes/manual_mapping.py - PYDANTIC MODELS FIXED
"""
Manual mapping routes for unmapped fields - FIXED PYDANTIC MODELS
"""
from typing import Dict, List, Optional, Any, Union
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import pandas as pd
import tempfile
import os

from services.execution_service import get_execution_service
from services.mapeo_service import get_mapeo_service
from services.storage.azure_storage_service import get_azure_storage_service
from config.settings import get_settings
from utils.serialization import safe_json_response

router = APIRouter()

# FIXED: Pydantic models with correct typing
class FieldSuggestion(BaseModel):
    """Individual field suggestion"""
    field: str
    reason: str
    confidence: float

class UnmappedField(BaseModel):
    """Unmapped field information - FIXED TYPING"""
    column_name: str
    sample_data: List[str]
    data_type: str
    suggestions: List[FieldSuggestion]  # FIXED: Use proper model instead of Dict[str, any]
    total_values: int
    non_null_values: int
    unique_values: int

class MappingDecision(BaseModel):
    """User's mapping decision"""
    column_name: str
    selected_field: str
    confidence: float = 0.8

class ManualMappingRequest(BaseModel):
    """Request to apply manual mappings"""
    mappings: List[MappingDecision]

class ManualMappingResponse(BaseModel):
    """Response with unmapped fields"""
    execution_id: str
    unmapped_fields: List[UnmappedField]
    available_standard_fields: List[str]
    message: str

class ApplyMappingResponse(BaseModel):
    """Response after applying mappings"""
    execution_id: str
    applied_mappings: int
    updated_decisions: Dict[str, str]
    regenerated_files: Dict[str, Optional[str]]
    message: str

@router.get("/mapeo/{execution_id}/unmapped", response_model=ManualMappingResponse)
async def get_unmapped_fields(execution_id: str):
    """Get fields that couldn't be mapped automatically for manual mapping - FIXED"""
    execution_service = get_execution_service()
    mapeo_service = get_mapeo_service()
    
    try:
        print(f"BUGS - MANUAL MAPPING: Getting unmapped fields for execution {execution_id}")
        
        execution = execution_service.get_execution(execution_id)
        
        # Check if mapeo has been completed
        if not hasattr(execution, 'mapeo_results') or not execution.mapeo_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mapeo not completed yet"
            )
        
        if not execution.mapeo_results.get('success'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mapeo failed, cannot get unmapped fields"
            )
        
        print(f"BUGS - MANUAL MAPPING: Mapeo results found, checking for unmapped fields")
        
        # Get the source file for analysis
        source_file = execution.result_path
        if not source_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No result file available for analysis"
            )
        
        print(f"BUGS - MANUAL MAPPING: Analyzing unmapped fields from file: {source_file}")
        
        # Get unmapped fields analysis
        analysis = mapeo_service.get_unmapped_fields_analysis(source_file, execution.mapeo_results)
        
        if 'error' in analysis:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error analyzing unmapped fields: {analysis['error']}"
            )
        
        # Convert analysis to proper Pydantic models
        unmapped_fields_list = []
        for field_data in analysis['unmapped_fields']:
            # Convert suggestions to proper FieldSuggestion models
            suggestions = []
            for suggestion in field_data.get('suggestions', []):
                if isinstance(suggestion, dict) and 'field' in suggestion:
                    suggestions.append(FieldSuggestion(
                        field=suggestion['field'],
                        reason=suggestion.get('reason', 'unknown'),
                        confidence=suggestion.get('confidence', 0.5)
                    ))
            
            unmapped_fields_list.append(UnmappedField(
                column_name=field_data['column_name'],
                sample_data=field_data['sample_data'],
                data_type=field_data['data_type'],
                suggestions=suggestions,
                total_values=field_data['total_values'],
                non_null_values=field_data['non_null_values'],
                unique_values=field_data['unique_values']
            ))
        
        response_message = f"Found {analysis['total_unmapped']} unmapped fields"
        if analysis['total_unmapped'] == 0:
            response_message = "All fields have been mapped successfully"
        
        print(f"BUGS - MANUAL MAPPING: {response_message}")
        
        return ManualMappingResponse(
            execution_id=execution_id,
            unmapped_fields=unmapped_fields_list,
            available_standard_fields=analysis['available_standard_fields'],
            message=response_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"BUGS - MANUAL MAPPING: Error in get_unmapped_fields: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing unmapped fields: {str(e)}"
        )

@router.post("/mapeo/{execution_id}/apply-manual-mapping", response_model=ApplyMappingResponse)
async def apply_manual_mapping(execution_id: str, mapping_request: ManualMappingRequest):
    """Apply manual mappings selected by user - ENHANCED"""
    execution_service = get_execution_service()
    
    try:
        print(f"BUGS - MANUAL MAPPING: Applying manual mappings for execution {execution_id}")
        
        execution = execution_service.get_execution(execution_id)
        
        if not hasattr(execution, 'mapeo_results') or not execution.mapeo_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mapeo not completed yet"
            )
        
        # Get current user decisions
        current_decisions = execution.mapeo_results.get('user_decisions', {}).copy()
        
        # Validate and apply new mappings
        applied_mappings = {}
        validation_errors = []
        
        # Get already used fields to prevent duplicates
        used_fields = set(decision['field_type'] for decision in current_decisions.values())
        
        # Validate and apply new mappings
        for mapping in mapping_request.mappings:
            # Validate field is not already used
            if mapping.selected_field in used_fields:
                validation_errors.append(
                    f"Field '{mapping.selected_field}' is already mapped to another column"
                )
                continue
            
            # Add new mapping decision
            current_decisions[mapping.column_name] = {
                'field_type': mapping.selected_field,
                'confidence': mapping.confidence,
                'decision_type': 'manual_mapping',
                'resolution_type': 'manual_selection'
            }
            
            applied_mappings[mapping.column_name] = mapping.selected_field
            used_fields.add(mapping.selected_field)
        
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation errors: {'; '.join(validation_errors)}"
            )
        
        # Update mapeo results with new decisions
        updated_mapeo_results = execution.mapeo_results.copy()
        updated_mapeo_results['user_decisions'] = current_decisions
        
        # Update statistics
        mapeo_stats = updated_mapeo_results.get('mapeo_stats', {})
        mapeo_stats['manual_mappings'] = mapeo_stats.get('manual_mappings', 0) + len(applied_mappings)
        mapeo_stats['columns_processed'] = mapeo_stats.get('columns_processed', 0) + len(applied_mappings)
        updated_mapeo_results['mapeo_stats'] = mapeo_stats
        
        # Regenerate CSV files with new mappings
        regenerated_files = await _regenerate_mapeo_files(execution, current_decisions)
        
        # Update mapeo results with new file paths
        if regenerated_files.get('header_file'):
            updated_mapeo_results['header_file'] = regenerated_files['header_file']
        if regenerated_files.get('detail_file'):
            updated_mapeo_results['detail_file'] = regenerated_files['detail_file']
        if regenerated_files.get('report_file'):
            updated_mapeo_results['report_file'] = regenerated_files['report_file']
        
        # Update execution
        execution_service.update_execution(
            execution_id,
            mapeo_results=updated_mapeo_results,
            manual_mapping_required=False,  # Manual mapping completed
            unmapped_fields_count=0
        )
        
        print(f"BUGS - MANUAL MAPPING: Applied {len(applied_mappings)} manual mappings successfully")
        
        return ApplyMappingResponse(
            execution_id=execution_id,
            applied_mappings=len(applied_mappings),
            updated_decisions=applied_mappings,
            regenerated_files=regenerated_files,
            message=f"Successfully applied {len(applied_mappings)} manual mappings and regenerated output files"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"BUGS - MANUAL MAPPING: Error applying manual mappings: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying manual mappings: {str(e)}"
        )

async def _regenerate_mapeo_files(execution, user_decisions: Dict) -> Dict[str, Optional[str]]:
    """Regenerate mapeo CSV files with updated mappings"""
    try:
        settings = get_settings()
        azure_service = get_azure_storage_service() if settings.use_azure_storage else None
        
        # Get source file
        source_file = execution.result_path
        if not source_file:
            raise RuntimeError("No source file available for regeneration")
        
        # Download source file if it's in Azure
        local_source_file = source_file
        temp_file_created = False
        
        if source_file.startswith("azure://"):
            if not azure_service:
                raise RuntimeError("Azure Storage not configured")
            
            temp_dir = tempfile.gettempdir()
            filename = os.path.basename(source_file.replace("azure://", ""))
            local_source_file = os.path.join(temp_dir, f"regen_{filename}")
            
            azure_service.download_file(source_file, local_source_file)
            temp_file_created = True
        
        try:
            # Read source data
            df = pd.read_csv(local_source_file)
            
            # Apply column mapping
            column_mapping = {col: decision['field_type'] for col, decision in user_decisions.items()}
            transformed_df = df.rename(columns=column_mapping)
            
            # Generate output files using the CSV transformer
            from procesos_mapeo.csv_transformer import IntegratedCSVTransformer
            
            transformer = IntegratedCSVTransformer(
                output_prefix="manual_mapeo",
                apply_numeric_processing=True
            )
            
            # Set Azure awareness if needed
            if azure_service and settings.use_azure_storage:
                transformer.settings = settings
                transformer.azure_service = azure_service
                transformer.execution_id = execution.id
            
            # Define standard fields
            standard_fields = [
                'journal_entry_id', 'line_number', 'description', 'line_description',
                'posting_date', 'fiscal_year', 'period_number', 'gl_account_number',
                'amount', 'debit_amount', 'credit_amount', 'debit_credit_indicator',
                'prepared_by', 'entry_date', 'entry_time', 'gl_account_name', 'vendor_id'
            ]
            
            # Create header/detail CSVs
            result = transformer.create_header_detail_csvs(df, user_decisions, standard_fields)
            
            if not result.get('success'):
                raise RuntimeError(f"Failed to regenerate files: {result.get('error')}")
            
            # Generate updated report
            report_file = await _generate_updated_report(execution, user_decisions, result)
            
            regenerated_files = {
                'header_file': result.get('header_file'),
                'detail_file': result.get('detail_file'),
                'report_file': report_file
            }
            
            print(f"BUGS - MANUAL MAPPING: Files regenerated successfully")
            print(f"BUGS - MANUAL MAPPING: Header: {regenerated_files['header_file']}")
            print(f"BUGS - MANUAL MAPPING: Detail: {regenerated_files['detail_file']}")
            print(f"BUGS - MANUAL MAPPING: Report: {regenerated_files['report_file']}")
            
            return regenerated_files
            
        finally:
            # Clean up temporary source file
            if temp_file_created and os.path.exists(local_source_file):
                try:
                    os.remove(local_source_file)
                    print(f"BUGS - MANUAL MAPPING: Cleaned up temp source file: {local_source_file}")
                except Exception as e:
                    print(f"BUGS - MANUAL MAPPING: Warning - could not clean up temp file: {e}")
        
    except Exception as e:
        print(f"BUGS - MANUAL MAPPING: Error regenerating files: {e}")
        return {
            'header_file': None,
            'detail_file': None,
            'report_file': None
        }

async def _generate_updated_report(execution, user_decisions: Dict, csv_result: Dict) -> Optional[str]:
    """Generate updated report with manual mappings"""
    try:
        from datetime import datetime
        
        settings = get_settings()
        azure_service = get_azure_storage_service() if settings.use_azure_storage else None
        
        # Calculate statistics
        manual_mappings = sum(1 for d in user_decisions.values() if d.get('decision_type') == 'manual_mapping')
        automatic_mappings = len(user_decisions) - manual_mappings
        
        # Generate report content
        report_content = f"""MANUAL MAPPING COMPLETION REPORT
{'=' * 50}

Execution ID: {execution.id}
File: {execution.file_name}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

MAPPING STATISTICS:
{'-' * 20}
Total Mappings: {len(user_decisions)}
Automatic Mappings: {automatic_mappings}
Manual Mappings: {manual_mappings}

FINAL FIELD MAPPINGS:
{'-' * 20}"""

        for column, decision in user_decisions.items():
            mapping_type = "MANUAL" if decision.get('decision_type') == 'manual_mapping' else "AUTO"
            confidence = decision.get('confidence', 0.0)
            report_content += f"\n{column} -> {decision['field_type']} ({mapping_type}, {confidence:.3f})"

        report_content += f"""

OUTPUT FILES GENERATED:
{'-' * 23}
Header CSV: {csv_result.get('header_file', 'Not generated')}
Detail CSV: {csv_result.get('detail_file', 'Not generated')}

PROCESS COMPLETED SUCCESSFULLY
Manual mapping process completed. All unmapped fields have been resolved.
"""

        # Save report
        if azure_service and settings.use_azure_storage:
            report_file = azure_service.upload_from_memory(
                report_content.encode('utf-8'),
                f"manual_mapping_report_{execution.id}.txt",
                container_type="mapeos",
                execution_id=execution.id
            )
        else:
            # Local fallback
            mapeos_dir = "mapeos"
            os.makedirs(mapeos_dir, exist_ok=True)
            report_file = os.path.join(mapeos_dir, f"manual_mapping_report_{execution.id}.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
        
        print(f"BUGS - MANUAL MAPPING: Report generated: {report_file}")
        return report_file
        
    except Exception as e:
        print(f"BUGS - MANUAL MAPPING: Error generating report: {e}")
        return None