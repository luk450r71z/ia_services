from fastapi import WebSocket
from typing import Dict, Any
import logging
import json
from datetime import datetime

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
            logger.info(f"✅ WebSocket connected for session: {id_session}")
        except Exception as e:
            logger.error(f"❌ Error connecting WebSocket for session {id_session}: {str(e)}")
            raise
    
    async def disconnect(self, id_session: str):
        """Disconnects a WebSocket client"""
        if id_session in self.active_connections:
            await self.active_connections[id_session].close()
            del self.active_connections[id_session]
            logger.info(f"🔌 WebSocket disconnected for session: {id_session}")
    
    async def send_message(self, id_session: str, message_type: str, content: str = None, data: Dict = None):
        """Sends a message to a WebSocket client"""
        try:
            if id_session in self.active_connections:
                message = WebSocketMessage(
                    type=message_type,
                    content=content,
                    data=data,
                    timestamp=datetime.now()
                )
                await self.active_connections[id_session].send_text(message.json())
                logger.debug(f"📤 Message sent to {id_session}: {message_type}")
        except Exception as e:
            logger.error(f"❌ Error sending message to {id_session}: {str(e)}")
            raise
    
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

    async def process_agent_response(self, id_session: str, response: str):
        """Processes and sends an agent's response"""
        try:
            # Enviar respuesta al cliente
            await self.send_message(id_session, "agent_response", response)
            logger.info(f"✅ Agent response sent for session {id_session}")
            
        except Exception as e:
            logger.error(f"❌ Error processing user message in session {id_session}: {str(e)}")
            raise

    async def send_ui_config(self, id_session: str, config: Dict):
        """Sends UI configuration to the client"""
        try:
            await self.send_message(id_session, "ui_config", data=config)
            logger.info(f"✅ UI configuration sent to session {id_session}")
            
        except Exception as e:
            logger.error(f"❌ Error sending UI configuration to session {id_session}: {str(e)}")
            raise

    async def send_welcome_message(self, id_session: str):
        """Sends welcome message and initializes agent"""
        try:
            # Inicializar agente
            welcome_message = await conversation_manager.initialize_conversation(id_session)
            
            if welcome_message:
                await self.send_message(id_session, "welcome_message", welcome_message)
                logger.info(f"📨 Welcome message sent to session: {id_session}")
            else:
                logger.warning(f"⚠️ Could not initialize agent for session: {id_session}")
                
        except Exception as e:
            logger.error(f"❌ Error initializing agent: {str(e)}")
            raise

    async def handle_message(self, id_session: str, message_data: str):
        """Handles incoming WebSocket messages"""
        try:
            # Log mensaje recibido
            logger.debug(f"📨 Message received from {id_session}: {message_data[:100]}...")
            
            # Parsear mensaje
            try:
                message = WebSocketMessage.parse_raw(message_data)
            except Exception as e:
                logger.error(f"❌ JSON error from session {id_session}: {str(e)}")
                return
            
            # Validar mensaje
            if not message.content:
                logger.warning(f"⚠️ Empty message from session: {id_session}")
                return
            
            # Procesar mensaje
            response = await self.conversation_manager.process_user_message(id_session, message.content)
            
            # Enviar respuesta
            await self.process_agent_response(id_session, response["response"])
            
        except Exception as e:
            logger.error(f"❌ Error processing message from session {id_session}: {str(e)}")
            raise

# Instancia global del manager
websocket_manager = WebSocketManager() 