from fastapi import WebSocket
from typing import Dict
import logging

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
    
    def register_agent_factory(self, agent_type: str, factory_func: callable):
        """Delegación a AgentManager"""
        self.agent_manager.register_agent_factory(agent_type, factory_func)
    
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

# Instancia global del manager
websocket_manager = WebSocketManager() 