# models/execution.py
"""
Pydantic models for execution tracking and API responses - Cleaned
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ExecutionStatus(BaseModel):
    id: str
    status: str  # 'pending', 'processing', 'completed', 'failed', 'mapeo', 'mapeo_completed', 'manual_mapping_required'
    step: Optional[str] = None  # 'upload', 'validation', 'conversion', 'mapeo', 'manual_mapping', etc.
    created_at: str
    updated_at: str
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    error: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    result_path: Optional[str] = None
    mapeo_results: Optional[Dict[str, Any]] = None
    manual_mapping_required: Optional[bool] = None
    unmapped_fields_count: Optional[int] = None

# Request/Response Models
class UploadResponse(BaseModel):
    execution_id: str
    file_name: str
    message: str

class ValidationRequest(BaseModel):
    execution_id: str

class ValidationResponse(BaseModel):
    execution_id: str
    message: str

class ConversionResponse(BaseModel):
    execution_id: str
    message: str

class MapeoRequest(BaseModel):
    erp_hint: Optional[str] = None

class MapeoResponse(BaseModel):
    execution_id: str
    message: str
    input_file: str
    erp_hint: Optional[str] = None
    manual_mapping_required: Optional[bool] = None

class MapeoStatusResponse(BaseModel):
    execution_id: str
    status: str
    step: Optional[str] = None
    updated_at: str
    mapeo_results: Optional[Dict[str, Any]] = None
    files_available: Optional[Dict[str, bool]] = None
    error: Optional[str] = None
    manual_mapping_required: Optional[bool] = None
    unmapped_fields_count: Optional[int] = None

class MapeoSummaryResponse(BaseModel):
    execution_id: str
    trainer_type: str
    summary: Dict[str, int]
    files_created: Dict[str, Optional[str]]
    warning: Optional[str] = None
    manual_mapping_required: Optional[bool] = None

# Manual mapping models
class UnmappedFieldDetail(BaseModel):
    column_name: str
    sample_data: List[str]
    data_type: str
    suggestions: List[Dict[str, Any]]
    total_values: int
    non_null_values: int
    unique_values: int

class UnmappedFieldsResponse(BaseModel):
    execution_id: str
    unmapped_fields: List[UnmappedFieldDetail]
    available_standard_fields: List[str]
    total_unmapped: int
    total_available_fields: int
    message: str

class MappingDecision(BaseModel):
    column_name: str
    selected_field: str
    confidence: Optional[float] = 0.8

class ManualMappingRequest(BaseModel):
    mappings: List[MappingDecision]

class ApplyMappingResponse(BaseModel):
    execution_id: str
    applied_mappings: int
    updated_decisions: Dict[str, str]
    regenerated_files: Dict[str, Optional[str]]
    message: str

class PreviewResponse(BaseModel):
    data: List[Dict[str, Any]]

class FileInfo(BaseModel):
    path: Optional[str]
    exists: bool
    size: int

class ExecutionFilesResponse(BaseModel):
    original_file: FileInfo
    result_file: FileInfo
    mapeo_files: Optional[Dict[str, FileInfo]] = None