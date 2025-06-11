import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from auth.db.sqlite_db import get_session_db, update_session_db

logger = logging.getLogger(__name__)

class SessionService:
    """Servicio para manejar operaciones de sesiones"""
    
    @staticmethod
    def validate_session_for_start(session_id: str) -> Optional[Dict[str, Any]]:
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

    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene los datos de una sesión
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Dict con datos de sesión o None si no existe
        """
        return get_session_db(session_id)
    
    @staticmethod
    def update_session_content(session_id: str, new_content: Dict[str, Any] = None, new_configs: Dict[str, Any] = None, session_type: str = None) -> Dict[str, Any]:
        """
        Actualiza el content y configs de una sesión preservando datos existentes
        
        Args:
            session_id: ID de la sesión
            new_content: Nuevo content a agregar/actualizar
            new_configs: Nuevos configs a agregar/actualizar
            session_type: Tipo de sesión (opcional, para establecer el tipo)
            
        Returns:
            Dict con datos de sesión actualizada
            
        Raises:
            ValueError: Si la sesión no es válida
        """
        session = SessionService.validate_session_for_initiate(session_id)
        
        # Merge simple: existing + new (manejar None correctamente)
        existing_content = session.get('content') or {}
        existing_configs = session.get('configs') or {}
        
        merged_content = {**existing_content, **(new_content or {})}
        merged_configs = {**existing_configs, **(new_configs or {})}
        
        # Actualizar usando la función existente
        updated_session = update_session_db(
            session_id=session_id,
            type_value=session_type or session.get('type'),
            status=session.get('status', 'new'),
            content=merged_content,
            configs=merged_configs
        )
        
        if not updated_session:
            raise Exception("Error al actualizar la sesión")
            
        return updated_session
    
    @staticmethod
    def complete_session_with_summary(session_id: str, conversation_summary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Finaliza una sesión agregando el resumen de conversación
        
        Args:
            session_id: ID de la sesión
            conversation_summary: Resumen de la conversación
            
        Returns:
            Dict con datos de sesión actualizada o None si hay error
        """
        try:
            logger.info(f"📝 Finalizando sesión {session_id} con resumen...")
            
            # Obtener sesión actual
            session_data = get_session_db(session_id)
            if not session_data:
                logger.error(f"❌ No se pudo obtener datos de sesión: {session_id}")
                return None
            
            # Actualizar content con resumen
            original_content = session_data.get('content', {})
            final_content = original_content.copy()
            final_content["summary"] = conversation_summary
            
            # Actualizar estado en BD
            updated_session = update_session_db(
                session_id=session_id,
                type_value=session_data.get('type', 'unknown'),
                status="complete",
                content=final_content,
                configs=session_data.get('configs', {})
            )
            
            if updated_session:
                logger.info(f"✅ Sesión finalizada: {session_id}")
                return updated_session
            else:
                logger.warning(f"⚠️ No se pudo actualizar estado de sesión: {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finalizando sesión {session_id}: {str(e)}")
            return None 