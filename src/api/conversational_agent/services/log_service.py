import logging
import aiohttp
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from ..models.log_models import WebhookLog
from .session_service import SessionService
from auth.db.sqlite_db import update_session_logs, get_session_logs, get_session_db

logger = logging.getLogger(__name__)

class LogService:
    """Servicio para manejar logs de mensajes y notificaciones al webhook"""
    
    def __init__(self):
        self.max_retries = 5  # Número máximo de intentos antes de marcar como SKIPPED
    
    def _get_event(self, message_type: str) -> str:
        """Determina el evento basado en el tipo de mensaje"""
        if message_type == "user":
            return "onUserMessage"
        elif message_type == "agent":
            return "onAgentMessage"
        else:
            return "onEvent"
    
    async def log_message(
        self,
        id_session: str,
        message_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WebhookLog:
        """Registra un nuevo mensaje y envía notificación al webhook"""
        try:     
            # Determinar el evento
            event = self._get_event(message_type)
            
            # Crear el log usando WebhookLog directamente
            log = WebhookLog(
                event=event,
                datetime=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                status="Success", #TODO: cambiar
                message=content,
                data={}
            )
            
            # Incluir métricas del usuario si están disponibles
            if metadata and metadata.get('user_metrics'):
                log.data['user_metrics'] = metadata['user_metrics']
            
            # Guardar en base de datos
            try:
                update_session_logs(id_session, log.dict())
            except Exception as e:
                logger.error(f"Error actualizando logs en base de datos: {str(e)}")
                raise
            
            # Enviar al webhook
            try:
                await self._send_to_webhook(log, id_session)
            except Exception as e:
                logger.error(f"Error enviando al webhook: {str(e)}")
                # No propagamos el error del webhook para no interrumpir el flujo principal
            
            return log
            
        except Exception as e:
            logger.error(f"Error guardando log: {str(e)}")
            raise
    
    async def _send_to_webhook(self, log: WebhookLog, id_session: str) -> None:
        """Envía el log al webhook configurado"""
        try:
            # Obtener datos de sesión
            session_data = get_session_db(id_session)
            if not session_data:
                logger.warning(f"No se encontró la sesión {id_session}")
                return
                
            if not session_data.get('configs', {}).get('webhook_url'):
                logger.warning(f"No webhook URL configured for session {id_session}")
                return
            
            webhook_url = session_data['configs']['webhook_url']
            
            # Incluir métricas del usuario si están disponibles
            if log.data.get('user_metrics'):
                logger.info(f"📊 Incluyendo métricas del usuario en webhook: {log.data['user_metrics']}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=log.dict(),
                    timeout=5
                ) as response:
                    logger.info(f"Webhook enviado exitosamente: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error sending log to webhook: {str(e)}")

# Instancia global del servicio
log_service = LogService()