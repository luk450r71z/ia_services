import logging
from secrets import compare_digest
from typing import Optional, Dict, Any

from auth.db.database import USERS
from auth.db.sqlite_db import create_session_db

logger = logging.getLogger(__name__)

class AuthService:
    """Servicio para manejar autenticación y creación de sesiones"""
    
    @staticmethod
    def validate_credentials(username: str, password: str) -> bool:
        """
        Valida credenciales de usuario
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            
        Returns:
            bool: True si las credenciales son válidas
        """
        return username in USERS and compare_digest(USERS[username], password)
    
    @staticmethod
    def create_user_session(
        username: str,
        session_type: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
        configs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crea una nueva sesión para un usuario autenticado
        
        Args:
            username: Usuario autenticado
            session_type: Tipo de sesión opcional
            content: Contenido de la sesión
            configs: Configuraciones de la sesión
            
        Returns:
            Dict con información de la sesión creada
            
        Raises:
            Exception: Si hay error al crear la sesión
        """
        logger.info(f"Creando sesión para usuario: {username}")
        
        session = create_session_db(
            type_value=session_type,
            content={"username": username, **(content or {})},
            configs=configs
        )
        
        if not session:
            raise Exception("No se pudo crear la sesión en la base de datos")
        
        logger.info(f"Sesión creada exitosamente: {session['id_session']}")
        return session 