# routes/conversion.py
"""
Conversion routes
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from models.execution import ConversionResponse
from services.execution_service import get_execution_service
from services.conversion_service import get_conversion_service
from utils.serialization import safe_json_response

router = APIRouter()

async def convert_file_background(execution_id: str):
    """Background task for file conversion"""
    execution_service = get_execution_service()
    conversion_service = get_conversion_service()
    
    try:
        execution_service.update_execution(
            execution_id,
            status="processing",
            step="conversion"
        )
        
        execution = execution_service.get_execution(execution_id)
        
        # Update step for model prediction
        execution_service.update_execution(execution_id, step="model_prediction")
        
        # Perform conversion
        conversion_result = await conversion_service.convert_file(
            execution.file_path, 
            execution_id
        )
        
        # Update execution with results
        execution_service.update_execution(
            execution_id,
            status="completed",
            step="conversion_completed",
            result_path=conversion_result["result_path"],
            stats=conversion_result["stats"]
        )
        
    except Exception as e:
        print(f"Error in conversion: {str(e)}")
        execution_service.update_execution(
            execution_id,
            status="failed",
            error=f"Conversion process error: {str(e)}"
        )

@router.post("/convert/{execution_id}", response_model=ConversionResponse)
async def convert_import(execution_id: str, background_tasks: BackgroundTasks):
    """Start file conversion"""
    execution_service = get_execution_service()
    
    # Verify execution exists and is ready
    execution = execution_service.get_execution(execution_id)
    
    if execution.status != "completed" or execution.step != "validation":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be successfully validated before conversion"
        )
    
    # Start conversion in background
    background_tasks.add_task(convert_file_background, execution_id)
    
    return ConversionResponse(
        execution_id=execution_id,
        message="Conversion started"
    )

@router.get("/convert/{execution_id}/status")
async def get_conversion_status(execution_id: str):
    """Get conversion status"""
    execution_service = get_execution_service()
    return execution_service.get_execution_safe(execution_id)