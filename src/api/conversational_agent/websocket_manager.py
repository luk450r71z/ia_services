from fastapi import WebSocket
from typing import Dict, Any
import logging
import json

from .models.schemas import WebSocketMessage
from .services.conversation_service import ConversationService, AgentManager

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Maneja conexiones WebSocket puras - delegando lógica de negocio a servicios"""
    
    def __init__(self):
        # Solo conexiones WebSocket activas
        self.active_connections: Dict[str, WebSocket] = {}
        # Delegación a AgentManager
        self.agent_manager = AgentManager()
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Acepta una nueva conexión WebSocket para una sesión específica
        """
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket
            logger.info(f"✅ WebSocket conectado para sesión: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error al conectar WebSocket para sesión {session_id}: {str(e)}")
            raise
    
    def disconnect(self, session_id: str):
        """
        Desconecta una sesión específica
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"🔌 WebSocket desconectado para sesión: {session_id}")
    
    async def send_message(self, session_id: str, message_type: str, content: str, data: Dict = None):
        """Envía un mensaje a una sesión específica"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            
            message = WebSocketMessage(
                type=message_type,
                content=content,
                session_id=session_id,
                data=data or {}
            )
            
            try:
                await websocket.send_text(message.model_dump_json())
                logger.debug(f"📤 Mensaje enviado a {session_id}: {message_type}")
            except Exception as e:
                logger.error(f"❌ Error enviando mensaje a {session_id}: {str(e)}")
                self.disconnect(session_id)
    
    async def handle_user_message(self, session_id: str, message: str):
        """Procesa un mensaje del usuario delegando a ConversationService"""
        try:
            # Asegurar que hay agente inicializado
            agent = self.agent_manager.get_agent(session_id)
            if not agent:
                await self.initialize_agent(session_id)
                agent = self.agent_manager.get_agent(session_id)
            
            if not agent:
                await self.send_message(session_id, "error", "No se pudo inicializar el agente conversacional")
                return
            
            # Delegar procesamiento a ConversationService
            result = await ConversationService.process_user_message(session_id, agent, message)
            
            # Enviar respuesta del agente
            await self.send_message(
                session_id, 
                "agent_response", 
                result["response"],
                {
                    "is_complete": result["is_complete"],
                    "summary": result["summary"]
                }
            )
            
            logger.info(f"✅ Respuesta del agente enviada para sesión {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje de usuario en sesión {session_id}: {str(e)}")
            await self.send_message(session_id, "error", f"Error interno: {str(e)}")
    
    async def initialize_agent(self, session_id: str, session_data: Dict = None):
        """Delega inicialización de agente a AgentManager"""
        return await self.agent_manager.initialize_agent(session_id, session_data)

    def get_welcome_message(self, session_id: str) -> str:
        """Delega mensaje de bienvenida a AgentManager"""
        return self.agent_manager.get_welcome_message(session_id)
    
    async def connect_and_initialize(self, websocket: WebSocket, session_id: str, session_data: Dict[str, Any] = None):
        """
        Conecta WebSocket e inicializa agente con mensaje de bienvenida
        """
        await self.connect(websocket, session_id)
        await self._initialize_agent_and_send_welcome(session_id, session_data or {})
    
    async def _initialize_agent_and_send_welcome(self, session_id: str, session_data: Dict[str, Any]):
        """
        Inicializa agente y envía mensaje de bienvenida (método privado)
        """
        try:
            agent_initialized = await self.initialize_agent(session_id, session_data)
            if agent_initialized:
                welcome_message = self.get_welcome_message(session_id)
                if welcome_message:
                    await self.send_message(
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
    
    async def handle_connection_lifecycle(self, websocket: WebSocket, session_id: str):
        """
        Maneja todo el ciclo de vida de la conexión WebSocket
        """
        try:
            while True:
                message_data = await websocket.receive_text()
                logger.debug(f"📨 Mensaje recibido de {session_id}: {message_data[:100]}...")
                
                try:
                    message_json = json.loads(message_data)
                    user_message = message_json.get('content', '').strip()
                    
                    if user_message:
                        await self.handle_user_message(session_id, user_message)
                    else:
                        logger.warning(f"⚠️ Mensaje vacío de sesión: {session_id}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Error JSON de sesión {session_id}: {str(e)}")
                    await self.send_message(
                        session_id, 
                        "error", 
                        "Formato inválido. Usa: {\"content\": \"tu mensaje\"}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje de sesión {session_id}: {str(e)}")
                    await self.send_message(
                        session_id, 
                        "error", 
                        f"Error procesando mensaje: {str(e)}"
                    )
        except Exception as e:
            # Desconectar automáticamente en caso de error
            self.disconnect(session_id)
            raise

# Instancia global del manager
websocket_manager = WebSocketManager() 