# config/settings.py
"""
Configuration settings with Azure Storage integration - Cleaned
"""
import os
from pathlib import Path
from typing import List, Optional, Any
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # Basic app settings
    app_name: str = "Document Processing API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Azure Storage settings
    use_azure_storage: bool = True
    azure_storage_connection_string: str = ""
    azure_storage_container: Optional[str] = None
    azure_storage_account_url: Optional[str] = None
    azure_storage_sas_token: Optional[str] = None
    
    # CSV filename for compatibility
    csv_filename: Optional[str] = None
    
    # Local directories (used as fallback or temp)
    base_dir: Path = Path(__file__).parent.parent
    upload_dir: str = "uploads"
    predictions_dir: str = "predictions"
    processed_dir: str = "processed"
    results_dir: str = "results"
    mapeos_dir: str = "mapeos"
    
    # File processing settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: List[str] = [".csv", ".txt", ".xlsx", ".xls"]
    rejection_threshold: float = 0.25  # Model confidence threshold
    
    # Model settings
    model_dirs: List[str] = [
        "modelo/modelo_parent_child",
        "modelo/modelo_header_data"
    ]
    
    @field_validator('model_dirs', mode='before')
    @classmethod
    def parse_model_dirs(cls, v: Any) -> List[str]:
        """Parse model_dirs from various input formats"""
        if isinstance(v, str):
            if ',' in v:
                return [path.strip() for path in v.split(",") if path.strip()]
            elif v.strip():
                return [v.strip()]
            else:
                return []
        elif isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        else:
            return [
                "modelo/modelo_parent_child",
                "modelo/modelo_header_data"
            ]
    
    @field_validator('allowed_extensions', mode='before')
    @classmethod
    def parse_allowed_extensions(cls, v: Any) -> List[str]:
        """Parse allowed_extensions from various input formats"""
        if isinstance(v, str):
            if ',' in v:
                return [ext.strip() for ext in v.split(",") if ext.strip()]
            elif v.strip():
                return [v.strip()]
            else:
                return [".csv", ".txt", ".xlsx", ".xls"]
        elif isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        else:
            return [".csv", ".txt", ".xlsx", ".xls"]
    
    @property
    def full_upload_dir(self) -> str:
        return str(self.base_dir / self.upload_dir)
    
    @property
    def full_predictions_dir(self) -> str:
        return str(self.base_dir / self.predictions_dir)
    
    @property
    def full_processed_dir(self) -> str:
        return str(self.base_dir / self.processed_dir)
    
    @property
    def full_results_dir(self) -> str:
        return str(self.base_dir / self.results_dir)
    
    @property
    def full_mapeos_dir(self) -> str:
        return str(self.base_dir / self.mapeos_dir)
    
    def validate_azure_config(self) -> bool:
        """Validate Azure Storage configuration"""
        if self.use_azure_storage:
            return bool(self.azure_storage_connection_string)
        return True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
            
            if _settings.use_azure_storage and not _settings.validate_azure_config():
                print("Warning: Azure Storage is enabled but AZURE_STORAGE_CONNECTION_STRING is not configured. Using local storage as fallback.")
                _settings.use_azure_storage = False
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            print("Using default settings with local storage")
            
            _settings = Settings(
                use_azure_storage=False,
                azure_storage_connection_string="",
                model_dirs=[
                    "modelo/modelo_parent_child", 
                    "modelo/modelo_header_data"
                ]
            )
    
    return _settings