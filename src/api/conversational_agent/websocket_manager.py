from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging
from datetime import datetime

from .agents.simple_agent import SimpleRRHHAgent
from auth.db.sqlite_db import get_session_db, update_session_db
from .models.schemas import WebSocketMessage

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Maneja las conexiones WebSocket y la comunicación con los agentes conversacionales
    """
    
    def __init__(self):
        # Diccionario para almacenar conexiones activas: {session_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Diccionario para almacenar agentes activos: {session_id: agent}
        self.active_agents: Dict[str, SimpleRRHHAgent] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Acepta una nueva conexión WebSocket para una sesión específica
        """
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket
            logger.info(f"✅ WebSocket conectado para sesión: {session_id}")
            
            # Inicializar agente si no existe
            if session_id not in self.active_agents:
                await self._initialize_agent(session_id)
            
            # Enviar mensaje de bienvenida
            if session_id in self.active_agents:
                welcome_message = self.active_agents[session_id].start_conversation()
                await self.send_message(session_id, "agent_response", welcome_message)
            
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
        
        # Mantener el agente por si se reconecta
        # if session_id in self.active_agents:
        #     del self.active_agents[session_id]
    
    async def send_message(self, session_id: str, message_type: str, content: str, data: Dict = None):
        """
        Envía un mensaje a una sesión específica
        """
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
                # Limpiar conexión inválida
                self.disconnect(session_id)
    
    async def handle_user_message(self, session_id: str, message: str):
        """
        Procesa un mensaje del usuario y genera la respuesta del agente
        """
        try:
            logger.info(f"💬 Procesando mensaje de usuario en sesión {session_id}: {message[:50]}...")
            
            if session_id not in self.active_agents:
                await self._initialize_agent(session_id)
            
            if session_id not in self.active_agents:
                await self.send_message(session_id, "error", "No se pudo inicializar el agente conversacional")
                return
            
            # Procesar mensaje con el agente
            agent = self.active_agents[session_id]
            agent_response = agent.process_user_input(message)
            
            # Verificar si la conversación se completó
            is_complete = agent.is_conversation_complete()
            
            # Si la conversación está completa, actualizar estado en la base de datos
            if is_complete:
                await self._update_session_to_complete(session_id, agent)
            
            # Enviar respuesta del agente
            await self.send_message(
                session_id, 
                "agent_response", 
                agent_response,
                {
                    "is_complete": is_complete,
                    "summary": agent.get_conversation_summary() if is_complete else None
                }
            )
            
            logger.info(f"✅ Respuesta del agente enviada para sesión {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje de usuario en sesión {session_id}: {str(e)}")
            await self.send_message(session_id, "error", f"Error interno: {str(e)}")
    
    async def _initialize_agent(self, session_id: str):
        """
        Inicializa un agente conversacional para la sesión
        """
        try:
            # Obtener datos de la sesión desde la base de datos
            session_data = get_session_db(session_id)
            
            if not session_data:
                logger.error(f"❌ No se encontró sesión en BD: {session_id}")
                return
            
            # Extraer preguntas del metadata
            metadata = session_data.get('metadata', {})
            questions = metadata.get('questions', [])
            
            if not questions:
                logger.warning(f"⚠️ No hay preguntas configuradas para sesión: {session_id}")
                # Usar preguntas por defecto si están disponibles
                questions = []
            
            # Crear agente con las preguntas específicas
            agent = SimpleRRHHAgent(questions=questions)
            self.active_agents[session_id] = agent
            
            logger.info(f"🤖 Agente inicializado para sesión {session_id} con {len(questions)} preguntas")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando agente para sesión {session_id}: {str(e)}")
    
    async def _update_session_to_complete(self, session_id: str, agent: SimpleRRHHAgent):
        """
        Actualiza el estado de la sesión a 'complete' en la base de datos.
        
        Args:
            session_id: ID de la sesión
            agent: Instancia del agente con los datos de la conversación
        """
        try:
            logger.info(f"📝 Actualizando estado de la sesión {session_id} a 'complete'...")
            
            # Obtener resumen de la conversación del agente
            conversation_summary = agent.get_conversation_summary()
            
            # Crear metadata actualizado con el resumen
            final_metadata = {
                "questions": agent.questions,
                "responses": conversation_summary.get("responses", {}),
                "completed_at": datetime.utcnow().isoformat(),
                "total_questions": conversation_summary.get("total_questions", 0),
                "total_responses": conversation_summary.get("questions_asked", 0),
                "messages_count": conversation_summary.get("messages_count", 0)
            }
            
            # Actualizar el estado en la base de datos
            updated_session = update_session_db(
                session_id=session_id,
                type_value="questionary",  # Mantener el tipo original
                state="complete",  # Cambiar estado a complete
                metadata=final_metadata
            )
            
            if updated_session:
                logger.info(f"✅ Estado de sesión actualizado a 'complete': {session_id}")
            else:
                logger.warning(f"⚠️ No se pudo actualizar el estado de la sesión: {session_id}")
                
        except Exception as e:
            logger.error(f"❌ Error al actualizar estado de sesión {session_id}: {str(e)}")

# Instancia global del manager
websocket_manager = WebSocketManager() 