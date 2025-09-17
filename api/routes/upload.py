# routes/upload.py 
"""
Upload routes with Azure Storage integration optimized for large files
Con nombres estructurados y coordinación de IDs
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

# Prefijo correcto que espera el frontend
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

async def upload_large_file_background(execution_id: str, file_path: str, 
                                     file_type: str, azure_service, settings):
    """Background task for uploading large files to Azure Storage with structured names"""
    execution_service = get_execution_service()
    
    try:
        progress_tracker = ProgressTracker(execution_id)
        upload_progress[execution_id] = progress_tracker
        
        def progress_callback(progress: float, uploaded: int, total: int):
            progress_tracker.update(progress, uploaded, total)
        
        # Usar el nuevo método con file_type para naming estructurado
        blob_url = azure_service.upload_file_chunked(
            file_path, 
            execution_id=execution_id,
            file_type=file_type,  # "Je" o "Sys"
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

def determine_file_type_from_test_type(test_type: str) -> str:
    """
    Determinar el tipo de archivo basado en test_type
    
    Returns:
        "Je" para Journal Entries (Libro Diario)
        "Sys" para Sumas y Saldos
    """
    if test_type and 'sumas' in test_type.lower():
        return "Sys"
    else:
        return "Je"  # Default para libro diario

def get_original_filename(upload_file: UploadFile) -> str:
    """
    Extraer nombre de archivo original limpio
    """
    if not upload_file.filename:
        return "unknown_file"
    
    # Limpiar el nombre de archivo de caracteres especiales si es necesario
    filename = upload_file.filename.strip()
    
    # Remover path si viene incluido
    if '/' in filename:
        filename = filename.split('/')[-1]
    if '\\' in filename:
        filename = filename.split('\\')[-1]
    
    return filename

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    test_type: Optional[str] = Form("libro_diario_import"),
    project_id: Optional[str] = Form(None),
    period: Optional[str] = Form(None),
    parent_execution_id: Optional[str] = Form(None)  # Para coordinar IDs entre LD y SS
):
    """
    Upload a file for processing with structured naming and coordinated IDs
    
    Args:
        file: El archivo a subir
        test_type: Tipo de test (libro_diario_import, sumas_saldos_import)
        project_id: ID del proyecto
        period: Período de la prueba
        parent_execution_id: ID de ejecución padre para coordinar con Sumas y Saldos
    """
    settings = get_settings()
    execution_service = get_execution_service()
    
    original_filename = get_original_filename(file)
    file_ext = os.path.splitext(original_filename)[1].lower()
    
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed types: {settings.allowed_extensions}"
        )
    
    # Determinar el tipo de archivo para la estructura de nombres
    file_type = determine_file_type_from_test_type(test_type or "libro_diario_import")
    
    # Usar el método coordinado del ExecutionService
    if parent_execution_id and file_type == "Sys":
        # Para Sumas y Saldos, crear con parent_execution_id
        execution_id = execution_service.create_coordinated_execution(
            file_name=original_filename,
            file_path="",  # Se actualizará después
            file_type=file_type,
            test_type=test_type,
            project_id=project_id,
            period=period,
            parent_execution_id=parent_execution_id
        )
        
        # Verificar que el parent existe
        try:
            parent_execution = execution_service.get_execution(parent_execution_id)
            print(f"✅ Parent execution found: {parent_execution_id}")
        except:
            print(f"⚠️  Warning: Parent execution {parent_execution_id} not found, proceeding anyway")
    else:
        # Para Libro Diario o casos sin parent
        execution_id = execution_service.create_coordinated_execution(
            file_name=original_filename,
            file_path="",  # Se actualizará después
            file_type=file_type,
            test_type=test_type,
            project_id=project_id,
            period=period,
            parent_execution_id=None
        )
    
    try:
        if settings.use_azure_storage:
            azure_service = get_azure_storage_service()
            
            # Calcular tamaño del archivo
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
                # Archivos grandes: usar background processing
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, f"temp_upload_{execution_id}_{original_filename}")
                
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
                    file_type,  # Pasar el tipo de archivo
                    azure_service, 
                    settings
                )
                
                file_path = f"uploading_to_azure://{execution_id}"
                
            else:
                # Archivos pequeños: subida inmediata con nombres estructurados
                file_content = await file.read()
                
                file_size = len(file_content)
                if file_size > settings.max_file_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size {file_size} exceeds maximum allowed size {settings.max_file_size}"
                    )
                
                # Usar el método específico según el tipo de archivo
                if file_type == "Je":  # Libro Diario
                    blob_url = azure_service.upload_libro_diario_file(
                        file_content, 
                        original_filename,
                        execution_id,
                        container_type="upload"
                    )
                elif file_type == "Sys":  # Sumas y Saldos
                    blob_url = azure_service.upload_sumas_saldos_file(
                        file_content, 
                        original_filename,
                        execution_id,
                        container_type="upload"
                    )
                else:
                    # Fallback genérico
                    blob_url = azure_service.upload_from_memory(
                        file_content, 
                        original_filename, 
                        container_type="upload",
                        execution_id=execution_id,
                        file_type=file_type
                    )
                
                file_path = blob_url
        else:
            # Local filesystem fallback (sin cambios)
            file_content = await file.read()
            
            file_size = len(file_content)
            if file_size > settings.max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size {file_size} exceeds maximum allowed size {settings.max_file_size}"
                )
            
            os.makedirs(settings.full_upload_dir, exist_ok=True)
            
            # Aplicar naming estructurado también en local
            name_without_ext = os.path.splitext(original_filename)[0]
            extension = os.path.splitext(original_filename)[1]
            local_filename = f"{execution_id}_{name_without_ext}_{file_type}{extension}"
            file_path = os.path.join(settings.full_upload_dir, local_filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
        
        # Actualizar la ejecución con metadata adicional
        execution_service.update_execution(
            execution_id, 
            file_path=file_path,
            file_name=original_filename,
            file_type=file_type,
            test_type=test_type,
            project_id=project_id,
            period=period,
            parent_execution_id=parent_execution_id
        )
        
        message = "Large file upload started in background" if file_path.startswith("uploading_to_azure://") else "File uploaded successfully"
        
        print(f"✅ Upload completed: {execution_id}")
        print(f"   Original: {original_filename}")
        print(f"   File type: {file_type}")
        print(f"   Test type: {test_type}")
        print(f"   Storage path: {file_path}")
        if parent_execution_id:
            print(f"   Parent execution: {parent_execution_id}")
        
        return UploadResponse(
            execution_id=execution_id,
            file_name=original_filename,
            message=message
        )
        
    except Exception as e:
        # Limpiar en caso de error
        try:
            execution_service.delete_execution(execution_id)
        except:
            pass
        
        if execution_id in upload_progress:
            del upload_progress[execution_id]
        
        print(f"❌ Upload failed: {execution_id} - {str(e)}")
        
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

@router.get("/upload/{execution_id}/info")
async def get_upload_info(execution_id: str):
    """Get upload information and file details"""
    execution_service = get_execution_service()
    
    try:
        execution = execution_service.get_execution(execution_id)
        
        return {
            "execution_id": execution_id,
            "file_name": getattr(execution, 'file_name', None),
            "file_type": getattr(execution, 'file_type', None),
            "test_type": getattr(execution, 'test_type', None),
            "file_path": execution.file_path,
            "status": execution.status,
            "created_at": execution.created_at,
            "updated_at": execution.updated_at,
            "project_id": getattr(execution, 'project_id', None),
            "period": getattr(execution, 'period', None),
            "parent_execution_id": getattr(execution, 'parent_execution_id', None)
        }
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Execution not found: {execution_id}"
        )