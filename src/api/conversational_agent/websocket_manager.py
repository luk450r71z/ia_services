from fastapi import WebSocket
from typing import Dict, Any
import logging
import json

from .models.schemas import WebSocketMessage
from .services.conversation_service import conversation_manager

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Maneja conexiones WebSocket puras - delegando lógica de negocio a servicios"""
    
    def __init__(self):
        # Solo conexiones WebSocket activas
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, id_session: str):
        """Acepta una nueva conexión WebSocket para una sesión específica"""
        try:
            await websocket.accept()
            self.active_connections[id_session] = websocket
            logger.info(f"✅ WebSocket conectado para sesión: {id_session}")
        except Exception as e:
            logger.error(f"❌ Error al conectar WebSocket para sesión {id_session}: {str(e)}")
            raise
    
    def disconnect(self, id_session: str):
        """Desconecta una sesión específica"""
        if id_session in self.active_connections:
            del self.active_connections[id_session]
            logger.info(f"🔌 WebSocket desconectado para sesión: {id_session}")
    
    async def send_message(self, id_session: str, message_type: str, content: str, data: Dict = None):
        """Envía un mensaje a una sesión específica"""
        if id_session in self.active_connections:
            websocket = self.active_connections[id_session]
            
            message = WebSocketMessage(
                type=message_type,
                content=content,
                id_session=id_session,
                data=data or {}
            )
            
            try:
                await websocket.send_text(message.model_dump_json())
                logger.debug(f"📤 Mensaje enviado a {id_session}: {message_type}")
            except Exception as e:
                logger.error(f"❌ Error enviando mensaje a {id_session}: {str(e)}")
                self.disconnect(id_session)
    
    async def handle_user_message(self, id_session: str, message: str):
        """Procesa un mensaje del usuario delegando a conversation_manager"""
        try:
            # Delegar procesamiento a conversation_manager
            result = await conversation_manager.process_user_message(id_session, message)
            
            # Enviar respuesta del agente
            await self.send_message(
                id_session, 
                "agent_response", 
                result["response"],
                {
                    "is_complete": result["is_complete"],
                    "summary": result["summary"]
                }
            )
            
            logger.info(f"✅ Respuesta del agente enviada para sesión {id_session}")
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje de usuario en sesión {id_session}: {str(e)}")
            await self.send_message(id_session, "error", f"Error interno: {str(e)}")

    async def connect_and_initialize(self, websocket: WebSocket, id_session: str, session_data: Dict[str, Any] = None):
        """Conecta WebSocket, envía configuración UI e inicializa agente con mensaje de bienvenida"""
        await self.connect(websocket, id_session)
        
        # Enviar configuración de UI al frontend
        try:
            configs = session_data.get('configs', {}) if session_data else {}
            await self.send_message(
                id_session,
                "ui_config",
                "",
                {
                    "avatar": configs.get('avatar', False),
                    "configs": configs
                }
            )
            logger.info(f"✅ Configuración de UI enviada a sesión {id_session}")
        except Exception as e:
            logger.error(f"❌ Error enviando configuración UI a sesión {id_session}: {str(e)}")
        
        # Inicializar agente y enviar mensaje de bienvenida
        try:
            welcome_message = await conversation_manager.initialize_conversation(id_session, session_data)
            if welcome_message:
                await self.send_message(
                    id_session,
                    "agent_response", 
                    welcome_message,
                    {"is_welcome": True}
                )
                logger.info(f"📨 Mensaje de bienvenida enviado a sesión: {id_session}")
            else:
                logger.warning(f"⚠️ No se pudo inicializar agente para sesión: {id_session}")
        except Exception as e:
            logger.error(f"❌ Error inicializando agente: {str(e)}")
    
    async def handle_connection_lifecycle(self, websocket: WebSocket, id_session: str):
        """Maneja todo el ciclo de vida de la conexión WebSocket"""
        try:
            while True:
                message_data = await websocket.receive_text()
                logger.debug(f"📨 Mensaje recibido de {id_session}: {message_data[:100]}...")
                
                try:
                    message_json = json.loads(message_data)
                    user_message = message_json.get('content', '').strip()
                    
                    if user_message:
                        await self.handle_user_message(id_session, user_message)
                    else:
                        logger.warning(f"⚠️ Mensaje vacío de sesión: {id_session}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Error JSON de sesión {id_session}: {str(e)}")
                    await self.send_message(
                        id_session, 
                        "error", 
                        "Formato inválido. Usa: {\"content\": \"tu mensaje\"}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje de sesión {id_session}: {str(e)}")
                    await self.send_message(
                        id_session, 
                        "error", 
                        f"Error procesando mensaje: {str(e)}"
                    )
        except Exception as e:
            # Desconectar automáticamente en caso de error
            self.disconnect(id_session)
            raise

# Instancia global del manager
websocket_manager = WebSocketManager() 