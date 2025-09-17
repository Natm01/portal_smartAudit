import os
import logging
from typing import Dict, Any
from pathlib import Path

from procesos_estructura.model_processor import DocumentPredict
from services.storage.temp_file_manager import get_temp_file_manager
from config.settings import get_settings

logger = logging.getLogger(__name__)

class ValidationService:
    """Clean validation service without Azure logic mixed in"""
    
    def __init__(self):
        self.settings = get_settings()
        self.temp_manager = get_temp_file_manager()
    
    async def validate_file(self, azure_file_path: str) -> Dict[str, Any]:
        """Validate a file using DocumentPredict logic with clean separation"""
        try:
            logger.info(f"Starting validation for file: {azure_file_path}")
            
            original_filename = self._extract_original_filename(azure_file_path)
            
            with self.temp_manager.get_local_file(azure_file_path) as local_file_path:
                return self._perform_validation(local_file_path, azure_file_path, original_filename)
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise Exception(f"Validation error: {str(e)}")
    
    def _extract_original_filename(self, azure_file_path: str) -> str:
        """Extract original filename from Azure path"""
        if azure_file_path.startswith("azure://"):
            blob_name = azure_file_path.split("/")[-1]
            parts = blob_name.split("_")
            if len(parts) >= 3:
                return "_".join(parts[1:-1]) + Path(blob_name).suffix
            else:
                return blob_name
        else:
            return os.path.basename(azure_file_path)
    
    def _perform_validation(self, local_file_path: str, original_azure_path: str, 
                          original_filename: str) -> Dict[str, Any]:
        """Perform actual validation logic"""
        tester = DocumentPredict(model_dirs=self.settings.model_dirs)
        
        tester._original_filename = original_filename
        
        logger.info(f"Validating file: {local_file_path} (original: {original_filename})")
        
        test_df = tester.load_test_file(local_file_path)
        
        file_type = os.path.splitext(original_filename)[1].lower()
        method_used = "read_text_file" if tester._last_is_txt else "read_csv_or_excel"
        
        preview_df = test_df.head(5)
        file_size = os.path.getsize(local_file_path)
        
        stats = {
            "preview_rows": len(preview_df),
            "total_rows": len(test_df),
            "columns": list(test_df.columns),
            "file_size": file_size,
            "file_type": file_type,
            "detection_method": method_used,
            "preview_data": preview_df.to_dict(orient="records"),
            "storage_type": "azure",
            "original_filename": original_filename
        }
        
        logger.info(f"Validation successful: {len(test_df)} rows, {len(test_df.columns)} columns, method: {method_used}")
        
        return {
            "success": True,
            "stats": stats,
            "message": f"File validated successfully: {len(test_df)} rows, {len(test_df.columns)} columns"
        }

_validation_service = None

def get_validation_service() -> ValidationService:
    """Get global validation service instance"""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service