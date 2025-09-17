# procesos_mapeo/dynamic_field_loader.py

import json
import hashlib
import threading
import time
import sys
import traceback
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from enum import Enum
from datetime import datetime

import yaml
import importlib.util

from .dynamic_field_definition import DynamicFieldDefinition, create_sample_field_definitions

logger = logging.getLogger(__name__)

class LoaderStatus(Enum):
    UNINITIALIZED = "uninitialized"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    RELOADING = "reloading"

class ConfigurationError(Exception):
    pass

class DynamicFieldLoader:
    """Dynamic configuration loader optimized with hot-reload support"""
    
    def __init__(self, config_source: Union[str, Path] = None, 
                 auto_reload: bool = True, reload_interval: int = 30):
        
        self.config_source = Path(config_source or "config/dynamic_fields_config.yaml")
        self.auto_reload_enabled = auto_reload
        self.reload_interval_seconds = reload_interval
        
        self.status = LoaderStatus.UNINITIALIZED
        self.last_error = None
        self.last_reload_time = None
        self.reload_count = 0
        
        self._field_definitions_cache = {}
        self._backup_definitions = {}
        self._last_config_hash = None
        self._custom_validators_cache = {}
        self._config_history = []
        
        self._reload_thread = None
        self._stop_reload = threading.Event()
        self._reload_lock = threading.RLock()
        
        self.custom_validators_module = None
        self.validators_path = Path("config/custom_field_validators.py")
        
        self.stats = {
            'total_reloads': 0,
            'successful_reloads': 0,
            'failed_reloads': 0,
            'last_reload_duration': 0,
            'config_changes_detected': 0
        }
        
        self.core_fields = {
            'journal_entry_id': "ID del Asiento",
            'line_number': "Numero de Linea del Asiento",
            'description': "Descripcion del Encabezado",
            'line_description': "Descripcion de la Linea",
            'posting_date': "Fecha Efectiva",
            'fiscal_year': "Ano Fiscal",
            'period_number': "Periodo",
            'gl_account_number': "Numero de Cuenta Contable",
            'gl_account_name': "Nombre de Cuenta Contable",
            'amount': "Importe",
            'debit_amount': "Importe Debe",
            'credit_amount': "Importe Haber",
            'debit_credit_indicator': "Indicador Debe/Haber",
            'prepared_by': "Introducido Por",
            'entry_date': "Fecha de Introduccion",
            'entry_time': "Hora de Introduccion",
            'vendor_id': "ID Tercero",
        }
        
        self._initialize()
    
    def _initialize(self):
        try:
            self.status = LoaderStatus.LOADING
            
            self.config_source.parent.mkdir(parents=True, exist_ok=True)
            
            success = self._load_configuration()
            
            if success:
                self.status = LoaderStatus.READY
                    
            else:
                self.status = LoaderStatus.ERROR
                
        except Exception as e:
            self.status = LoaderStatus.ERROR
            self.last_error = str(e)
            logger.debug(traceback.format_exc())
    
    
    def _start_auto_reload_thread(self):
        if self._reload_thread and self._reload_thread.is_alive():
            return
        
        self._stop_reload.clear()
        self._reload_thread = threading.Thread(
            target=self._auto_reload_worker,
            name="DynamicFieldLoader-AutoReload",
            daemon=True
        )
        self._reload_thread.start()
        logger.debug("Auto-reload thread started")
    
    def _auto_reload_worker(self):
        while not self._stop_reload.wait(self.reload_interval_seconds):
            try:
                if self._should_reload():
                    self.reload_configuration()
            except Exception as e:
                logger.error(f"Error in auto-reload worker: {e}")
    
    def _should_reload(self) -> bool:
        if not self.auto_reload_enabled:
            return False
        
        try:
            current_hash = self._get_config_hash()
            return current_hash != self._last_config_hash
        except Exception as e:
            logger.warning(f"Error checking if reload needed: {e}")
            return False
    
    def _get_config_hash(self) -> str:
        hash_content = ""
        
        if self.config_source.exists():
            hash_content += self.config_source.read_text(encoding='utf-8')
        
        if self.validators_path.exists():
            hash_content += self.validators_path.read_text(encoding='utf-8')
        
        config_dir = self.config_source.parent
        if config_dir.exists():
            for file_path in config_dir.glob("*.yaml"):
                if file_path != self.config_source:
                    try:
                        hash_content += file_path.read_text(encoding='utf-8')
                    except Exception:
                        pass
        
        return hashlib.md5(hash_content.encode()).hexdigest()
    
    def _load_configuration(self) -> bool:
        start_time = time.time()
        
        try:
            with self._reload_lock:
                if self._field_definitions_cache:
                    self._backup_definitions = self._field_definitions_cache.copy()
                
                self._field_definitions_cache.clear()
                
                if not self.config_source.exists():
                    self._create_default_config()
                
                config_data = self._load_config_file(self.config_source)
                
                self._process_field_definitions(config_data)
                
                self._load_custom_validators()
                
                self._last_config_hash = self._get_config_hash()
                self.last_reload_time = datetime.now()
                self.reload_count += 1
                
                duration = time.time() - start_time
                self.stats['total_reloads'] += 1
                self.stats['successful_reloads'] += 1
                self.stats['last_reload_duration'] = duration
                
                self._config_history.append({
                    'timestamp': self.last_reload_time.isoformat(),
                    'fields_loaded': len(self._field_definitions_cache),
                    'duration_seconds': duration,
                    'config_hash': self._last_config_hash[:8]
                })
                
                if len(self._config_history) > 10:
                    self._config_history = self._config_history[-10:]
                
                logger.info(f"Configuration loaded successfully. {len(self._field_definitions_cache)} field definitions loaded in {duration:.3f}s")
                return True
                
        except Exception as e:
            self.stats['failed_reloads'] += 1
            self.last_error = str(e)
            
            if self._backup_definitions:
                logger.warning(f"Configuration loading failed, restoring from backup: {e}")
                self._field_definitions_cache = self._backup_definitions.copy()
                return True
            else:
                logger.error(f"Configuration loading failed and no backup available: {e}")
                logger.debug(traceback.format_exc())
                return False
    
    def _create_default_config(self):
        sample_fields = create_sample_field_definitions()
        
        default_config = {
            "system": {
                "version": "2.0.0",
                "auto_reload": True,
                "last_updated": datetime.now().isoformat(),
                "reload_interval_seconds": 30
            },
            "field_definitions": {
                "dynamic_fields": {}
            }
        }
        
        for field_code, field_def in sample_fields.items():
            default_config["field_definitions"]["dynamic_fields"][field_code] = field_def.to_dict()
        
        try:
            self._save_config_file(default_config, self.config_source)
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
            raise ConfigurationError(f"Cannot create default configuration: {e}")
    
    def _save_config_file(self, data: Dict, file_path: Path):
        try:
            if file_path.suffix.lower() in ['.yml', '.yaml']:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            else:
                json_path = file_path.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigurationError(f"Error saving configuration: {e}")
    
    def _load_config_file(self, file_path: Path) -> Dict:
        try:
            content = file_path.read_text(encoding='utf-8')
            
            if file_path.suffix.lower() in ['.yml', '.yaml']:
                data = yaml.safe_load(content)
            elif file_path.suffix.lower() == '.json':
                data = json.loads(content)
            else:
                raise ConfigurationError(f"Unsupported file format: {file_path.suffix}")
            
            if not isinstance(data, dict):
                raise ConfigurationError("Configuration must be a dictionary")
            
            return data
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML parsing error in {file_path}: {e}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"JSON parsing error in {file_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading {file_path}: {e}")
    
    def _process_field_definitions(self, config_data: Dict):
        # Add core fields first (without synonyms by default)
        for code, name in self.core_fields.items():
            try:
                field_def = DynamicFieldDefinition(
                    code=code,
                    name=name,
                    description=f"Core field: {name}",
                    data_type="text",
                    active=True,
                    priority=100
                )
                self._field_definitions_cache[code] = field_def
            except Exception as e:
                logger.warning(f"Error creating core field {code}: {e}")
        
        # Process dynamic fields
        field_definitions = config_data.get('field_definitions', {})
        dynamic_fields = field_definitions.get('dynamic_fields', {})
        
        if not dynamic_fields:
            logger.warning("No dynamic fields found in configuration")
            return

        processed_count = 0
        error_count = 0

        for field_code, field_config in dynamic_fields.items():
            try:
                processed_config = field_config.copy()
                
                # Process synonyms correctly
                if 'synonyms' in field_config:
                    raw_synonyms = field_config['synonyms']
                    
                    # Verify ERP structure
                    if isinstance(raw_synonyms, dict):
                        is_erp_structure = all(
                            isinstance(v, list) and 
                            all(isinstance(item, dict) and 'name' in item for item in v)
                            for v in raw_synonyms.values()
                        )
                        
                        if is_erp_structure:
                            processed_config['synonyms'] = raw_synonyms
                
                field_data = {
                    "code": field_code,
                    **processed_config
                }

                field_def = DynamicFieldDefinition.from_dict(field_data)

                if field_def.is_valid():
                    self._field_definitions_cache[field_code] = field_def
                    processed_count += 1
                else:
                    logger.warning(f"Invalid field definition: {field_code}")
                    error_count += 1

            except Exception as e:
                logger.error(f"Error processing field {field_code}: {e}")
                logger.debug(traceback.format_exc())
                error_count += 1

        logger.info(f"Processed {processed_count} field definitions ({error_count} errors)")
    
    def _load_custom_validators(self):
        if not self.validators_path.exists():
            return
        
        try:
            spec = importlib.util.spec_from_file_location("custom_validators", self.validators_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'AVAILABLE_VALIDATORS'):
                self._custom_validators_cache = module.AVAILABLE_VALIDATORS
                logger.info(f"Loaded {len(self._custom_validators_cache)} custom validators")
            
            self.custom_validators_module = module
                
        except Exception as e:
            logger.warning(f"Error loading custom validators: {e}")
    
    def reload_configuration(self, force: bool = False) -> bool:
        if not force and not self._should_reload():
            return False
        
        old_status = self.status
        self.status = LoaderStatus.RELOADING
        
        try:
            success = self._load_configuration()
            self.status = LoaderStatus.READY if success else LoaderStatus.ERROR
            return success
        except Exception as e:
            self.status = old_status
            logger.error(f"Reload failed: {e}")
            return False
    
    def get_field_definitions(self) -> Dict[str, DynamicFieldDefinition]:
        return {k: v for k, v in self._field_definitions_cache.items() if v.active}
    
    def get_field_definition(self, field_code: str) -> Optional[DynamicFieldDefinition]:
        return self._field_definitions_cache.get(field_code)
    
    def add_field_definition(self, definition: DynamicFieldDefinition) -> bool:
        if not definition.is_valid():
            logger.error(f"Invalid definition for field {definition.code}")
            return False
        
        self._field_definitions_cache[definition.code] = definition
        logger.info(f"Added field definition: {definition.code}")
        return True
    
    def remove_field_definition(self, field_code: str) -> bool:
        if field_code in self._field_definitions_cache:
            del self._field_definitions_cache[field_code]
            logger.info(f"Removed field definition: {field_code}")
            return True
        return False
    
    def update_field_definition(self, definition: DynamicFieldDefinition) -> bool:
        if not definition.is_valid():
            logger.error(f"Invalid definition for field {definition.code}")
            return False
        
        if definition.code in self._field_definitions_cache:
            definition.updated_at = datetime.now()
            self._field_definitions_cache[definition.code] = definition
            logger.info(f"Updated field definition: {definition.code}")
            return True
        else:
            logger.warning(f"Field not found for update: {definition.code}")
            return False
    
    def get_custom_validator(self, validator_name: str):
        if validator_name in self._custom_validators_cache:
            return self._custom_validators_cache[validator_name]
        
        if self.custom_validators_module and hasattr(self.custom_validators_module, validator_name):
            return getattr(self.custom_validators_module, validator_name)
        
        return None
    
    def list_available_validators(self) -> List[str]:
        validators = []
        
        if self._custom_validators_cache:
            validators.extend(self._custom_validators_cache.keys())
        
        if (self.custom_validators_module and 
            hasattr(self.custom_validators_module, 'list_available_validators')):
            validators.extend(self.custom_validators_module.list_available_validators())
        
        return list(set(validators))
    
    def export_configuration(self, output_path: Union[str, Path], format: str = 'yaml') -> bool:
        try:
            output_path = Path(output_path)
            
            export_data = {
                'system': {
                    'version': '2.0.0',
                    'auto_reload': self.auto_reload_enabled,
                    'last_updated': datetime.now().isoformat(),
                    'reload_interval_seconds': self.reload_interval_seconds
                },
                'field_definitions': {
                    'dynamic_fields': {}
                }
            }
            
            for field_code, definition in self._field_definitions_cache.items():
                if field_code not in self.core_fields:
                    export_data['field_definitions']['dynamic_fields'][field_code] = definition.to_dict()
            
            self._save_config_file(export_data, output_path)
            
            logger.info(f"Configuration exported to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        definitions = self.get_field_definitions()
        
        erp_counts = {}
        total_synonyms = 0
        
        for definition in definitions.values():
            if hasattr(definition, 'synonyms_by_erp'):
                for erp_system, synonyms in definition.synonyms_by_erp.items():
                    if erp_system not in erp_counts:
                        erp_counts[erp_system] = 0
                    erp_counts[erp_system] += len(synonyms)
                    total_synonyms += len(synonyms)
        
        return {
            "status": self.status.value,
            "total_fields": len(self._field_definitions_cache),
            "active_fields": len(definitions),
            "core_fields": len(self.core_fields),
            "dynamic_fields": len(definitions) - len(self.core_fields),
            "total_synonyms": total_synonyms,
            "erp_systems": len(erp_counts),
            "synonyms_by_erp": erp_counts,
            "last_reload": self.last_reload_time.isoformat() if self.last_reload_time else None,
            "auto_reload_enabled": self.auto_reload_enabled,
            "config_hash": self._last_config_hash,
            "stats": self.stats.copy(),
            "config_history": self._config_history.copy()
        }
    
    def debug_synonyms(self, field_code: str = None):
        if field_code:
            field_def = self.get_field_definition(field_code)
            if field_def:
                if hasattr(field_def, 'synonyms_by_erp'):
                    for erp, synonyms in field_def.synonyms_by_erp.items():
                        for i, syn in enumerate(synonyms, 1):
                            pass  # Debug information removed
                else:
                    pass  # No synonyms_by_erp attribute found
            else:
                pass  # Field not found
        else:
            definitions = self.get_field_definitions()
            for code, field_def in definitions.items():
                if hasattr(field_def, 'synonyms_by_erp') and field_def.synonyms_by_erp:
                    total_synonyms = sum(len(synonyms) for synonyms in field_def.synonyms_by_erp.values())
    
    def shutdown(self):
        self._stop_reload.set()
        if self._reload_thread:
            self._reload_thread.join(timeout=5)
        logger.info("DynamicFieldLoader shutdown complete")

def create_field_loader(config_file: str = None, auto_reload: bool = True) -> DynamicFieldLoader:
    return DynamicFieldLoader(
        config_source=config_file,
        auto_reload=auto_reload
    )