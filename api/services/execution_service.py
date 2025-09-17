# services/execution_service.py
"""
Service for managing execution state and lifecycle - Cleaned
"""
import os
import uuid
from datetime import datetime
from typing import Dict, Optional
from fastapi import HTTPException

from models.execution import ExecutionStatus
from config.settings import get_settings
from utils.serialization import safe_json_response

class ExecutionService:
    def __init__(self):
        self.execution_store: Dict[str, ExecutionStatus] = {}
        self.settings = get_settings()
    
    def create_execution(self, file_name: str, file_path: str) -> str:
        """Create a new execution record"""
        execution_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        execution = ExecutionStatus(
            id=execution_id,
            status="pending",
            created_at=now,
            updated_at=now,
            file_name=file_name,
            file_path=file_path
        )
        
        self.execution_store[execution_id] = execution
        return execution_id
    
    def get_execution(self, execution_id: str) -> ExecutionStatus:
        """Get execution by ID"""
        if execution_id not in self.execution_store:
            raise HTTPException(status_code=404, detail="Execution ID not found")
        return self.execution_store[execution_id]
    
    def update_execution(self, execution_id: str, **kwargs) -> None:
        """Update execution status"""
        if execution_id not in self.execution_store:
            raise HTTPException(status_code=404, detail="Execution ID not found")
        
        execution = self.execution_store[execution_id]
        execution_dict = execution.dict()
        
        for key, value in kwargs.items():
            if key in execution_dict:
                execution_dict[key] = value
        
        execution_dict["updated_at"] = datetime.now().isoformat()
        self.execution_store[execution_id] = ExecutionStatus(**execution_dict)
    
    def get_execution_safe(self, execution_id: str) -> Dict:
        """Get execution with safe JSON serialization"""
        execution = self.get_execution(execution_id)
        return safe_json_response(execution.dict())
    
    def list_executions(self) -> Dict[str, ExecutionStatus]:
        """List all executions"""
        return self.execution_store
    
    def delete_execution(self, execution_id: str) -> bool:
        """Delete execution record"""
        if execution_id in self.execution_store:
            del self.execution_store[execution_id]
            return True
        return False

# Global service instance
_execution_service = None

def get_execution_service() -> ExecutionService:
    """Get global execution service instance"""
    global _execution_service
    if _execution_service is None:
        _execution_service = ExecutionService()
    return _execution_service

def create_directories():
    """Create necessary directories for the application"""
    settings = get_settings()
    directories = [
        settings.upload_dir,
        settings.predictions_dir,
        settings.processed_dir,
        settings.results_dir
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)