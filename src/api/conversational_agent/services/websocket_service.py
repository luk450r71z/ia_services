import logging
import json
from typing import Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketService:
    """Servicio para manejar lógica de comunicación WebSocket"""
    
    @staticmethod
    async def initialize_agent_and_send_welcome(websocket_manager, session_id: str, session_data: Dict[str, Any]) -> None:
        """
        Inicializa agente y envía mensaje de bienvenida
        
        Args:
            websocket_manager: Manager de WebSockets
            session_id: ID de la sesión
            session_data: Datos de la sesión
        """
        try:
            agent_initialized = await websocket_manager.initialize_agent(session_id, session_data)
            if agent_initialized:
                welcome_message = websocket_manager.get_welcome_message(session_id)
                if welcome_message:
                    await websocket_manager.send_message(
                        session_id,
                        "agent_response", 
                        welcome_message,
                        {"is_welcome": True}
                    )
                    logger.info(f"📨 Mensaje de bienvenida enviado a sesión: {session_id}")
            else:
                logger.warning(f"⚠️ No se pudo inicializar agente para sesión: {session_id}")
        except Exception as e:
            logger.error(f"❌ Error inicializando agente: {str(e)}")
    
    @staticmethod
    async def handle_message_loop(websocket_manager, websocket: WebSocket, session_id: str) -> None:
        """
        Maneja el bucle principal de mensajes WebSocket
        
        Args:
            websocket_manager: Manager de WebSockets
            websocket: Conexión WebSocket
            session_id: ID de la sesión
        """
        try:
            while True:
                message_data = await websocket.receive_text()
                logger.debug(f"📨 Mensaje recibido de {session_id}: {message_data[:100]}...")
                
                try:
                    message_json = json.loads(message_data)
                    user_message = message_json.get('content', '').strip()
                    
                    if user_message:
                        await websocket_manager.handle_user_message(session_id, user_message)
                    else:
                        logger.warning(f"⚠️ Mensaje vacío de sesión: {session_id}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Error JSON de sesión {session_id}: {str(e)}")
                    await websocket_manager.send_message(
                        session_id, 
                        "error", 
                        "Formato inválido. Usa: {\"content\": \"tu mensaje\"}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje de sesión {session_id}: {str(e)}")
                    await websocket_manager.send_message(
                        session_id, 
                        "error", 
                        f"Error procesando mensaje: {str(e)}"
                    )
        except Exception as e:
            # Re-raise para que sea manejado por el caller
            raise 