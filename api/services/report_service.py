import logging
from typing import Dict, Any

from procesos_mapeo.comprehensive_reporter import get_comprehensive_reporter
from services.storage.azure_storage_service import get_azure_storage_service

logger = logging.getLogger(__name__)

class ReportService:
    """Clean report service using comprehensive reporter only"""
    
    def __init__(self):
        self.azure_service = get_azure_storage_service()
        self.reporter = get_comprehensive_reporter()
    
    async def generate_mapeo_report(self, mapeo_data: Dict[str, Any], 
                                  execution_id: str = None) -> str:
        """Generate comprehensive mapeo report and upload to Azure"""
        try:
            logger.info("Generating comprehensive mapeo report")
            
            report_content = self.reporter.generate_mapeo_report(mapeo_data)
            
            if execution_id:
                filename = f"mapeo_report_{execution_id}.txt"
            else:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"mapeo_report_{timestamp}.txt"
            
            azure_report_path = self.azure_service.upload_from_memory(
                report_content.encode('utf-8'),
                filename,
                container_type="mapeos",
                execution_id=execution_id
            )
            
            logger.info(f"Report uploaded to Azure: {azure_report_path}")
            return azure_report_path
            
        except Exception as e:
            logger.error(f"Error generating mapeo report: {e}")
            raise Exception(f"Report generation failed: {str(e)}")

_report_service = None

def get_report_service() -> ReportService:
    """Get global report service instance"""
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service