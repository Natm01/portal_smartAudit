import os
import tempfile
import logging
from contextlib import contextmanager
from typing import List, Optional
from pathlib import Path

from services.storage.azure_storage_service import get_azure_storage_service

logger = logging.getLogger(__name__)


class TempFileManager:
    """Manager for handling temporary files with automatic cleanup"""
    
    def __init__(self):
        self.azure_service = get_azure_storage_service()
        self._temp_files: List[str] = []
    
    @contextmanager
    def get_local_file(self, azure_path: str, suffix: str = None):
        """Context manager that downloads Azure file to temp and cleans up automatically"""
        temp_file = None
        try:
            # Extract original extension from Azure path if suffix not provided
            if not suffix:
                if azure_path.startswith("azure://"):
                    # Extract blob name from azure://container/blob_name
                    blob_name = azure_path.split("/")[-1]
                    original_ext = Path(blob_name).suffix
                    if original_ext:
                        suffix = original_ext
                else:
                    original_ext = Path(azure_path).suffix
                    if original_ext:
                        suffix = original_ext
            
            # Create temp file with proper extension
            if suffix:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix).name
            else:
                temp_file = tempfile.NamedTemporaryFile(delete=False).name
            
            self.azure_service.download_file(azure_path, temp_file)
            self._temp_files.append(temp_file)
            
            logger.info(f"Downloaded {azure_path} to {temp_file} (suffix: {suffix})")
            yield temp_file
            
        except Exception as e:
            logger.error(f"Error in temp file manager: {e}")
            raise
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    if temp_file in self._temp_files:
                        self._temp_files.remove(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Could not remove temp file {temp_file}: {e}")
    
    @contextmanager
    def create_temp_file(self, suffix: str = None):
        """Context manager for creating temporary files"""
        temp_file = None
        try:
            if suffix:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix).name
            else:
                temp_file = tempfile.NamedTemporaryFile(delete=False).name
            
            self._temp_files.append(temp_file)
            yield temp_file
            
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    if temp_file in self._temp_files:
                        self._temp_files.remove(temp_file)
                    logger.debug(f"Cleaned up created temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Could not remove temp file {temp_file}: {e}")
    
    def cleanup_all(self):
        """Cleanup all tracked temporary files"""
        for temp_file in self._temp_files[:]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    self._temp_files.remove(temp_file)
                    logger.debug(f"Cleaned up tracked temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Could not remove tracked temp file {temp_file}: {e}")


_temp_file_manager: Optional[TempFileManager] = None


def get_temp_file_manager() -> TempFileManager:
    """Get global temp file manager instance"""
    global _temp_file_manager
    if _temp_file_manager is None:
        _temp_file_manager = TempFileManager()
    return _temp_file_manager