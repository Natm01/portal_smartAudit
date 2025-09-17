import os
import logging
from typing import Dict, Any

from procesos_estructura.model_processor import DocumentPredict
from procesos_estructura.prediction_processor import procesar_csv_estructura
from procesos_estructura.tabular_processor import process_csv_tabular
from services.storage.azure_storage_service import get_azure_storage_service
from services.storage.temp_file_manager import get_temp_file_manager
from config.settings import get_settings

logger = logging.getLogger(__name__)

class ConversionService:
    """Clean conversion service with separated Azure operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.azure_service = get_azure_storage_service()
        self.temp_manager = get_temp_file_manager()
    
    async def convert_file(self, azure_file_path: str, execution_id: str) -> Dict[str, Any]:
        """Convert file through complete pipeline with clean separation"""
        try:
            logger.info(f"Starting conversion for file: {azure_file_path}")
            
            with self.temp_manager.get_local_file(azure_file_path) as input_file:
                with self.temp_manager.create_temp_file('.csv') as prediction_file:
                    with self.temp_manager.create_temp_file('.csv') as processed_file:
                        with self.temp_manager.create_temp_file('.csv') as result_file:
                            
                            conversion_result = self._run_conversion_pipeline(
                                input_file, prediction_file, processed_file, result_file
                            )
                            
                            azure_result_path = self.azure_service.upload_file_chunked(
                                result_file,
                                container_type="results",
                                execution_id=execution_id
                            )
                            
                            intermediate_files = await self._upload_intermediate_files(
                                prediction_file, processed_file, execution_id
                            )
                            
                            return {
                                "success": True,
                                "result_path": azure_result_path,
                                "stats": conversion_result["stats"],
                                "intermediate_files": intermediate_files,
                                "message": conversion_result["message"]
                            }
                            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            raise Exception(f"Conversion failed: {str(e)}")
    
    def _run_conversion_pipeline(self, input_file: str, prediction_file: str, 
                               processed_file: str, result_file: str) -> Dict[str, Any]:
        """Run the complete conversion pipeline on local files"""
        
        logger.info("Running model prediction")
        tester = DocumentPredict(model_dirs=self.settings.model_dirs)
        test_df = tester.load_test_file(input_file)
        results_df = tester.predict_file(test_df)
        
        if 'confidence' in results_df.columns:
            mean_confidence = results_df['confidence'].mean()
            logger.info(f"Mean confidence: {mean_confidence:.3f}")
            
            if mean_confidence < self.settings.rejection_threshold:
                raise Exception(
                    f"Este archivo no parece ser un libro diario contable válido. "
                    f"La confianza del modelo es muy baja ({mean_confidence:.1%}). "
                    f"Se requiere una confianza mínima del {self.settings.rejection_threshold:.1%}. "
                    f"Por favor, verifique que el archivo contenga datos contables estructurados."
                )
        
        tester.save_results(results_df, prediction_file)
        
        logger.info("Processing predictions")
        procesar_csv_estructura(prediction_file, processed_file)
        
        logger.info("Generating final table")
        df = process_csv_tabular(processed_file, result_file)
        
        stats = {
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": list(df.columns),
            "mean_confidence": float(results_df['confidence'].mean()) if 'confidence' in results_df.columns else None,
            "storage_type": "azure"
        }
        
        message = f"Conversion completed successfully. Generated {df.shape[0]} rows, {df.shape[1]} columns"
        
        return {
            "stats": stats,
            "message": message
        }
    
    async def _upload_intermediate_files(self, prediction_file: str, processed_file: str, 
                                       execution_id: str) -> Dict[str, str]:
        """Upload intermediate files to Azure"""
        intermediate_files = {}
        
        try:
            if os.path.exists(prediction_file):
                with open(prediction_file, 'rb') as f:
                    pred_data = f.read()
                pred_url = self.azure_service.upload_from_memory(
                    pred_data,
                    f"prediction_{execution_id}.csv",
                    container_type="predictions",
                    execution_id=execution_id
                )
                intermediate_files["prediction_path"] = pred_url
            
            if os.path.exists(processed_file):
                with open(processed_file, 'rb') as f:
                    proc_data = f.read()
                proc_url = self.azure_service.upload_from_memory(
                    proc_data,
                    f"processed_{execution_id}.csv",
                    container_type="processed",
                    execution_id=execution_id
                )
                intermediate_files["processed_path"] = proc_url
                
        except Exception as e:
            logger.warning(f"Error uploading intermediate files: {e}")
        
        return intermediate_files

_conversion_service = None

def get_conversion_service() -> ConversionService:
    """Get global conversion service instance"""
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = ConversionService()
    return _conversion_service