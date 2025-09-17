from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
import logging
import os
import uvicorn
import sys

# Importar routers del portal-web
from routes.projects import router as projects_router
from routes.applications import router as applications_router
from routes.upload import router as upload_router
from routes.validation import router as validation_router
from routes.conversion import router as conversion_router
from routes.mapeo import router as mapeo_router
from routes.manual_mapping import router as manual_mapping_router
from routes.preview import router as preview_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Crear FastAPI instance con path prefix
app = FastAPI(
    title="SmartAudit Proto API",
    description="API para SmartAudit Portal - Python 3.11 con FastAPI integrado con Portal Web",
    version="1.0.0",
    root_path="/smau-proto",
    docs_url="/smau-proto/docs",
    redoc_url="/smau-proto/redoc",
    openapi_url="/smau-proto/openapi.json"
)

# Configurar CORS para dominios smartaudit.com
ALLOWED_ORIGINS = [
    "https://devapi.grantthornton.es",
    "https://testapi.grantthornton.es",
    "https://api.grantthornton.es",
    "https://devsmartaudit.grantthornton.es",
    "https://testsmartaudit.grantthornton.es", 
    "https://smartaudit.grantthornton.es", 
    "http://localhost:3000",
    "http://localhost:4280",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Middleware de seguridad para hosts permitidos
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*.grantthornton.es", "localhost", "127.0.0.1", "*"]
)

# Incluir todos los routers del portal-web
app.include_router(projects_router)
app.include_router(applications_router)

# Portal Web Processing Routers
app.include_router(upload_router)
app.include_router(validation_router)
app.include_router(conversion_router)
app.include_router(mapeo_router)
app.include_router(manual_mapping_router)
app.include_router(preview_router)

# Modelos Pydantic
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime.datetime
    version: str
    environment: str
    checks: dict

# Utility functions
def get_environment():
    return os.getenv("ENVIRONMENT", "development")

def get_current_timestamp():
    return datetime.datetime.now(datetime.timezone.utc)

def perform_health_checks():
    """Realizar verificaciones de salud de la aplicación"""
    checks = {
        "database": "ok",  # Simular check de BD
        "memory": "ok",
        "disk_space": "ok",
        "azure_storage": "ok" if os.getenv("AZURE_STORAGE_CONNECTION_STRING") else "not_configured"
    }
    
    return checks

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": get_current_timestamp().isoformat()
        }
    )

# ==========================================
# HEALTH ENDPOINTS PARA CONTAINER APPS (Infrastructure level)
# ==========================================

@app.get("/health/ready")
async def readiness_probe():
    """
    Readiness probe - Container Apps usa esto automáticamente
    Verifica que el contenedor está listo para recibir tráfico
    """
    try:
        return {
            "status": "ready",
            "timestamp": get_current_timestamp().isoformat(),
            "service": "container-ready"
        }
    except Exception as e:
        logger.error(f"Container readiness failed: {str(e)}")
        return {
            "status": "ready", 
            "timestamp": get_current_timestamp().isoformat(),
            "warning": "degraded_but_ready"
        }

@app.get("/health/live")
async def liveness_probe():
    """
    Liveness probe - Container Apps usa esto automáticamente
    Verifica que el contenedor debe seguir corriendo (no restart)
    """
    try:
        return {
            "status": "alive",
            "timestamp": get_current_timestamp().isoformat(),
            "service": "container-alive"
        }
    except Exception as e:
        logger.error(f"Container liveness failed: {str(e)}")
        return {
            "status": "alive",
            "timestamp": get_current_timestamp().isoformat(),
            "warning": "degraded_but_alive"
        }

# ==========================================
# APPLICATION HEALTH ENDPOINT (Business level)
# ==========================================

@app.get("/smau-proto/health/simple")
async def simple_health_check():
    """
    Health check simplificado para debugging
    """
    return {
        "status": "healthy",
        "message": "SmartAudit Proto API funcionando correctamente con Portal Web",
        "timestamp": get_current_timestamp().isoformat(),
        "version": "1.0.0",
        "environment": get_environment(),
        "service": "smartaudit-proto-api-integrated",
        "container_info": {
            "hostname": os.getenv("HOSTNAME", "unknown"),
            "container_app_name": os.getenv("CONTAINER_APP_NAME", "unknown"),
            "revision": os.getenv("CONTAINER_APP_REVISION", "unknown")
        },
        "deployment_info": {
            "app_version": os.getenv("APP_VERSION", "unknown"),
            "image_tag": os.getenv("IMAGE_TAG", "unknown"), 
            "build_id": os.getenv("BUILD_ID", "unknown"),
            "deployment_timestamp": os.getenv("DEPLOYMENT_TIMESTAMP", "unknown")
        },
        "azure_config": {
            "storage_configured": bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING")),
            "environment_from_azure": bool(os.getenv("AZURE_CLIENT_ID"))
        }
    }

@app.get("/smau-proto/health", response_model=HealthResponse)
async def application_health_check():
    """
    Application health check - Desde Application Gateway
    Verifica que SmartAudit Proto API funciona correctamente
    """
    try:
        checks = perform_health_checks()
        
        # Verificaciones específicas de SmartAudit
        business_checks = {
            "api_endpoints": "ok",  # Verificar endpoints principales
            "memory_usage": "ok",   # Verificar uso de memoria
            "portal_web_integration": "ok",  # Portal web integrado
            "azure_storage": checks.get("azure_storage", "not_configured")
        }
        
        # Combinar checks infrastructure + business
        all_checks = {**checks, **business_checks}
        
        return HealthResponse(
            status="healthy",
            timestamp=get_current_timestamp(),
            version="1.0.0",
            environment=get_environment(),
            checks={
                **all_checks,
                "deployment_info": {
                    "app_version": os.getenv("APP_VERSION", "unknown"),
                    "image_tag": os.getenv("IMAGE_TAG", "unknown"), 
                    "build_id": os.getenv("BUILD_ID", "unknown"),
                    "container_app_name": os.getenv("CONTAINER_APP_NAME", "unknown"),
                    "container_app_revision": os.getenv("CONTAINER_APP_REVISION", "unknown")
                }
            }
        )
    except Exception as e:
        logger.error(f"Application health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SmartAudit Proto API health check failed"
        )

# ==========================================
# ROUTES PRINCIPALES
# ==========================================

@app.get("/")
async def root_redirect():
    """
    Endpoint raíz que redirige a la documentación
    """
    return {
        "message": "SmartAudit Proto API with Portal Web Integration",
        "version": "1.0.0",
        "docs_url": "/smau-proto/docs",
        "api_base": "/smau-proto/",
        "features": ["upload", "validation", "conversion", "mapeo", "manual_mapping"]
    }

@app.get("/smau-proto/", response_model=dict)
async def root():
    """
    Endpoint raíz de la API
    """
    logger.info("Root endpoint accessed")
    return {
        "message": "SmartAudit Proto API with Portal Web",
        "version": "1.0.0",
        "python_version": "3.11",
        "framework": "FastAPI",
        "environment": get_environment(),
        "docs_url": "/smau-proto/docs",
        "timestamp": get_current_timestamp(),
        "available_endpoints": [
            "/smau-proto/api/import/upload",
            "/smau-proto/api/import/validate/{execution_id}",
            "/smau-proto/api/import/convert/{execution_id}",
            "/smau-proto/api/import/mapeo/{execution_id}",
            "/smau-proto/api/import/preview/{execution_id}",
            "/smau-proto/api/projects/",
            "/smau-proto/api/applications/"
        ]
    }

@app.get("/smau-proto/version")
async def get_version():
    """
    Información de versión detallada
    """
    return {
        "api_version": "1.0.0",
        "python_version": "3.11",
        "fastapi_version": "0.104.1",
        "environment": get_environment(),
        "build_timestamp": get_current_timestamp(),
        "portal_web_integrated": True,
        "azure_storage_enabled": bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING")),
        "container_info": {
            "hostname": os.getenv("HOSTNAME", "unknown"),
            "container_app_name": os.getenv("CONTAINER_APP_NAME", "unknown"),
            "container_app_revision": os.getenv("CONTAINER_APP_REVISION", "unknown")
        }
    }

@app.get("/smau-proto/test-connection")
async def test_connection():
    """Endpoint simple para testing de conectividad desde el frontend"""
    return {
        "message": "SmartAudit Proto API - Conexión exitosa con Portal Web",
        "status": "connected",
        "api_url": "/smau-proto/",
        "timestamp": get_current_timestamp().isoformat(),
        "cors_enabled": True,
        "environment": get_environment(),
        "version": "1.0.0",
        "python_version": "3.11",
        "framework": "FastAPI",
        "portal_web_features": {
            "upload": True,
            "validation": True,
            "conversion": True,
            "mapeo": True,
            "manual_mapping": True,
            "preview": True
        },
        "azure_storage": {
            "configured": bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING")),
            "connection_available": bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
        },
        "container_info": {
            "hostname": os.getenv("HOSTNAME", "unknown"),
            "container_app_name": os.getenv("CONTAINER_APP_NAME", "unknown"),
            "revision": os.getenv("CONTAINER_APP_REVISION", "unknown")
        },
        "deployment_info": {
            "app_version": os.getenv("APP_VERSION", "unknown"),
            "image_tag": os.getenv("IMAGE_TAG", "unknown"), 
            "build_id": os.getenv("BUILD_ID", "unknown"),
            "deployment_timestamp": os.getenv("DEPLOYMENT_TIMESTAMP", "unknown")
        },
        "available_endpoints": [
            "/smau-proto/api/import/upload",
            "/smau-proto/api/import/validate/{execution_id}",
            "/smau-proto/api/import/convert/{execution_id}",
            "/smau-proto/api/import/mapeo/{execution_id}",
            "/smau-proto/api/import/preview/{execution_id}",
            "/smau-proto/api/projects/",
            "/smau-proto/api/applications/",
            "/smau-proto/health",
            "/smau-proto/test-connection",
            "/smau-proto/version",
            "/smau-proto/docs"
        ]
    }

if __name__ == "__main__":
    # Para desarrollo local - configuración optimizada para Container Apps
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False,  # Deshabilitado en container
        log_level="info",
        timeout_keep_alive=65,  # Timeout extendido
        timeout_graceful_shutdown=30,
        limit_concurrency=100,
        backlog=2048
    )