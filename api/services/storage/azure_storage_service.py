# api/services/storage/azure_storage_service.py
import os
import io
import logging
import tempfile
from pathlib import Path
from datetime import datetime, UTC
from typing import Optional, Dict, Any, BinaryIO
from contextlib import contextmanager

from azure.storage.blob import BlobServiceClient, ContentSettings, BlobClient
from azure.storage.blob import BlobBlock
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class AzureStorageService:
    """Centralized Azure Blob Storage service for all file operations"""
    
    def __init__(self):
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not self.connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable is required")
        
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        
        self.chunk_size = 4 * 1024 * 1024
        self.download_chunk_size = 8 * 1024 * 1024
        self.memory_threshold = 50 * 1024 * 1024
        self.max_single_put_size = 64 * 1024 * 1024
        
        self.containers = {
            "upload": "upload",
            "predictions": "predictions", 
            "processed": "processed",
            "results": "results",
            "mapeos": "mapeos"
        }
        
        self._ensure_containers_exist()
    
    def _ensure_containers_exist(self):
        """Create containers if they don't exist"""
        for container_name in self.containers.values():
            try:
                container_client = self.blob_service_client.get_container_client(container_name)
                container_client.create_container()
                logger.info(f"Created container: {container_name}")
            except ResourceExistsError:
                logger.debug(f"Container already exists: {container_name}")
            except Exception as e:
                logger.error(f"Error creating container {container_name}: {e}")
                raise
    
    def _get_blob_name(self, file_path: str, execution_id: Optional[str] = None, 
                      file_type: Optional[str] = None) -> str:
        """
        Generate structured blob name: execution_id_filename_filetype.extension
        
        Args:
            file_path: Original file path/name
            execution_id: Execution identifier
            file_type: "Je" for Journal Entries (Libro Diario), "Sys" for Sumas y Saldos
        
        Returns:
            Structured blob name
        """
        path = Path(file_path)
        original_filename = path.stem  # Filename without extension
        extension = path.suffix  # .txt, .csv, .xlsx, etc.
        
        if execution_id and file_type:
            # Usar ID base (sin -ss) para que ambos archivos tengan el mismo prefijo
            base_execution_id = execution_id.replace('-ss', '') if execution_id.endswith('-ss') else execution_id
            # Estructura: baseExecutionId_NombreArchivo_TipoArchivo.extensión
            blob_name = f"{base_execution_id}_{original_filename}_{file_type}{extension}"
        elif execution_id:
            # Fallback: executionId_filename.extension
            base_execution_id = execution_id.replace('-ss', '') if execution_id.endswith('-ss') else execution_id
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            blob_name = f"{base_execution_id}_{original_filename}_{timestamp}{extension}"
        else:
            # Fallback sin execution_id
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            blob_name = f"{original_filename}_{timestamp}{extension}"
        
        logger.info(f"Generated blob name: {blob_name} (from: {file_path}, execution_id: {execution_id})")
        return blob_name
    
    def upload_file_chunked(self, local_path: str, container_type: str = "upload", 
                           execution_id: Optional[str] = None, 
                           file_type: Optional[str] = None,
                           progress_callback=None) -> str:
        """
        Upload file using chunked upload for large files with structured naming
        
        Args:
            local_path: Path to local file
            container_type: Type of container (upload, results, etc.)
            execution_id: Execution identifier for structured naming
            file_type: "Je" for Journal Entries, "Sys" for Sumas y Saldos
            progress_callback: Progress callback function
        """
        try:
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local file not found: {local_path}")
            
            file_size = os.path.getsize(local_path)
            logger.info(f"Uploading file {local_path} (size: {file_size:,} bytes)")
            
            container_name = self.containers.get(container_type, "upload")
            blob_name = self._get_blob_name(local_path, execution_id, file_type)
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            content_type = self._get_content_type(local_path)
            
            if file_size <= self.max_single_put_size:
                with open(local_path, "rb") as data:
                    blob_client.upload_blob(
                        data,
                        overwrite=True,
                        content_settings=ContentSettings(content_type=content_type),
                        max_concurrency=4
                    )
                logger.info(f"Single upload completed for {blob_name}")
            else:
                self._upload_large_file_chunked(
                    blob_client, local_path, file_size, content_type, progress_callback
                )
                logger.info(f"Chunked upload completed for {blob_name}")
            
            blob_url = f"azure://{container_name}/{blob_name}"
            logger.info(f"File uploaded successfully: {local_path} -> {blob_url}")
            
            return blob_url
            
        except Exception as e:
            logger.error(f"Error uploading file {local_path}: {e}")
            raise
    
    def upload_from_memory(self, file_data: bytes, filename: str, 
                          container_type: str = "upload", 
                          execution_id: Optional[str] = None,
                          file_type: Optional[str] = None) -> str:
        """
        Upload file from memory with structured naming
        
        Args:
            file_data: File data as bytes
            filename: Original filename
            container_type: Type of container
            execution_id: Execution identifier for structured naming
            file_type: "Je" for Journal Entries, "Sys" for Sumas y Saldos
        """
        try:
            container_name = self.containers.get(container_type, "upload")
            blob_name = self._get_blob_name(filename, execution_id, file_type)
            content_type = self._get_content_type(filename)
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            data_size = len(file_data)
            logger.info(f"Uploading from memory: {filename} (size: {data_size:,} bytes)")
            
            if data_size <= self.max_single_put_size:
                blob_client.upload_blob(
                    file_data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                    max_concurrency=4
                )
            else:
                self._upload_large_data_chunked(blob_client, file_data, content_type)
            
            blob_url = f"azure://{container_name}/{blob_name}"
            logger.info(f"File uploaded from memory: {filename} -> {blob_url}")
            
            return blob_url
            
        except Exception as e:
            logger.error(f"Error uploading file from memory {filename}: {e}")
            raise
    
    def upload_libro_diario_file(self, file_data: bytes, original_filename: str, 
                                execution_id: str, container_type: str = "upload") -> str:
        """
        Upload Libro Diario file with 'Je' type identifier
        
        Args:
            file_data: File data as bytes
            original_filename: Original filename
            execution_id: Execution identifier
            container_type: Container type
        
        Returns:
            Azure blob URL
        """
        return self.upload_from_memory(
            file_data=file_data,
            filename=original_filename,
            container_type=container_type,
            execution_id=execution_id,
            file_type="Je"  # Journal Entries
        )
    
    def upload_sumas_saldos_file(self, file_data: bytes, original_filename: str, 
                                execution_id: str, container_type: str = "upload") -> str:
        """
        Upload Sumas y Saldos file with 'Sys' type identifier
        
        Args:
            file_data: File data as bytes
            original_filename: Original filename
            execution_id: Execution identifier
            container_type: Container type
        
        Returns:
            Azure blob URL
        """
        return self.upload_from_memory(
            file_data=file_data,
            filename=original_filename,
            container_type=container_type,
            execution_id=execution_id,
            file_type="Sys"  # Sumas y Saldos
        )
    
    def download_file(self, blob_url: str, local_path: str = None, 
                     progress_callback=None) -> str:
        """Download file from Azure Blob Storage"""
        try:
            container_name, blob_name = self._parse_blob_url(blob_url)
            
            if not local_path:
                temp_dir = tempfile.gettempdir()
                local_path = os.path.join(temp_dir, blob_name)
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            properties = blob_client.get_blob_properties()
            file_size = properties.size
            
            logger.info(f"Downloading file: {blob_url} (size: {file_size:,} bytes)")
            
            if file_size <= self.memory_threshold:
                with open(local_path, "wb") as download_file:
                    download_data = blob_client.download_blob()
                    download_file.write(download_data.readall())
            else:
                self._download_large_file_chunked(
                    blob_client, local_path, file_size, progress_callback
                )
            
            logger.info(f"File downloaded: {blob_url} -> {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading file {blob_url}: {e}")
            raise
    
    @contextmanager
    def get_temp_file(self, blob_url: str):
        """Context manager for temporary file handling"""
        temp_file = None
        try:
            temp_file = self.download_file(blob_url)
            yield temp_file
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Could not remove temp file {temp_file}: {e}")
    
    def file_exists(self, blob_url: str) -> bool:
        """Check if file exists in Azure Blob Storage"""
        try:
            container_name, blob_name = self._parse_blob_url(blob_url)
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            return blob_client.exists()
        except Exception:
            return False
    
    def delete_file(self, blob_url: str) -> bool:
        """Delete file from Azure Blob Storage"""
        try:
            container_name, blob_name = self._parse_blob_url(blob_url)
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            logger.info(f"File deleted: {blob_url}")
            return True
        except ResourceNotFoundError:
            logger.warning(f"File not found for deletion: {blob_url}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file {blob_url}: {e}")
            return False
    
    def get_file_info(self, blob_url: str) -> Dict[str, Any]:
        """Get file information from Azure Blob Storage"""
        try:
            container_name, blob_name = self._parse_blob_url(blob_url)
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            properties = blob_client.get_blob_properties()
            
            return {
                "exists": True,
                "size": properties.size,
                "size_mb": round(properties.size / (1024 * 1024), 2),
                "size_gb": round(properties.size / (1024 * 1024 * 1024), 3),
                "last_modified": properties.last_modified.isoformat(),
                "content_type": properties.content_settings.content_type,
                "etag": properties.etag,
                "container": container_name,
                "blob_name": blob_name,
                "is_large_file": properties.size > self.memory_threshold
            }
            
        except ResourceNotFoundError:
            return {"exists": False}
        except Exception as e:
            logger.error(f"Error getting file info {blob_url}: {e}")
            return {"exists": False, "error": str(e)}
    
    def _upload_large_file_chunked(self, blob_client: BlobClient, file_path: str, 
                                  file_size: int, content_type: str, progress_callback=None):
        """Upload large file using block upload"""
        block_list = []
        uploaded_bytes = 0
        
        with open(file_path, 'rb') as file_stream:
            block_id = 0
            
            while True:
                chunk = file_stream.read(self.chunk_size)
                if not chunk:
                    break
                
                block_id_str = f"{block_id:08d}"
                block_list.append(BlobBlock(block_id=block_id_str))
                
                blob_client.stage_block(
                    block_id=block_id_str,
                    data=chunk
                )
                
                uploaded_bytes += len(chunk)
                block_id += 1
                
                if progress_callback:
                    progress = (uploaded_bytes / file_size) * 100
                    progress_callback(progress, uploaded_bytes, file_size)
                
                if block_id % 10 == 0:
                    logger.info(f"Uploaded {uploaded_bytes:,} / {file_size:,} bytes ({uploaded_bytes/file_size*100:.1f}%)")
        
        blob_client.commit_block_list(
            block_list,
            content_settings=ContentSettings(content_type=content_type)
        )
        
        logger.info(f"Committed {len(block_list)} blocks for large file upload")
    
    def _upload_large_data_chunked(self, blob_client: BlobClient, data: bytes, content_type: str):
        """Upload large data from memory using block upload"""
        block_list = []
        data_stream = io.BytesIO(data)
        block_id = 0
        
        while True:
            chunk = data_stream.read(self.chunk_size)
            if not chunk:
                break
            
            block_id_str = f"{block_id:08d}"
            block_list.append(BlobBlock(block_id=block_id_str))
            
            blob_client.stage_block(
                block_id=block_id_str,
                data=chunk
            )
            
            block_id += 1
        
        blob_client.commit_block_list(
            block_list,
            content_settings=ContentSettings(content_type=content_type)
        )
        
        logger.info(f"Committed {len(block_list)} blocks for large memory upload")
    
    def _download_large_file_chunked(self, blob_client: BlobClient, local_path: str, 
                                   file_size: int, progress_callback=None):
        """Download large file in chunks"""
        downloaded_bytes = 0
        
        with open(local_path, "wb") as download_file:
            while downloaded_bytes < file_size:
                chunk_end = min(downloaded_bytes + self.download_chunk_size - 1, file_size - 1)
                
                download_stream = blob_client.download_blob(
                    offset=downloaded_bytes,
                    length=chunk_end - downloaded_bytes + 1
                )
                
                chunk_data = download_stream.readall()
                download_file.write(chunk_data)
                
                downloaded_bytes += len(chunk_data)
                
                if progress_callback:
                    progress = (downloaded_bytes / file_size) * 100
                    progress_callback(progress, downloaded_bytes, file_size)
                
                if downloaded_bytes % (40 * 1024 * 1024) == 0:
                    logger.info(f"Downloaded {downloaded_bytes:,} / {file_size:,} bytes ({downloaded_bytes/file_size*100:.1f}%)")
    
    def _parse_blob_url(self, blob_url: str) -> tuple:
        """Parse Azure blob URL to get container and blob name"""
        if not blob_url.startswith("azure://"):
            raise ValueError(f"Invalid blob URL format: {blob_url}")
        
        path = blob_url[8:]
        parts = path.split("/", 1)
        
        if len(parts) != 2:
            raise ValueError(f"Invalid blob URL format: {blob_url}")
        
        return parts[0], parts[1]
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type based on file extension"""
        extension = Path(filename).suffix.lower()
        
        content_types = {
            ".csv": "text/csv",
            ".txt": "text/plain", 
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".json": "application/json",
            ".pdf": "application/pdf"
        }
        
        return content_types.get(extension, "application/octet-stream")


_azure_storage_service: Optional[AzureStorageService] = None


def get_azure_storage_service() -> AzureStorageService:
    """Get global Azure Storage service instance"""
    global _azure_storage_service
    if _azure_storage_service is None:
        _azure_storage_service = AzureStorageService()
    return _azure_storage_service