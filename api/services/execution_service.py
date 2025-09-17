# services/execution_service.py
"""
Service for managing execution state and lifecycle - Updated with coordination
"""
import os
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from fastapi import HTTPException

from models.execution import ExecutionStatus, ExecutionSummary
from config.settings import get_settings
from utils.serialization import safe_json_response

class ExecutionService:
    def __init__(self):
        self.execution_store: Dict[str, ExecutionStatus] = {}
        self.settings = get_settings()
    
    def create_execution(self, file_name: str, file_path: str, execution_id: str = None) -> str:
        """
        Create a new execution record with optional custom execution_id
        
        Args:
            file_name: Original file name
            file_path: File path (can be temporary for background uploads)
            execution_id: Optional custom execution ID (for coordinated uploads)
        
        Returns:
            execution_id string
        """
        if execution_id is None:
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
        print(f"✅ Created execution: {execution_id} for file: {file_name}")
        return execution_id
    
    def create_coordinated_execution(self, file_name: str, file_path: str, 
                                   file_type: str, test_type: str,
                                   project_id: str = None, period: str = None,
                                   parent_execution_id: str = None) -> str:
        """
        Create execution with full coordination metadata
        
        Args:
            file_name: Original filename
            file_path: Storage path
            file_type: "Je" or "Sys"
            test_type: Type of test
            project_id: Project identifier
            period: Period string
            parent_execution_id: Parent execution for coordination
            
        Returns:
            execution_id string
        """
        # Para Sumas y Saldos, crear ID derivado del parent
        if parent_execution_id and file_type == "Sys":
            execution_id = f"{parent_execution_id}-ss"
        else:
            execution_id = str(uuid.uuid4())
        
        now = datetime.now().isoformat()
        
        execution = ExecutionStatus(
            id=execution_id,
            status="pending",
            created_at=now,
            updated_at=now,
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            test_type=test_type,
            project_id=project_id,
            period=period,
            parent_execution_id=parent_execution_id
        )
        
        self.execution_store[execution_id] = execution
        
        print(f"✅ Created coordinated execution: {execution_id}")
        print(f"   File: {file_name} (Type: {file_type})")
        if parent_execution_id:
            print(f"   Parent: {parent_execution_id}")
        
        return execution_id
    
    def get_execution(self, execution_id: str) -> ExecutionStatus:
        """Get execution by ID"""
        if execution_id not in self.execution_store:
            raise HTTPException(status_code=404, detail="Execution ID not found")
        return self.execution_store[execution_id]
    
    def update_execution(self, execution_id: str, **kwargs) -> None:
        """Update execution status with enhanced field support"""
        if execution_id not in self.execution_store:
            raise HTTPException(status_code=404, detail="Execution ID not found")
        
        execution = self.execution_store[execution_id]
        execution_dict = execution.dict()
        
        # Lista de campos permitidos para actualización
        allowed_fields = {
            'status', 'step', 'file_path', 'result_path', 'error', 'stats',
            'file_type', 'test_type', 'project_id', 'period', 'parent_execution_id',
            'mapeo_results', 'manual_mapping_required', 'unmapped_fields_count',
            'file_name'  # Permitir actualizar file_name si es necesario
        }
        
        updated_fields = []
        for key, value in kwargs.items():
            if key in allowed_fields and key in execution_dict:
                execution_dict[key] = value
                updated_fields.append(key)
        
        execution_dict["updated_at"] = datetime.now().isoformat()
        self.execution_store[execution_id] = ExecutionStatus(**execution_dict)
        
        if updated_fields:
            print(f"📝 Updated execution {execution_id}: {', '.join(updated_fields)}")
    
    def get_execution_safe(self, execution_id: str) -> Dict:
        """Get execution with safe JSON serialization"""
        execution = self.get_execution(execution_id)
        return safe_json_response(execution.dict())
    
    def list_executions(self, file_type: str = None, 
                       parent_execution_id: str = None) -> List[ExecutionSummary]:
        """
        List executions with optional filtering
        
        Args:
            file_type: Filter by file type ("Je", "Sys")
            parent_execution_id: Filter by parent execution
            
        Returns:
            List of ExecutionSummary objects
        """
        executions = []
        
        for execution in self.execution_store.values():
            # Aplicar filtros si se especifican
            if file_type and getattr(execution, 'file_type', None) != file_type:
                continue
            if parent_execution_id and getattr(execution, 'parent_execution_id', None) != parent_execution_id:
                continue
            
            summary = ExecutionSummary(
                execution_id=execution.id,
                file_name=execution.file_name,
                file_type=getattr(execution, 'file_type', None),
                test_type=getattr(execution, 'test_type', None),
                status=execution.status,
                step=execution.step,
                created_at=execution.created_at,
                updated_at=execution.updated_at,
                project_id=getattr(execution, 'project_id', None),
                period=getattr(execution, 'period', None),
                parent_execution_id=getattr(execution, 'parent_execution_id', None),
                error=execution.error
            )
            
            executions.append(summary)
        
        # Ordenar por fecha de creación (más recientes primero)
        executions.sort(key=lambda x: x.created_at, reverse=True)
        return executions
    
    def get_coordinated_executions(self, execution_id: str) -> Dict[str, Optional[ExecutionStatus]]:
        """
        Get related executions (parent and children)
        
        Args:
            execution_id: Base execution ID
            
        Returns:
            Dict with 'libro_diario' and 'sumas_saldos' executions
        """
        result = {
            'libro_diario': None,
            'sumas_saldos': None
        }
        
        try:
            base_execution = self.get_execution(execution_id)
            
            if getattr(base_execution, 'file_type', None) == 'Je':
                # Es Libro Diario, buscar Sumas y Saldos relacionado
                result['libro_diario'] = base_execution
                
                # Buscar SS con este como parent
                ss_id = f"{execution_id}-ss"
                try:
                    ss_execution = self.get_execution(ss_id)
                    result['sumas_saldos'] = ss_execution
                except:
                    pass  # SS no existe
                    
            elif getattr(base_execution, 'file_type', None) == 'Sys':
                # Es Sumas y Saldos, buscar Libro Diario parent
                result['sumas_saldos'] = base_execution
                
                parent_id = getattr(base_execution, 'parent_execution_id', None)
                if parent_id:
                    try:
                        ld_execution = self.get_execution(parent_id)
                        result['libro_diario'] = ld_execution
                    except:
                        pass  # Parent no existe
            else:
                # Tipo desconocido, asumir que es LD
                result['libro_diario'] = base_execution
                
        except Exception as e:
            print(f"Error getting coordinated executions for {execution_id}: {e}")
        
        return result
    
    def delete_execution(self, execution_id: str) -> bool:
        """Delete execution record"""
        if execution_id in self.execution_store:
            execution = self.execution_store[execution_id]
            del self.execution_store[execution_id]
            
            print(f"Deleted execution: {execution_id} ({execution.file_name})")
            return True
        return False
    
    def delete_coordinated_executions(self, execution_id: str) -> Dict[str, bool]:
        """
        Delete coordinated executions (both LD and SS)
        
        Returns:
            Dict indicating success for each deletion
        """
        result = {'libro_diario': False, 'sumas_saldos': False}
        
        coordinated = self.get_coordinated_executions(execution_id)
        
        if coordinated['libro_diario']:
            result['libro_diario'] = self.delete_execution(coordinated['libro_diario'].id)
        
        if coordinated['sumas_saldos']:
            result['sumas_saldos'] = self.delete_execution(coordinated['sumas_saldos'].id)
        
        return result

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