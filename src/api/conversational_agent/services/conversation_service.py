import logging
from typing import Dict, Any, Protocol, Optional

from .session_service import SessionService
from ..notifications import notification_manager

logger = logging.getLogger(__name__)

class ConversationalAgent(Protocol):
    """Protocolo que define la interfaz para agentes conversacionales"""
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

class ConversationManager:
    """Maneja toda la lógica conversacional: agentes, sesiones y procesamiento de mensajes"""
    
    def __init__(self):
        self.active_agents: Dict[str, ConversationalAgent] = {}
    
    async def initialize_conversation(self, session_id: str, session_data: Dict = None) -> Optional[str]:
        """
        Inicializa una conversación creando el agente y retornando mensaje de bienvenida
        
        Args:
            session_id: ID de la sesión
            session_data: Datos de la sesión (opcional)
            
        Returns:
            Mensaje de bienvenida o None si hay error
        """
        try:
            # Usar datos proporcionados o obtener de BD
            if not session_data:
                session_data = SessionService.get_session(session_id)
                
            if not session_data:
                logger.error(f"❌ No se encontró sesión en BD: {session_id}")
                return None
            
            # Crear agente
            agent = self._create_agent(session_data)
            if not agent:
                return None
            
            # Guardar agente y obtener mensaje de bienvenida
            self.active_agents[session_id] = agent
            welcome_message = agent.start_conversation()
            
            logger.info(f"🤖 Conversación inicializada para sesión: {session_id}")
            return welcome_message
            
        except Exception as e:
            logger.error(f"❌ Error inicializando conversación {session_id}: {str(e)}")
            return None
    
    async def process_user_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Procesa un mensaje del usuario y maneja toda la lógica conversacional
        
        Args:
            session_id: ID de la sesión
            message: Mensaje del usuario
            
        Returns:
            Dict con respuesta del agente y datos adicionales
        """
        try:
            logger.info(f"💬 Procesando mensaje de usuario en sesión {session_id}: {message[:50]}...")
            
            # Obtener agente
            agent = self.active_agents.get(session_id)
            if not agent:
                raise ValueError(f"No hay agente activo para sesión: {session_id}")
            
            # Procesar mensaje con el agente
            agent_response = agent.process_user_input(message)
            is_complete = agent.is_conversation_complete()
            
            # Si está completa, finalizar sesión
            summary = None
            if is_complete:
                summary = await self._complete_session(session_id, agent)
                self._remove_agent(session_id)
            
            return {
                "response": agent_response,
                "is_complete": is_complete,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje de usuario en sesión {session_id}: {str(e)}")
            raise
    
    def _create_agent(self, session_data: Dict) -> Optional[ConversationalAgent]:
        """
        Crea un agente basado en el tipo de sesión
        
        Args:
            session_data: Datos de la sesión
            
        Returns:
            Instancia del agente o None si hay error
        """
        agent_type = session_data.get('type')
        if not agent_type:
            logger.error(f"❌ No se especificó tipo de agente")
            return None
        
        if agent_type == "questionnarie":
            from ..agents.questionarie_rh import QuestionarieRHAgent
            
            content = session_data.get('content', {})
            questions_data = content.get('questions', [])
            
            if not questions_data:
                logger.warning(f"⚠️ No hay preguntas configuradas para sesión questionnarie")
                return None
            
            questions = QuestionarieRHAgent.extract_questions(questions_data)
            logger.info(f"🤖 Agente extrajo {len(questions)} preguntas del JSON")
            
            return QuestionarieRHAgent(questions=questions)
        else:
            logger.error(f"❌ Tipo de agente no soportado: {agent_type}")
            return None
    
    async def _complete_session(self, session_id: str, agent: ConversationalAgent) -> Optional[Dict[str, Any]]:
        """
        Finaliza una sesión actualizando estado y enviando notificaciones
        
        Args:
            session_id: ID de la sesión
            agent: Instancia del agente
            
        Returns:
            Resumen de la conversación o None si hay error
        """
        try:
            logger.info(f"📝 Finalizando sesión {session_id}...")
            
            # Obtener resumen de la conversación
            conversation_summary = agent.get_conversation_summary()
            
            # Actualizar sesión con resumen
            updated_session = SessionService.complete_session_with_summary(session_id, conversation_summary)
            
            if updated_session:
                logger.info(f"✅ Sesión finalizada: {session_id}")
                
                # Enviar notificaciones
                await self._send_notifications(session_id, updated_session, conversation_summary)
                return conversation_summary
            else:
                logger.warning(f"⚠️ No se pudo actualizar estado de sesión: {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finalizando sesión {session_id}: {str(e)}")
            return None
    
    async def _send_notifications(self, session_id: str, session_data: Dict, conversation_summary: Dict):
        """Envía notificaciones de finalización de sesión"""
        try:
            notification_results = await notification_manager.send_completion_notifications(
                session_id=session_id,
                session_data=session_data,
                conversation_summary=conversation_summary
            )
            
            if notification_results.get("emails_sent") or notification_results.get("webhook_sent"):
                logger.info(f"📬 Notificaciones enviadas para sesión {session_id}")
            
            if notification_results.get("errors"):
                logger.warning(f"⚠️ Errores en notificaciones: {notification_results['errors']}")
                
        except Exception as notification_error:
            logger.error(f"❌ Error enviando notificaciones: {str(notification_error)}")
    
    def _remove_agent(self, session_id: str):
        """Remueve un agente activo"""
        if session_id in self.active_agents:
            del self.active_agents[session_id]
            logger.info(f"🗑️ Agente removido para sesión: {session_id}")

# Instancia singleton para uso global
conversation_manager = ConversationManager() 