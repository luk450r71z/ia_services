import logging
import aiohttp
import json
from typing import Optional, Dict, Any

from ..models.log_models import MessageLog, LogStatus
from .session_service import SessionService
from auth.db.sqlite_db import update_session_logs, get_session_logs, get_session_db

logger = logging.getLogger(__name__)

class LogService:
    """Servicio para manejar logs de mensajes y notificaciones al webhook"""
    
    def __init__(self):
        self.max_retries = 5  # Número máximo de intentos antes de marcar como SKIPPED
    
    async def log_message(
        self,
        id_session: str,
        message_type: str,
        content: str,
        status: LogStatus = LogStatus.ANSWERED,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MessageLog:
        """Registra un nuevo mensaje y envía notificación al webhook"""
        try:
            # Obtener logs previos de la sesión
            session_logs = get_session_logs(id_session) or []
            attempt_number = 1
            
            if session_logs:
                last_log = session_logs[-1]
                if last_log.get('content') == content:
                    attempt_number = last_log.get('attempt_number', 0) + 1
            
            # Crear nuevo log
            log = MessageLog(
                id_session=id_session,
                message_type=message_type,
                content=content,
                status=status,
                attempt_number=attempt_number,
                metadata=metadata or {}
            )
            
            # Guardar en base de datos
            try:
                # Convertir a JSON y luego a dict para asegurar serialización correcta
                log_dict = json.loads(log.json())
                update_session_logs(id_session, log_dict)
            except Exception as e:
                logger.error(f"Error actualizando logs en base de datos: {str(e)}")
                raise
            
            # Enviar al webhook
            try:
                await self._send_to_webhook(log)
            except Exception as e:
                logger.error(f"Error enviando al webhook: {str(e)}")
                # No propagamos el error del webhook para no interrumpir el flujo principal
            
            return log
            
        except Exception as e:
            logger.error(f"Error guardando log: {str(e)}")
            raise
    
    async def _send_to_webhook(self, log: MessageLog) -> None:
        """Envía el log al webhook configurado"""
        try:
            # Obtener datos de sesión
            session_data = get_session_db(log.id_session)
            if not session_data:
                logger.warning(f"No se encontró la sesión {log.id_session}")
                return
                
            if not session_data.get('configs', {}).get('webhook_url'):
                logger.warning(f"No webhook URL configured for session {log.id_session}")
                return
            
            webhook_url = session_data['configs']['webhook_url']
            
            # Convertir log a diccionario para el webhook
            webhook_data = json.loads(log.json())
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=webhook_data,
                    timeout=5
                ) as response:
                    # Actualizar el log existente con la información del webhook
                    log.webhook_sent = True
                    log.webhook_response = {
                        "status": response.status,
                        "response": await response.text()
                    }
                    
                    # Actualizar el log existente en la base de datos
                    try:
                        # Obtener logs actuales
                        session_logs = get_session_logs(log.id_session) or []
                        if session_logs:
                            # Reemplazar el último log con el actualizado
                            session_logs[-1] = json.loads(log.json())
                            # Actualizar todos los logs
                            update_session_logs(log.id_session, session_logs[-1])
                    except Exception as e:
                        logger.error(f"Error actualizando log con respuesta del webhook: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error sending log to webhook: {str(e)}")
            log.webhook_sent = False
            log.webhook_response = {"error": str(e)}
            
            # Actualizar el log existente con el error
            try:
                # Obtener logs actuales
                session_logs = get_session_logs(log.id_session) or []
                if session_logs:
                    # Reemplazar el último log con el actualizado
                    session_logs[-1] = json.loads(log.json())
                    # Actualizar todos los logs
                    update_session_logs(log.id_session, session_logs[-1])
            except Exception as db_error:
                logger.error(f"Error actualizando log con error del webhook: {str(db_error)}")
    
    def get_session_logs(self, id_session: str) -> list[MessageLog]:
        """Obtiene todos los logs de una sesión"""
        try:
            logs = get_session_logs(id_session)
            if logs is None:
                logger.warning(f"No se encontraron logs para la sesión {id_session}")
                return []
            return [MessageLog(**log) for log in logs]
        except Exception as e:
            logger.error(f"Error obteniendo logs de sesión: {str(e)}")
            return []

# Instancia global del servicio
log_service = LogService() 