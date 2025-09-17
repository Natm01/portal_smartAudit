from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/smau-proto/api/applications", tags=["applications"])

def get_applications_file_path() -> str:
    """Obtener la ruta del archivo de aplicaciones"""
    return os.path.join(os.path.dirname(__file__), "..", "data", "applications.json")

def load_applications() -> List[Dict[str, Any]]:
    """Cargar aplicaciones desde el archivo JSON"""
    try:
        applications_file = get_applications_file_path()
        with open(applications_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            applications = data.get("applications", [])
            logger.info(f"Loaded {len(applications)} applications")
            return applications
    except FileNotFoundError:
        logger.error("Applications file not found")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Applications configuration file not found"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in applications file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Invalid applications configuration file format"
        )
    except Exception as e:
        logger.error(f"Error loading applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error loading applications configuration"
        )

@router.get("/", response_model=Dict[str, Any])
async def get_all_applications():
    """
    Obtener todas las aplicaciones activas
    
    Returns:
        Dict con success, applications (solo activas) y total count
    """
    try:
        applications = load_applications()
        # Filtrar solo aplicaciones activas
        active_applications = [app for app in applications if app.get("isActive", True)]
        
        logger.info(f"Retrieved {len(active_applications)} active applications from {len(applications)} total")
        
        return {
            "success": True,
            "applications": active_applications,
            "total": len(active_applications)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )

@router.get("/{application_id}", response_model=Dict[str, Any])
async def get_application_by_id(application_id: str):
    """
    Obtener una aplicación específica por ID
    
    Args:
        application_id: ID único de la aplicación
        
    Returns:
        Dict con success y application data
        
    Raises:
        404: Si la aplicación no existe o no está activa
    """
    try:
        applications = load_applications()
        application = next((app for app in applications if app["id"] == application_id), None)
        
        if not application:
            logger.warning(f"Application not found: {application_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Application with ID '{application_id}' not found"
            )
        
        if not application.get("isActive", True):
            logger.warning(f"Application is inactive: {application_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Application with ID '{application_id}' is not active"
            )
        
        logger.info(f"Retrieved application: {application_id}")
        return {
            "success": True,
            "application": application
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving application {application_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )