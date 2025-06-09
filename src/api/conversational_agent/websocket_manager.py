from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, Protocol, Type
import json
import logging
from datetime import datetime

from auth.db.sqlite_db import get_session_db, update_session_db, save_conversation_response
from .models.schemas import WebSocketMessage

logger = logging.getLogger(__name__)

class ConversationalAgent(Protocol):
    """
    Protocolo que define la interfaz que debe implementar cualquier agente conversacional
    """
    def start_conversation(self) -> str:
        """Inicia la conversación y retorna el mensaje de bienvenida"""
        ...
    
    def process_user_input(self, user_input: str) -> str:
        """Procesa el input del usuario y retorna la respuesta del agente"""
        ...
    
    def is_conversation_complete(self) -> bool:
        """Verifica si la conversación ha terminado"""
        ...
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de la conversación"""
        ...

class WebSocketManager:
    """
    Maneja las conexiones WebSocket y la comunicación con agentes conversacionales genéricos
    """
    
    def __init__(self):
        # Diccionario para almacenar conexiones activas: {session_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Diccionario para almacenar agentes activos: {session_id: agent}
        self.active_agents: Dict[str, ConversationalAgent] = {}
        # Registro de factorías de agentes por tipo
        self._agent_factories: Dict[str, callable] = {}
    
    def register_agent_factory(self, agent_type: str, factory_func: callable):
        """
        Registra una factoría para crear agentes de un tipo específico
        
        Args:
            agent_type: Tipo de agente (ej: "questionnarie", "support", "sales")
            factory_func: Función que crea y retorna una instancia del agente
        """
        self._agent_factories[agent_type] = factory_func
        logger.info(f"🏭 Factoría registrada para agente tipo: {agent_type}")
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Acepta una nueva conexión WebSocket para una sesión específica
        """
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket
            logger.info(f"✅ WebSocket conectado para sesión: {session_id}")
            
            # Inicializar agente si no existe y enviar mensaje de bienvenida
            if session_id not in self.active_agents:
                await self.initialize_agent(session_id)
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
                await self.initialize_agent(session_id)
            
            if session_id not in self.active_agents:
                await self.send_message(session_id, "error", "No se pudo inicializar el agente conversacional")
                return
            
            agent = self.active_agents[session_id]
            
            # Procesar mensaje con el agente
            agent_response = agent.process_user_input(message)
            
            # Guardar respuesta si el agente lo soporta (específico para ciertos tipos)
            await self._save_response_if_supported(session_id, agent, message)
            
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
        Inicializa un agente conversacional basado en el tipo de sesión
        
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
            
            # Obtener tipo de agente de la sesión
            agent_type = session_data.get('type')
            if not agent_type:
                logger.error(f"❌ No se especificó tipo de agente para sesión: {session_id}")
                return False
            
            # Verificar que existe una factoría para este tipo
            if agent_type not in self._agent_factories:
                logger.error(f"❌ No hay factoría registrada para tipo de agente: {agent_type}")
                return False
            
            # Crear agente usando la factoría correspondiente
            factory_func = self._agent_factories[agent_type]
            agent = factory_func(session_data)
            
            if agent:
                self.active_agents[session_id] = agent
                logger.info(f"🤖 Agente tipo '{agent_type}' inicializado para sesión {session_id}")
                return True
            else:
                logger.error(f"❌ La factoría no pudo crear agente para sesión: {session_id}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error inicializando agente para sesión {session_id}: {str(e)}")
            return False

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
                welcome_message = self.active_agents[session_id].start_conversation()
                logger.info(f"🤖 Mensaje de bienvenida obtenido para sesión: {session_id}")
                return welcome_message
            except Exception as e:
                logger.error(f"❌ Error obteniendo mensaje de bienvenida para sesión {session_id}: {str(e)}")
                return None
        else:
            logger.warning(f"⚠️ No hay agente inicializado para sesión: {session_id}")
            return None
    
    async def _save_response_if_supported(self, session_id: str, agent: ConversationalAgent, message: str):
        """
        Guarda la respuesta si el agente soporta el tracking específico (como questionnarie)
        """
        try:
            # Verificar si el agente tiene estado específico de questionnarie
            if hasattr(agent, 'state') and hasattr(agent.state, 'current_question'):
                current_question = agent.state.current_question
                current_question_index = getattr(agent.state, 'current_question_index', 0)
                needs_clarification = getattr(agent.state, 'needs_clarification', False)
                
                # Solo guardar si había una pregunta activa y la respuesta fue aceptada
                if current_question and not needs_clarification:
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
    
    async def _update_session_to_complete(self, session_id: str, agent: ConversationalAgent):
        """
        Actualiza el estado de la sesión a 'complete' en la base de datos.
        
        Args:
            session_id: ID de la sesión
            agent: Instancia del agente con los datos de la conversación
        """
        try:
            logger.info(f"📝 Actualizando estado de la sesión {session_id} a 'complete'...")
            
            # Obtener sesión actual para mantener el tipo
            session_data = get_session_db(session_id)
            if not session_data:
                logger.error(f"❌ No se pudo obtener datos de sesión: {session_id}")
                return
            
            agent_type = session_data.get('type', 'unknown')
            
            # Obtener resumen de la conversación del agente
            conversation_summary = agent.get_conversation_summary()
            
            # Obtener content original de la sesión
            original_content = session_data.get('content', {})
            
            # Crear content actualizado con el resumen 
            final_content = original_content.copy()
            final_content["summary"] = conversation_summary
            
            # Actualizar el estado en la base de datos
            updated_session = update_session_db(
                session_id=session_id,
                type_value=agent_type,
                status="complete",
                content=final_content,
                configs={}
            )
            
            if updated_session:
                logger.info(f"✅ Estado de sesión actualizado a 'complete': {session_id}")
            else:
                logger.warning(f"⚠️ No se pudo actualizar el estado de la sesión: {session_id}")
                
        except Exception as e:
            logger.error(f"❌ Error al actualizar estado de sesión {session_id}: {str(e)}")

# Instancia global del manager
websocket_manager = WebSocketManager() 