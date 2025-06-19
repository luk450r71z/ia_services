import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import json

from auth.db.sqlite_db import get_session_db, update_session_db

logger = logging.getLogger(__name__)

class SessionService:
    """Servicio para manejar operaciones de sesiones"""
    
    # ===== Métodos de validación =====
    
    @staticmethod
    def _validate_session_expiration(session: Dict[str, Any]) -> bool:
        """Valida si una sesión no ha expirado (5 minutes)"""
        try:
            created_at = session['created_at']
            if isinstance(created_at, str):
                created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            elif not isinstance(created_at, datetime):
                logger.error(f"Invalid date format in session: {created_at}")
                return False
            
            return datetime.now(timezone.utc) - created_at <= timedelta(minutes=5)
        except (KeyError, ValueError) as e:
            logger.error(f"Error validating session expiration: {str(e)}")
            return False

    @staticmethod
    def validate_and_start_session(id_session: str) -> Optional[Dict[str, Any]]:
        """Valida y actualiza el estado de una sesión para WebSocket.
        Si la sesión está en estado 'initiated', la marca como 'started'.
        Si la sesión ya está en estado 'started', permite reconexión.
        Retorna la sesión actualizada o None si hay algún error."""
        session = get_session_db(id_session)
        if not session:
            logger.warning(f"Session not found: {id_session}")
            return None
        
        # Verificar expiración y marcar como expired si es necesario
        if not SessionService._validate_session_expiration(session):
            update_session_db(
                id_session=id_session,
                type_value=session.get('type'),
                status="expired",
                content=session.get('content', {}),
                configs=session.get('configs', {})
            )
            logger.warning(f"Session expirada: {id_session}")
            return None
        
        # Validar estados permitidos para conexión WebSocket
        estados_permitidos = ['initiated', 'started']
        if session['status'] not in estados_permitidos:
            logger.warning(f"Estado de sesión no permitido para conexión WebSocket: {session['status']}")
            return None
        
        # Si está initiated, actualizar a started
        if session['status'] == 'initiated':
            updated_session = update_session_db(
                id_session=id_session,
                type_value=session.get('type'),
                status="started",
                content=session.get('content'),
                configs=session.get('configs', {})
            )
            if updated_session:
                logger.info(f"✅ Sesión {id_session} actualizada a 'started'")
                return updated_session
            else:
                logger.warning(f"⚠️ No se pudo actualizar estado de sesión: {id_session}")
                return None
        
        # Si ya está started, permitir reconexión
        if session['status'] == 'started':
            logger.info(f"✅ Reconexión permitida para sesión {id_session} en estado 'started'")
            return session
            
        return None

    @staticmethod
    def validate_and_initiate_session(id_session: str, new_content: Dict[str, Any] = None, new_configs: Dict[str, Any] = None, session_type: str = None) -> Dict[str, Any]:
        """Valida y actualiza el estado de una sesión para inicialización.
        Si se proporcionan, actualiza el contenido y configuraciones.
        Retorna la sesión actualizada o lanza una excepción si hay algún error."""
        session = get_session_db(id_session)
        if not session:
            raise ValueError("Session not found")
        
        # Verificar tiempo de expiración y marcar como expired si es necesario
        if not SessionService._validate_session_expiration(session):
            update_session_db(
                id_session=id_session,
                type_value=session.get('type'),
                status="expired",
                content=session.get('content', {}),
                configs=session.get('configs', {})
            )
            raise ValueError(f"Session expired. Maximum 5 minutes from creation")
        
        # Validar estados no permitidos
        estados_no_permitidos = ['started', 'ended', 'initiated']
        if session['status'] in estados_no_permitidos:
            raise ValueError(f"Cannot restart a session that is already in '{session['status']}' status")
        
        # Validar tipos de datos para nuevo contenido/configs
        if new_content is not None and not isinstance(new_content, dict):
            raise ValueError("Content must be a dictionary")
        if new_configs is not None and not isinstance(new_configs, dict):
            raise ValueError("Configurations must be a dictionary")
        
        # Usar el nuevo contenido si se proporciona, sino mantener el existente
        final_content = new_content if new_content is not None else session.get('content', {})
        final_configs = new_configs if new_configs is not None else session.get('configs', {})
        
        # Actualizar la sesión con nuevo contenido/configs y estado initiated
        updated_session = update_session_db(
            id_session=id_session,
            type_value=session_type or session.get('type'),
            status="initiated",
            content=final_content,
            configs=final_configs
        )
        
        if not updated_session:
            raise Exception("Error updating session")
            
        return updated_session

    # ===== Métodos de finalización =====
    
    @staticmethod
    def complete_session_with_summary(id_session: str, conversation_summary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Finaliza una sesión agregando el resumen de conversación"""
        try:
            logger.info(f"📝 Finalizando sesión {id_session} con resumen...")
            
            # Obtener sesión actual
            session_data = get_session_db(id_session)
            if not session_data:
                logger.error(f"❌ No se pudo obtener datos de sesión: {id_session}")
                return None
            
            # Actualizar content con resumen
            original_content = session_data.get('content', {})
            final_content = original_content.copy()
            final_content["summary"] = conversation_summary
            
            # Actualizar estado en BD
            updated_session = update_session_db(
                id_session=id_session,
                type_value=session_data.get('type', 'unknown'),
                status="ended",
                content=final_content,
                configs=session_data.get('configs', {})
            )
            
            if updated_session:
                logger.info(f"✅ Sesión finalizada: {id_session}")
                return updated_session
            else:
                logger.warning(f"⚠️ No se pudo actualizar estado de sesión: {id_session}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finalizando sesión {id_session}: {str(e)}")
            return None 