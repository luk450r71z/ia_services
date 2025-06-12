import logging
from typing import Dict, Any, Protocol, Optional

from .session_service import SessionService
from ..notifications import notification_manager

logger = logging.getLogger(__name__)

class ConversationalAgent(Protocol):
    """Protocolo que define la interfaz para agentes conversacionales"""
    def start_conversation(self, session_data: Dict = None) -> str:
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
    
    async def initialize_conversation(self, id_session: str, session_data: Dict = None) -> Optional[str]:
        """Inicializa una conversación creando el agente y retornando mensaje de bienvenida"""
        try:
            # Usar datos proporcionados o obtener de BD
            if not session_data:
                session_data = SessionService.get_session(id_session)
                
            if not session_data:
                logger.error(f"❌ No se encontró sesión en BD: {id_session}")
                return None
            
            # Crear agente
            agent = self._create_agent(session_data)
            if not agent:
                return None
            
            # Guardar agente y obtener mensaje de bienvenida
            self.active_agents[id_session] = agent
            welcome_message = agent.start_conversation()
            
            logger.info(f"🤖 Conversación inicializada para sesión: {id_session}")
            return welcome_message
            
        except Exception as e:
            logger.error(f"❌ Error inicializando conversación {id_session}: {str(e)}")
            return None
    
    async def process_user_message(self, id_session: str, message: str) -> Dict[str, Any]:
        """Procesa un mensaje del usuario y maneja toda la lógica conversacional"""
        try:
            logger.info(f"💬 Procesando mensaje de usuario en sesión {id_session}: {message[:50]}...")
            
            # Obtener agente
            agent = self.active_agents.get(id_session)
            if not agent:
                raise ValueError(f"No hay agente activo para sesión: {id_session}")
            
            # Procesar mensaje con el agente
            agent_response = agent.process_user_input(message)
            is_complete = agent.is_conversation_complete()
            
            # Si está completa, finalizar sesión
            summary = None
            if is_complete:
                summary = await self._complete_session(id_session, agent)
                self._remove_agent(id_session)
            
            return {
                "response": agent_response,
                "is_complete": is_complete,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje de usuario en sesión {id_session}: {str(e)}")
            raise
    
    def _create_agent(self, session_data: Dict) -> Optional[ConversationalAgent]:
        """Crea un agente basado en el tipo de sesión"""
        agent_type = session_data.get('type')
        if not agent_type:
            logger.error(f"❌ No se especificó tipo de agente")
            return None
        
        if agent_type == "questionnaire":
            from ..agents.questionnaire_rh import QuestionnaireRHAgent
            
            content = session_data.get('content', {})
            questions_data = content.get('questions', [])
            
            if not questions_data:
                logger.warning(f"⚠️ No hay preguntas configuradas para sesión questionnaire")
                return None
            
            logger.info(f"🤖 Creando agente con content completo (questions_data: {len(questions_data)} preguntas)")
            
            return QuestionnaireRHAgent(content=content)
        else:
            logger.error(f"❌ Tipo de agente no soportado: {agent_type}")
            return None
    
    async def _complete_session(self, id_session: str, agent: ConversationalAgent) -> Optional[Dict[str, Any]]:
        """Finaliza una sesión actualizando estado y enviando notificaciones"""
        try:
            logger.info(f"📝 Finalizando sesión {id_session}...")
            
            # Obtener resumen de la conversación
            conversation_summary = agent.get_conversation_summary()
            
            # Actualizar sesión con resumen
            updated_session = SessionService.complete_session_with_summary(id_session, conversation_summary)
            
            if updated_session:
                logger.info(f"✅ Sesión finalizada: {id_session}")
                
                # Enviar notificaciones
                try:
                    notification_results = await notification_manager.send_completion_notifications(
                        id_session=id_session,
                        session_data=updated_session,
                        conversation_summary=conversation_summary
                    )
                    
                    if notification_results.get("emails_sent") or notification_results.get("webhook_sent"):
                        logger.info(f"📬 Notificaciones enviadas para sesión {id_session}")
                    
                    if notification_results.get("errors"):
                        logger.warning(f"⚠️ Errores en notificaciones: {notification_results['errors']}")
                        
                except Exception as notification_error:
                    logger.error(f"❌ Error enviando notificaciones: {str(notification_error)}")
                
                return conversation_summary
            else:
                logger.warning(f"⚠️ No se pudo actualizar estado de sesión: {id_session}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finalizando sesión {id_session}: {str(e)}")
            return None
    
    def _remove_agent(self, id_session: str):
        """Remueve un agente activo"""
        if id_session in self.active_agents:
            del self.active_agents[id_session]
            logger.info(f"🗑️ Agente removido para sesión: {id_session}")

# Instancia singleton para uso global
conversation_manager = ConversationManager() 