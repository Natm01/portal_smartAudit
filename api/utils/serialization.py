# utils/serialization.py
"""
Utilities for serialization and type conversion
"""
import numpy as np
import math
from typing import Any, Dict, List, Union

def convert_numpy_types(obj: Any) -> Any:
    """
    Convierte recursivamente tipos numpy a tipos Python nativos para serialización JSON
    Maneja valores NaN y los convierte a None para compatibilidad con JSON
    
    Args:
        obj: Objeto que puede contener tipos numpy
        
    Returns:
        Objeto con tipos Python nativos y valores NaN convertidos a None
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        # Verificar si es NaN, infinito o un número válido
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    elif isinstance(obj, float):
        # Manejar valores float nativos de Python que también pueden ser NaN
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    else:
        return obj

def safe_json_response(data: Any) -> Any:
    """
    Convierte datos para respuesta JSON segura
    Maneja valores NaN, infinitos y tipos numpy
    
    Args:
        data: Datos a convertir
        
    Returns:
        Datos seguros para JSON
    """
    return convert_numpy_types(data)