# routes/upload.py 
"""
Upload routes with Azure Storage integration optimized for large files
"""
import os
import shutil
import tempfile
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks, Form

from models.execution import UploadResponse
from services.execution_service import get_execution_service
from services.storage.azure_storage_service import get_azure_storage_service
from config.settings import get_settings

# CAMBIO: Agregar el prefijo correcto que espera el frontend
router = APIRouter(prefix="/smau-proto/api/import", tags=["upload"])

class ProgressTracker:
    """Simple progress tracker for large file uploads"""
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.progress = 0
        self.uploaded_bytes = 0
        self.total_bytes = 0
        self.status = "starting"
    
    def update(self, progress: float, uploaded: int, total: int):
        self.progress = progress
        self.uploaded_bytes = uploaded
        self.total_bytes = total
        self.status = "uploading"

# Global progress tracker
upload_progress = {}

async def upload_large_file_background(execution_id: str, file_path: str, azure_service, settings):
    """Background task for uploading large files to Azure Storage"""
    execution_service = get_execution_service()
    
    try:
        progress_tracker = ProgressTracker(execution_id)
        upload_progress[execution_id] = progress_tracker
        
        def progress_callback(progress: float, uploaded: int, total: int):
            progress_tracker.update(progress, uploaded, total)
        
        blob_url = azure_service.upload_file_chunked(
            file_path, 
            execution_id=execution_id,
            progress_callback=progress_callback
        )
        
        execution_service.update_execution(execution_id, file_path=blob_url)
        progress_tracker.status = "completed"
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not remove temp file {file_path}: {e}")
        
    except Exception as e:
        if execution_id in upload_progress:
            upload_progress[execution_id].status = f"failed: {str(e)}"
        
        execution_service.update_execution(execution_id, error=f"Upload failed: {str(e)}")
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

# CAMBIO: Ahora solo necesitas "/upload" porque el prefijo ya está en el router
@router.post("/upload", response_model=UploadResponse)
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a file for processing with optimized large file support"""
    settings = get_settings()
    execution_service = get_execution_service()
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed types: {settings.allowed_extensions}"
        )
    
    execution_id = execution_service.create_execution(file.filename, "")
    
    try:
        if settings.use_azure_storage:
            azure_service = get_azure_storage_service()
            
            file_size = None
            if hasattr(file, 'size') and file.size:
                file_size = file.size
            elif hasattr(file.file, 'seek'):
                try:
                    current_pos = file.file.tell()
                    file.file.seek(0, 2)
                    file_size = file.file.tell()
                    file.file.seek(current_pos)
                except:
                    file_size = None
            
            if file_size and file_size > settings.max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size {file_size} exceeds maximum allowed size {settings.max_file_size}"
                )
            
            large_file_threshold = 50 * 1024 * 1024  # 50MB
            
            if file_size and file_size > large_file_threshold:
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, f"temp_upload_{execution_id}_{file.filename}")
                
                with open(temp_file_path, "wb") as buffer:
                    while True:
                        chunk = await file.read(8 * 1024 * 1024)  # 8MB chunks
                        if not chunk:
                            break
                        buffer.write(chunk)
                
                actual_size = os.path.getsize(temp_file_path)
                if actual_size > settings.max_file_size:
                    os.remove(temp_file_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size {actual_size} exceeds maximum allowed size {settings.max_file_size}"
                    )
                
                background_tasks.add_task(
                    upload_large_file_background, 
                    execution_id, 
                    temp_file_path, 
                    azure_service, 
                    settings
                )
                
                file_path = f"uploading_to_azure://{execution_id}"
                
            else:
                file_content = await file.read()
                
                file_size = len(file_content)
                if file_size > settings.max_file_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size {file_size} exceeds maximum allowed size {settings.max_file_size}"
                    )
                
                blob_url = azure_service.upload_from_memory(
                    file_content, 
                    file.filename, 
                    container_type="upload",
                    execution_id=execution_id
                )
                file_path = blob_url
        else:
            # Local filesystem fallback
            file_content = await file.read()
            
            file_size = len(file_content)
            if file_size > settings.max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size {file_size} exceeds maximum allowed size {settings.max_file_size}"
                )
            
            os.makedirs(settings.full_upload_dir, exist_ok=True)
            file_path = os.path.join(settings.full_upload_dir, file.filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
        
        execution_service.update_execution(execution_id, file_path=file_path)
        
        message = "Large file upload started in background" if file_path.startswith("uploading_to_azure://") else "File uploaded successfully"
        
        return UploadResponse(
            execution_id=execution_id,
            file_name=file.filename,
            message=message
        )
        
    except Exception as e:
        execution_service.delete_execution(execution_id)
        
        if execution_id in upload_progress:
            del upload_progress[execution_id]
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

@router.get("/upload/{execution_id}/progress")
async def get_upload_progress(execution_id: str):
    """Get upload progress for large files"""
    if execution_id not in upload_progress:
        raise HTTPException(
            status_code=404,
            detail="Upload not found or already completed"
        )
    
    progress = upload_progress[execution_id]
    return {
        "execution_id": execution_id,
        "progress": progress.progress,
        "uploaded_bytes": progress.uploaded_bytes,
        "total_bytes": progress.total_bytes,
        "status": progress.status
    }