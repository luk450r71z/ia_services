import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from auth.db.sqlite_db import get_session_db, update_session_db

logger = logging.getLogger(__name__)

class SessionService:
    """Servicio para manejar operaciones de sesiones"""
    
    @staticmethod
    def validate_session_for_websocket(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Valida sesión para WebSocket con lógica mínima
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Dict con datos de sesión si es válida, None si no
        """
        session = get_session_db(session_id)
        if not session:
            return None
        
        # Verificar expiración (5 minutos)
        created_at = session['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        if datetime.utcnow() - created_at > timedelta(minutes=5):
            return None
        
        # Debe estar initiated para poder iniciar WebSocket
        if session['status'] not in ['initiated', 'started']:
            return None
            
        return session
    
    @staticmethod
    def validate_session_for_initiate(session_id: str) -> Dict[str, Any]:
        """
        Valida y obtiene sesión para inicialización
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Dict con datos de sesión
            
        Raises:
            ValueError: Si la sesión no es válida
        """
        session = get_session_db(session_id)
        if not session:
            raise ValueError("Sesión no encontrada")
        
        # Verificar tiempo de expiración (5 minutos)
        created_at = session['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        time_diff = datetime.utcnow() - created_at
        if time_diff > timedelta(minutes=5):
            # Actualizar status como expired
            service_type = session.get('type')
            content = session.get('content', {})
            configs = session.get('configs', {})
            
            update_session_db(
                session_id=session_id,
                type_value=service_type,
                status="expired",
                content=content,
                configs=configs or {}
            )
            raise ValueError(f"Sesión expirada. Máximo 5 minutos desde la creación")
        
        # El contenido se validará en el endpoint de inicialización
        # No es necesario que esté presente en este punto
            
        return session
    
    @staticmethod
    def initiate_session(session_id: str) -> Dict[str, Any]:
        """
        Inicializa una sesión cambiando su status a 'initiated'
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Dict con datos de sesión actualizada
            
        Raises:
            Exception: Si hay error al actualizar
        """
        session = SessionService.validate_session_for_initiate(session_id)
        
        service_type = session.get('type')
        content = session.get('content', {})
        configs = session.get('configs', {})
        
        # Actualizar la sesión en la base de datos
        updated_session = update_session_db(
            session_id=session_id,
            type_value=service_type,
            status="initiated",
            content=content,
            configs=configs
        )
        
        if not updated_session:
            raise Exception("Error al actualizar la sesión")
            
        return updated_session
    
    @staticmethod
    def start_session(session_id: str, session_data: Dict[str, Any]) -> None:
        """
        Marca una sesión como 'started'
        
        Args:
            session_id: ID de la sesión
            session_data: Datos de la sesión
        """
        if session_data['status'] == 'initiated':
            content = session_data.get('content')
            update_session_db(
                session_id=session_id,
                type_value=session_data.get('type'),
                status="started",
                content=content,
                configs=session_data.get('configs', {})
            )
            logger.info(f"✅ Sesión {session_id} actualizada a 'started'") 