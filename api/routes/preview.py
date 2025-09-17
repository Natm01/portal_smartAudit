# routes/preview.py
"""
Preview routes with Azure Storage support
"""
import os
import pandas as pd
import tempfile
from fastapi import APIRouter, HTTPException, status, Query
from pathlib import Path

from services.execution_service import get_execution_service
from services.storage.azure_storage_service import get_azure_storage_service
from config.settings import get_settings

router = APIRouter(prefix="/smau-proto/api/import", tags=["preview"])

@router.get("/preview/{execution_id}")
async def get_preview(execution_id: str, rows: int = Query(10, description="Number of rows to preview")):
    """Get file preview with Azure Storage support"""
    execution_service = get_execution_service()
    execution = execution_service.get_execution(execution_id)
    settings = get_settings()
    
    # Determine which file to preview based on processing stage
    file_to_preview = None
    temp_file_created = False
    local_file_path = None
    
    try:
        if execution.result_path and execution.result_path != "":
            file_to_preview = execution.result_path
        elif execution.status == "completed" and execution.step == "validation":
            file_to_preview = execution.file_path
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No preview available at current processing stage"
            )
        
        # Handle Azure Storage files
        if file_to_preview.startswith("azure://") and settings.use_azure_storage:
            azure_service = get_azure_storage_service()
            
            # Check if file exists in Azure
            if not azure_service.file_exists(file_to_preview):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found in Azure Storage"
                )
            
            # Download to temporary location for preview
            temp_dir = tempfile.gettempdir()
            filename = Path(file_to_preview).name.split('_', 1)[-1]  # Remove execution_id prefix
            local_file_path = os.path.join(temp_dir, f"temp_preview_{execution_id}_{filename}")
            
            azure_service.download_file(file_to_preview, local_file_path)
            temp_file_created = True
        else:
            # Local file
            local_file_path = file_to_preview
            if not os.path.exists(local_file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )
        
        # Read and process file for preview
        try:
            file_ext = os.path.splitext(local_file_path)[1].lower()
            
            if file_ext == '.csv':
                df = pd.read_csv(local_file_path, nrows=rows)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(local_file_path, nrows=rows)
            elif file_ext == '.txt':
                with open(local_file_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines()[:rows]]
                df = pd.DataFrame({"text": lines})
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file format for preview: {file_ext}"
                )
            
            # Handle NaN values before JSON serialization
            df_cleaned = df.fillna("")
            
            # Add metadata about storage type
            preview_data = {
                "data": df_cleaned.to_dict(orient="records"),
                "metadata": {
                    "total_rows_previewed": len(df_cleaned),
                    "total_columns": len(df_cleaned.columns),
                    "storage_type": "azure" if file_to_preview.startswith("azure://") else "local",
                    "file_extension": file_ext,
                    "execution_step": execution.step
                }
            }
            
            return preview_data
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate preview: {str(e)}"
            )
    
    finally:
        # Clean up temporary file
        if temp_file_created and local_file_path and os.path.exists(local_file_path):
            try:
                os.remove(local_file_path)
            except Exception as e:
                print(f"Warning: Could not remove temp file {local_file_path}: {e}")