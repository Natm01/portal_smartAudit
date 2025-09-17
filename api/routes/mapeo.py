import os
import tempfile
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Query
from fastapi.responses import FileResponse
from pathlib import Path

from services.execution_service import get_execution_service
from services.mapeo_service import get_mapeo_service
from services.storage.azure_storage_service import get_azure_storage_service
from utils.serialization import safe_json_response

router = APIRouter(prefix="/smau-proto/api/import", tags=["mapeo"])

async def run_mapeo_background(execution_id: str, erp_hint: Optional[str] = None):
    """Clean background task for running mapeo"""
    execution_service = get_execution_service()
    mapeo_service = get_mapeo_service()
    
    try:
        execution_service.update_execution(
            execution_id,
            status="processing",
            step="mapeo"
        )
        
        execution = execution_service.get_execution(execution_id)
        
        # Validate file path
        result_path = execution.result_path
        if not result_path:
            raise RuntimeError("No result file path found in execution")
        
        # Run mapeo
        mapeo_result = await mapeo_service.run_mapeo(
            result_path,
            execution_id,
            erp_hint
        )
        
        # Validate mapeo result
        if mapeo_result is None:
            raise RuntimeError("Mapeo service returned None result")
        
        if not mapeo_result.get('success', False):
            error_msg = mapeo_result.get('error', 'Unknown mapeo error')
            raise RuntimeError(f"Mapeo failed: {error_msg}")
        
        # Check if manual mapping is required
        manual_mapping_required = mapeo_result.get('manual_mapping_required', False)
        unmapped_count = mapeo_result.get('unmapped_fields_count', 0)
        
        if manual_mapping_required:
            # Update execution to indicate manual mapping is required
            execution_service.update_execution(
                execution_id,
                status="completed",
                step="mapeo_completed_manual_required",
                mapeo_results=mapeo_result,
                manual_mapping_required=True,
                unmapped_fields_count=unmapped_count
            )
        else:
            # Complete mapeo process normally
            execution_service.update_execution(
                execution_id,
                status="completed",
                step="mapeo_completed",
                mapeo_results=mapeo_result,
                manual_mapping_required=False,
                unmapped_fields_count=0
            )
        
    except Exception as e:
        error_msg = str(e)
        execution_service.update_execution(
            execution_id,
            status="failed",
            step="mapeo_failed",
            error=f"Mapeo error: {error_msg}"
        )


@router.post("/mapeo/{execution_id}")
async def start_automatic_mapeo(
    execution_id: str, 
    background_tasks: BackgroundTasks, 
    erp_hint: Optional[str] = Query(None, description="ERP system hint")
):
    """Start automatic mapeo with clean validation"""
    execution_service = get_execution_service()
    
    try:
        # Verify execution exists and conversion is complete
        execution = execution_service.get_execution(execution_id)
        
        if execution.status != "completed" or execution.step != "conversion_completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversion must be completed before mapeo"
            )
        
        # Verify result file exists
        if not execution.result_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No result file found for mapeo"
            )
        
        # Start mapeo in background
        background_tasks.add_task(run_mapeo_background, execution_id, erp_hint)
        
        return {
            "execution_id": execution_id,
            "message": "Automatic mapeo started",
            "input_file": execution.result_path,
            "erp_hint": erp_hint,
            "status": "started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start mapeo: {str(e)}"
        )


@router.get("/mapeo/{execution_id}/status")
async def get_mapeo_status(execution_id: str):
    """Get mapeo status with enhanced information"""
    execution_service = get_execution_service()
    
    try:
        execution = execution_service.get_execution(execution_id)
        
        response = {
            "execution_id": execution_id,
            "status": execution.status,
            "step": execution.step,
            "updated_at": execution.updated_at,
            "manual_mapping_required": getattr(execution, 'manual_mapping_required', False),
            "unmapped_fields_count": getattr(execution, 'unmapped_fields_count', 0)
        }
        
        # Add mapeo results if available
        if hasattr(execution, 'mapeo_results') and execution.mapeo_results:
            response["mapeo_results"] = execution.mapeo_results
            
            # Enhanced files availability check
            files_available = {}
            for file_type in ['header_file', 'detail_file', 'report_file']:
                file_path = execution.mapeo_results.get(file_type)
                if file_path:
                    files_available[file_type.replace('_file', '_csv' if 'csv' in file_type else '')] = True
                else:
                    files_available[file_type.replace('_file', '_csv' if 'csv' in file_type else '')] = False
            
            response["files_available"] = files_available
        
        if hasattr(execution, 'error') and execution.error:
            response["error"] = execution.error
        
        return safe_json_response(response)
        
    except Exception as e:
        return {
            "execution_id": execution_id,
            "status": "error",
            "error": str(e)
        }


@router.get("/mapeo/{execution_id}/unmapped-fields")
async def get_unmapped_fields(execution_id: str):
    """Get unmapped fields that require manual mapping"""
    execution_service = get_execution_service()
    mapeo_service = get_mapeo_service()
    
    try:
        execution = execution_service.get_execution(execution_id)
        
        if not hasattr(execution, 'mapeo_results') or not execution.mapeo_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mapeo not completed yet"
            )
        
        # Get the source file for analysis
        source_file = execution.result_path
        if not source_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No result file available for analysis"
            )
        
        # Get unmapped fields analysis
        analysis = mapeo_service.get_unmapped_fields_analysis(source_file, execution.mapeo_results)
        
        if 'error' in analysis:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error analyzing unmapped fields: {analysis['error']}"
            )
        
        response_message = f"Found {analysis['total_unmapped']} fields requiring manual mapping"
        if analysis['total_unmapped'] == 0:
            response_message = "All fields have been mapped successfully"
        
        return {
            "execution_id": execution_id,
            "unmapped_fields": analysis['unmapped_fields'],
            "available_standard_fields": analysis['available_standard_fields'],
            "total_unmapped": analysis['total_unmapped'],
            "total_available_fields": analysis['total_available_fields'],
            "message": response_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting unmapped fields: {str(e)}"
        )


@router.get("/mapeo/{execution_id}/download/{file_type}")
async def download_mapeo_file(execution_id: str, file_type: str):
    """Download mapeo files with clean Azure Storage support"""
    execution_service = get_execution_service()
    azure_service = get_azure_storage_service()
    execution = execution_service.get_execution(execution_id)
    
    try:
        if not hasattr(execution, 'mapeo_results') or not execution.mapeo_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mapeo not completed yet"
            )
        
        file_map = {
            'header': execution.mapeo_results.get('header_file'),
            'detail': execution.mapeo_results.get('detail_file'),
            'report': execution.mapeo_results.get('report_file')
        }
        
        if file_type not in file_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Must be one of: {list(file_map.keys())}"
            )
        
        file_path = file_map[file_type]
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{file_type.title()} file not found"
            )
        
        local_file_path = file_path
        temp_file_created = False
        
        # Handle Azure Storage files
        if file_path.startswith("azure://"):
            temp_file_path = tempfile.NamedTemporaryFile(delete=False).name
            
            try:
                azure_service.download_file(file_path, temp_file_path)
                temp_file_created = True
                local_file_path = temp_file_path
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error downloading file from storage: {str(e)}"
                )
        
        # Verify local file exists
        if not os.path.exists(local_file_path):
            if temp_file_created and os.path.exists(local_file_path):
                try:
                    os.remove(local_file_path)
                except Exception:
                    pass
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk"
            )
        
        # Determine filename and media type
        if file_type == 'report':
            download_filename = f"mapeo_report_{execution_id}.txt"
            media_type = "text/plain"
        else:
            download_filename = f"mapeo_{file_type}_{execution_id}.csv"
            media_type = "text/csv"
        
        # Create FileResponse with proper background task for cleanup
        if temp_file_created:
            from starlette.background import BackgroundTask
            
            def cleanup_temp_file():
                try:
                    if os.path.exists(local_file_path):
                        os.remove(local_file_path)
                except Exception:
                    pass
            
            response = FileResponse(
                path=local_file_path,
                filename=download_filename,
                media_type=media_type,
                background=BackgroundTask(cleanup_temp_file)
            )
        else:
            response = FileResponse(
                path=local_file_path,
                filename=download_filename,
                media_type=media_type
            )
        
        return response
        
    except HTTPException:
        # Clean up temp file on HTTP error
        if 'temp_file_created' in locals() and temp_file_created and 'local_file_path' in locals():
            try:
                if os.path.exists(local_file_path):
                    os.remove(local_file_path)
            except Exception:
                pass
        raise
    except Exception as e:
        # Clean up temp file on general error
        if 'temp_file_created' in locals() and temp_file_created and 'local_file_path' in locals():
            try:
                if os.path.exists(local_file_path):
                    os.remove(local_file_path)
            except Exception:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download error: {str(e)}"
        )


@router.get("/mapeo/{execution_id}/summary")
async def get_mapeo_summary(execution_id: str):
    """Get mapeo summary with enhanced information"""
    execution_service = get_execution_service()
    
    try:
        execution = execution_service.get_execution(execution_id)
        
        if not hasattr(execution, 'mapeo_results') or not execution.mapeo_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mapeo not completed yet"
            )
        
        mapeo_stats = execution.mapeo_results.get('mapeo_stats', {})
        
        response = {
            "execution_id": execution_id,
            "trainer_type": execution.mapeo_results.get('trainer_type', 'automatic'),
            "summary": {
                "columns_processed": mapeo_stats.get('columns_processed', 0),
                "automatic_mappings": mapeo_stats.get('automatic_mappings', 0),
                "high_confidence_mappings": mapeo_stats.get('high_confidence_mappings', 0),
                "low_confidence_mappings": mapeo_stats.get('low_confidence_mappings', 0),
                "unmapped_columns": mapeo_stats.get('unmapped_columns', 0),
                "manual_mappings": mapeo_stats.get('manual_mappings', 0)
            },
            "files_created": {
                "header_file": execution.mapeo_results.get('header_file'),
                "detail_file": execution.mapeo_results.get('detail_file'),
                "report_file": execution.mapeo_results.get('report_file')
            },
            "warning": execution.mapeo_results.get('warning'),
            "manual_mapping_required": execution.mapeo_results.get('manual_mapping_required', False),
            "unmapped_fields_count": execution.mapeo_results.get('unmapped_fields_count', 0),
            "storage_info": {
                "storage_type": "azure",
                "files_in_cloud": True
            }
        }
        
        return safe_json_response(response)
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "execution_id": execution_id,
            "status": "error",
            "error": str(e)
        }

@router.get("/mapeo/{execution_id}/fields-mapping")
async def get_fields_mapping_status(execution_id: str):
    """Get detailed mapping status showing mapped fields and missing standard fields"""
    execution_service = get_execution_service()
    mapeo_service = get_mapeo_service()
    
    try:
        execution = execution_service.get_execution(execution_id)
        
        if not hasattr(execution, 'mapeo_results') or not execution.mapeo_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mapeo not completed yet"
            )
        
        mapeo_results = execution.mapeo_results
        user_decisions = mapeo_results.get('user_decisions', {})
        mapeo_stats = mapeo_results.get('mapeo_stats', {})
        
        # Reutilizar campos estándar del servicio existente
        standard_fields = mapeo_service.standard_fields
        
        # Analizar campos mapeados
        mapped_fields = {}
        mapped_field_types = set()
        
        for column_name, decision in user_decisions.items():
            field_type = decision.get('field_type')
            mapped_field_types.add(field_type)
            mapped_fields[field_type] = {
                'mapped_column': column_name,
                'confidence': decision.get('confidence', 0.0),
                'decision_type': decision.get('decision_type', 'unknown'),
                'is_manual': 'manual' in decision.get('decision_type', '').lower()
            }
        
        # Identificar campos faltantes
        missing_fields = [field for field in standard_fields if field not in mapped_field_types]
        
        # Clasificar por criticidad (usando lógica similar a la existente)
        critical_fields = {'journal_entry_id', 'amount', 'posting_date'}
        missing_critical = [f for f in missing_fields if f in critical_fields]
        
        # Calcular completitud
        completeness = len(mapped_field_types) / len(standard_fields) * 100
        critical_completeness = len([f for f in critical_fields if f in mapped_field_types]) / len(critical_fields) * 100
        
        # Generar recomendaciones simples
        recommendations = []
        if missing_critical:
            recommendations.append({
                'type': 'critical',
                'message': f'Faltan campos críticos: {", ".join(missing_critical)}',
                'fields': missing_critical
            })
        
        if mapeo_results.get('manual_mapping_required', False):
            recommendations.append({
                'type': 'manual_required',
                'message': f'Se requiere mapeo manual para {mapeo_results.get("unmapped_fields_count", 0)} campos'
            })
        
        response = {
            "execution_id": execution_id,
            "mapping_summary": {
                "total_standard_fields": len(standard_fields),
                "mapped_fields_count": len(mapped_field_types),
                "missing_fields_count": len(missing_fields),
                "completeness_percentage": round(completeness, 1),
                "critical_completeness_percentage": round(critical_completeness, 1),
                "needs_manual_mapping": mapeo_results.get('manual_mapping_required', False)
            },
            "mapped_fields": mapped_fields,
            "missing_fields": missing_fields,
            "critical_missing": missing_critical,
            "recommendations": recommendations,
            "mapeo_stats": mapeo_stats
        }
        
        return safe_json_response(response)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving fields mapping status: {str(e)}"
        )