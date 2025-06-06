from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging
from datetime import datetime

from .agents.questionarie_rh import QuestionarieRHAgent
from auth.db.sqlite_db import get_session_db, update_session_db, save_conversation_response
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
        self.active_agents: Dict[str, QuestionarieRHAgent] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Acepta una nueva conexión WebSocket para una sesión específica
        """
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket
            logger.info(f"✅ WebSocket conectado para sesión: {session_id}")
            
            # Inicializar agente si no existe
            agent_already_existed = session_id in self.active_agents
            if not agent_already_existed:
                await self._initialize_agent(session_id)
            
            # Enviar mensaje de bienvenida solo si el agente no existía previamente
            # (Si ya existía, significa que se inició desde start_questionnarie)
            if session_id in self.active_agents and not agent_already_existed:
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
            
            # Guardar información antes de procesar (para capturar pregunta actual)
            agent = self.active_agents[session_id]
            current_question = agent.state.current_question
            current_question_index = agent.state.current_question_index
            
            # Procesar mensaje con el agente
            agent_response = agent.process_user_input(message)
            
            # Solo guardar si había una pregunta activa y la respuesta fue aceptada
            # (es decir, si no necesita clarificación)
            if current_question and not agent.state.needs_clarification:
                # Guardar la respuesta en la base de datos
                try:
                    success = save_conversation_response(
                        session_id=session_id,
                        id_question=current_question_index,
                        question=current_question,
                        response=message
                    )
                    if success:
                        logger.info(f"💾 Respuesta guardada en BD para sesión {session_id}, pregunta {current_question_index}")
                    else:
                        logger.warning(f"⚠️ No se pudo guardar respuesta en BD para sesión {session_id}")
                except Exception as e:
                    logger.error(f"❌ Error guardando respuesta en BD: {str(e)}")
            
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
    
    async def initialize_agent(self, session_id: str, session_data: Dict = None):
        """
        Inicializa un agente conversacional para la sesión (método público)
        
        Args:
            session_id: ID de la sesión
            session_data: Datos de la sesión (opcional, si no se provee se obtiene de BD)
        """
        try:
            # Usar datos proporcionados o obtener de BD
            if not session_data:
                session_data = get_session_db(session_id)
                
            if not session_data:
                logger.error(f"❌ No se encontró sesión en BD: {session_id}")
                return False
            
            # Extraer preguntas del content
            content = session_data.get('content', {})
            questions = content.get('questions', [])
            
            if not questions:
                logger.warning(f"⚠️ No hay preguntas configuradas para sesión: {session_id}")
                return False
            
            # Crear agente con las preguntas específicas
            agent = QuestionarieRHAgent(questions=questions)
            self.active_agents[session_id] = agent
            
            logger.info(f"🤖 Agente inicializado para sesión {session_id} con {len(questions)} preguntas")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando agente para sesión {session_id}: {str(e)}")
            return False

    async def _initialize_agent(self, session_id: str):
        """
        Inicializa un agente conversacional para la sesión (método privado - wrapper del público)
        """
        await self.initialize_agent(session_id)

    def get_welcome_message(self, session_id: str) -> str:
        """
        Obtiene el mensaje de bienvenida del agente sin necesidad de WebSocket
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            str: Mensaje de bienvenida del agente o None si no hay agente
        """
        if session_id in self.active_agents:
            try:
                # Usar directamente start_conversation() del agente
                welcome_message = self.active_agents[session_id].start_conversation()
                logger.info(f"🤖 Mensaje de bienvenida obtenido para sesión: {session_id}")
                return welcome_message
            except Exception as e:
                logger.error(f"❌ Error obteniendo mensaje de bienvenida para sesión {session_id}: {str(e)}")
                return None
        else:
            logger.warning(f"⚠️ No hay agente inicializado para sesión: {session_id}")
            return None
    
    async def _update_session_to_complete(self, session_id: str, agent: QuestionarieRHAgent):
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
            
            # Crear content actualizado con el resumen
            final_content = {
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
                type_value="questionnarie",  # Mantener el tipo original
                status="complete",  # Cambiar estado a complete
                content=final_content,
                configs={}  # Configs vacío por ahora
            )
            
            if updated_session:
                logger.info(f"✅ Estado de sesión actualizado a 'complete': {session_id}")
            else:
                logger.warning(f"⚠️ No se pudo actualizar el estado de la sesión: {session_id}")
                
        except Exception as e:
            logger.error(f"❌ Error al actualizar estado de sesión {session_id}: {str(e)}")

# Instancia global del manager
websocket_manager = WebSocketManager() 