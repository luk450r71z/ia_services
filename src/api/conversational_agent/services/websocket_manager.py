from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any
import logging
import json
from datetime import datetime, timezone

from ..models.schemas import WebSocketMessage, WebSocketMessageType
from .conversation_manager import conversation_manager
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Maneja conexiones WebSocket puras - delegando lógica de negocio a servicios"""
    
    def __init__(self):
        # Solo conexiones WebSocket activas
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, id_session: str):
        """Acepta una nueva conexión WebSocket para una sesión específica"""
        try:
            if id_session in self.active_connections:
                logger.warning(f"⚠️ Sesión {id_session} ya tiene una conexión activa. Cerrando conexión anterior...")
                await self.disconnect(id_session)
                
            await websocket.accept()
            self.active_connections[id_session] = websocket
            logger.info(f"✅ Nueva conexión WebSocket establecida para sesión: {id_session}")
        except Exception as e:
            logger.error(f"❌ Error conectando WebSocket para sesión {id_session}: {str(e)}")
            raise
    
    async def disconnect(self, id_session: str):
        """Disconnects a WebSocket client"""
        try:
            if id_session in self.active_connections:
                await self.active_connections[id_session].close()
                del self.active_connections[id_session]
                logger.info(f"✅ Conexión WebSocket cerrada para sesión: {id_session}")
        except Exception as e:
            logger.error(f"❌ Error cerrando conexión WebSocket para sesión {id_session}: {str(e)}")
            # Intentar limpiar la conexión incluso si hay error
            if id_session in self.active_connections:
                del self.active_connections[id_session]
    
    async def send_message(self, id_session: str, message_type: str, content: str = None, data: Dict = None):
        """Sends a message to a WebSocket client"""
        try:
            if id_session in self.active_connections:
                message = WebSocketMessage(
                    type=WebSocketMessageType(message_type),
                    content=content,
                    data=data,
                    timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                )
                await self.active_connections[id_session].send_text(message.json())
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
                    "summary": result["summary"],
                    "answerType": result.get("answerType"),
                    "options": result.get("options")
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje de usuario en sesión {id_session}: {str(e)}")
            await self.send_message(id_session, "error", f"Error interno: {str(e)}")

    async def connect_and_initialize(self, websocket: WebSocket, id_session: str, session_data: Dict[str, Any] = None):
        """Conecta WebSocket, envía configuración UI e inicializa agente con mensaje de bienvenida"""
        try:
            await self.connect(websocket, id_session)
            
            # Enviar configuración de UI al frontend
            configs = session_data.get('configs', {}) if session_data else {}
            await self.send_message(
                id_session,
                "ui_config",
                data={
                    "avatar": configs.get('avatar', False),
                    "configs": configs
                }
            )
            
            # Inicializar agente - ahora siempre retorna el objeto agente
            agent = await conversation_manager.initialize_conversation(id_session, session_data)
            if agent:
                # Enviar historial de mensajes (incluyendo el de bienvenida)
                for message in agent.state.messages:
                    if hasattr(message, 'content'):
                        if isinstance(message, AIMessage):
                            await self.send_message(
                                id_session,
                                "agent_response",
                                message.content
                            )
                        elif isinstance(message, HumanMessage):
                            await self.send_message(
                                id_session,
                                "user_message",
                                message.content
                            )
                
                # Enviar el estado actual con answerType y options si la conversación no está completa
                if not agent.is_conversation_complete():
                    # Obtener answerType y options de la pregunta actual
                    answerType = None
                    options = None
                    if hasattr(agent, 'state') and hasattr(agent.state, 'current_question_index'):
                        # Obtener datos de sesión para acceder al contenido original
                        if session_data and session_data.get('content'):
                            questions = session_data['content'].get('questions', [])
                            current_index = agent.state.current_question_index
                            if current_index < len(questions):
                                current_question = questions[current_index]
                                answerType = current_question.get("answerType")
                                options = current_question.get("options")
                    
                    # Si hay opciones actuales, enviar un mensaje de estado actual
                    if answerType and options:
                        await self.send_message(
                            id_session,
                            "agent_response",
                            "Please continue with your selection:",
                            {
                                "is_current_state": True,
                                "answerType": answerType,
                                "options": options
                            }
                        )
            else:
                logger.warning(f"⚠️ No se pudo inicializar agente para sesión: {id_session}")
        except Exception as e:
            logger.error(f"❌ Error en inicialización: {str(e)}")
            await self.disconnect(id_session)
            raise

    async def handle_connection_lifecycle(self, websocket: WebSocket, id_session: str):
        """Maneja todo el ciclo de vida de la conexión WebSocket"""
        try:
            while True:
                try:
                    message_data = await websocket.receive_text()
                    
                    if not message_data:
                        logger.warning(f"⚠️ Mensaje vacío recibido de sesión: {id_session}")
                        continue
                        
                    try:
                        message_json = json.loads(message_data)
                        user_message = message_json.get('content', '').strip()
                        
                        if not user_message:
                            logger.warning(f"⚠️ Mensaje sin contenido de sesión: {id_session}")
                            continue
                            
                        await self.handle_user_message(id_session, user_message)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Error JSON de sesión {id_session}: {str(e)}")
                        await self.send_message(
                            id_session, 
                            "error", 
                            "Formato inválido. Usa: {\"content\": \"tu mensaje\"}"
                        )
                        
                except WebSocketDisconnect:
                    logger.info(f"📡 Cliente desconectado: {id_session}")
                    break
                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje de sesión {id_session}: {str(e)}")
                    await self.send_message(
                        id_session, 
                        "error", 
                        f"Error procesando mensaje: {str(e)}"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error fatal en ciclo de vida WebSocket {id_session}: {str(e)}")
        finally:
            await self.disconnect(id_session)

# Instancia global del manager
websocket_manager = WebSocketManager() 