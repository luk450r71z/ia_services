"""
Utilidades para manejo de variables de entorno y configuración.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, List


def load_env_variables(env_filename: str = ".env") -> bool:
    """
    Carga variables de entorno desde diferentes ubicaciones posibles.
    
    Args:
        env_filename: Nombre del archivo de entorno (por defecto: .env)
        
    Returns:
        True si se cargó un archivo .env, False si solo se usó el fallback
    """
    current_dir = Path.cwd()
    possible_env_files = [
        current_dir / env_filename,
        current_dir.parent / env_filename,
        Path(__file__).parent / env_filename,
        Path(__file__).parent.parent / env_filename
    ]
    
    for env_file in possible_env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)
            print(f"✅ Variables de entorno cargadas desde: {env_file}")
            return True
    
    # Fallback: cargar desde ubicación por defecto
    load_dotenv(override=True)
    print(f"⚠️ No se encontró archivo {env_filename}, usando variables del sistema")
    return False


def get_env_variable(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Obtiene una variable de entorno con manejo de errores.
    
    Args:
        key: Nombre de la variable de entorno
        default: Valor por defecto si no existe
        required: Si es True, lanza excepción si no existe
        
    Returns:
        Valor de la variable de entorno
        
    Raises:
        ValueError: Si la variable es requerida y no existe
    """
    value = os.getenv(key, default)
    
    if required and value is None:
        raise ValueError(f"Variable de entorno requerida '{key}' no encontrada")
    
    return value


def check_required_env_variables(required_vars: List[str]) -> List[str]:
    """
    Verifica que todas las variables de entorno requeridas estén presentes.
    
    Args:
        required_vars: Lista de nombres de variables requeridas
        
    Returns:
        Lista de variables faltantes (vacía si todas están presentes)
    """
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars


def print_env_status(required_vars: List[str] = None) -> None:
    """
    Imprime el estado de las variables de entorno importantes.
    
    Args:
        required_vars: Lista de variables requeridas a verificar
    """
    print("🔧 Estado de variables de entorno:")
    print("-" * 40)
    
    # Variables comunes del proyecto
    common_vars = ["GROQ_API_KEY", "SMTP_SERVER", "SENDER_EMAIL", "RECIPIENT_EMAIL"]
    
    if required_vars:
        vars_to_check = required_vars
    else:
        vars_to_check = common_vars
    
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            # Mostrar solo los primeros y últimos caracteres de claves sensibles
            if "KEY" in var or "PASSWORD" in var or "TOKEN" in var:
                masked_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
                print(f"  ✅ {var}: {masked_value}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: No configurada")
    
    print("-" * 40) 