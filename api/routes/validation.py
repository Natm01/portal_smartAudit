# routes/validation.py - CLEANED
"""
Validation routes
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.execution import ValidationResponse, ExecutionStatus
from services.execution_service import get_execution_service
from services.validation_service import get_validation_service
from utils.serialization import safe_json_response

router = APIRouter(prefix="/smau-proto/api/import", tags=["validate"])

async def validate_file_background(execution_id: str):
    """Background task for file validation"""
    execution_service = get_execution_service()
    validation_service = get_validation_service()
    
    try:
        execution_service.update_execution(
            execution_id,
            status="processing",
            step="validation"
        )
        
        execution = execution_service.get_execution(execution_id)
        
        validation_result = await validation_service.validate_file(execution.file_path)
        
        execution_service.update_execution(
            execution_id,
            status="completed",
            step="validation",
            stats=validation_result["stats"]
        )
        
    except Exception as e:
        print(f"Error in validation: {str(e)}")
        execution_service.update_execution(
            execution_id,
            status="failed",
            error=f"Validation error: {str(e)}"
        )

@router.post("/validate/{execution_id}", response_model=ValidationResponse)
async def validate_import(execution_id: str, background_tasks: BackgroundTasks):
    """Start file validation"""
    execution_service = get_execution_service()
    
    execution_service.get_execution(execution_id)
    
    background_tasks.add_task(validate_file_background, execution_id)
    
    return ValidationResponse(
        execution_id=execution_id,
        message="Validation started"
    )

@router.get("/validate/{execution_id}/status")
async def get_validation_status(execution_id: str):
    """Get validation status"""
    execution_service = get_execution_service()
    return execution_service.get_execution_safe(execution_id)