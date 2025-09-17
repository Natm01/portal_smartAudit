from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/smau-proto/api/projects", tags=["projects"])

def get_projects_file_path() -> str:
    """Obtener la ruta del archivo de proyectos"""
    return os.path.join(os.path.dirname(__file__), "..", "data", "projects.json")

def load_projects() -> List[Dict[str, Any]]:
    """Cargar proyectos desde el archivo JSON"""
    try:
        projects_file = get_projects_file_path()
        with open(projects_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            projects = data.get("projects", [])
            logger.info(f"Loaded {len(projects)} projects")
            return projects
    except FileNotFoundError:
        logger.error("Projects file not found")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Projects configuration file not found"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in projects file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Invalid projects configuration file format"
        )
    except Exception as e:
        logger.error(f"Error loading projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error loading projects configuration"
        )

@router.get("/", response_model=Dict[str, Any])
async def get_all_projects():
    """
    Obtener todos los proyectos disponibles
    
    Returns:
        Dict con success, projects y total count
    """
    try:
        projects = load_projects()
        logger.info(f"Retrieved {len(projects)} projects")
        
        return {
            "success": True,
            "projects": projects,
            "total": len(projects)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )

@router.get("/{project_id}", response_model=Dict[str, Any])
async def get_project_by_id(project_id: str):
    """
    Obtener un proyecto específico por ID
    
    Args:
        project_id: ID único del proyecto
        
    Returns:
        Dict con success y project data
        
    Raises:
        404: Si el proyecto no existe
    """
    try:
        projects = load_projects()
        project = next((p for p in projects if p["id"] == project_id), None)
        
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Project with ID '{project_id}' not found"
            )
        
        logger.info(f"Retrieved project: {project_id}")
        return {
            "success": True,
            "project": project
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )