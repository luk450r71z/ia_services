import logging
from typing import Dict, Any, Optional

from .session_service import SessionService
from .log_service import log_service
from .notification_service import notification_service
from ..models.log_models import LogStatus
from ..models.agent_protocol import ConversationalAgent
from auth.db.sqlite_db import get_session_db

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages all conversational logic: agents, sessions and message processing"""
    
    def __init__(self):
        self.active_agents: Dict[str, ConversationalAgent] = {}
    
    async def initialize_conversation(self, id_session: str, session_data: Dict = None) -> Optional[ConversationalAgent]:
        """Initializes a conversation by creating the agent and returning the agent object"""
        try:
            # Obtener datos de sesión
            session_data = get_session_db(id_session)
            
            if not session_data:
                logger.error(f"❌ Session not found in DB: {id_session}")
                return None
            
            # Si ya existe un agente activo, retornarlo
            if id_session in self.active_agents:
                logger.info(f"✅ Recuperando agente existente para sesión: {id_session}")
                return self.active_agents[id_session]
            
            # Create agent
            agent = self._create_agent(session_data)
            if not agent:
                return None
             
            # Save agent and get welcome message
            self.active_agents[id_session] = agent
            welcome_message = agent.start_conversation()
            
            # Log welcome message
            try:
                await log_service.log_message(
                    id_session=id_session,
                    message_type="agent",
                    content=welcome_message,
                    status=LogStatus.ANSWERED,
                    metadata={"is_welcome": True}
                )
            except Exception as e:
                logger.error(f"Error logging welcome message: {str(e)}")
            
            return agent
            
        except Exception as e:
            logger.error(f"❌ Error initializing conversation {id_session}: {str(e)}")
            return None
    
    async def process_user_message(self, id_session: str, message: str) -> Dict[str, Any]:
        """Processes a user message and handles all conversational logic"""
        try:
            # Log user message
            await log_service.log_message(
                id_session=id_session,
                message_type="user",
                content=message,
                status=LogStatus.ANSWERED
            )
            
            # Get agent
            agent = self.active_agents.get(id_session)
            if not agent:
                raise ValueError(f"No active agent for session: {id_session}")
            
            # Process message with agent
            agent_response = agent.process_user_input(message)
            is_complete = agent.is_conversation_complete()
            
            # Obtener answerType y options de la pregunta actual
            answerType = None
            options = None
            if not is_complete and hasattr(agent, 'state') and hasattr(agent.state, 'current_question_index'):
                # Obtener datos de sesión para acceder al contenido original
                session_data = get_session_db(id_session)
                if session_data and session_data.get('content'):
                    questions = session_data['content'].get('questions', [])
                    current_index = agent.state.current_question_index
                    if current_index < len(questions):
                        current_question = questions[current_index]
                        answerType = current_question.get("answerType")
                        options = current_question.get("options")
            
            # Log agent response
            await log_service.log_message(
                id_session=id_session,
                message_type="agent",
                content=agent_response,
                status=LogStatus.ANSWERED,
                metadata={"is_complete": is_complete}
            )
            
            # If complete, finalize session
            summary = None
            if is_complete:
                summary = await self._complete_session(id_session, agent)
                self._remove_agent(id_session)
            
            return {
                "response": agent_response,
                "is_complete": is_complete,
                "summary": summary,
                "answerType": answerType,
                "options": options
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing user message in session {id_session}: {str(e)}")
            # Log error
            await log_service.log_message(
                id_session=id_session,
                message_type="system",
                content=f"Error: {str(e)}",
                status=LogStatus.SKIPPED,
                metadata={"error": str(e)}
            )
            raise
    
    def _create_agent(self, session_data: Dict) -> Optional[ConversationalAgent]:
        """Crea un agente basado en el tipo de sesión"""
        agent_type = session_data.get('type')
        if not agent_type:
            logger.error(f"❌ No se especificó tipo de agente")
            return None
        
        if agent_type == "questionnaire":
            from ..agents.questionnaire import QuestionnaireAgent
            
            content = session_data.get('content', {})
            questions_data = content.get('questions', [])
            
            if not questions_data:
                logger.warning(f"⚠️ No hay preguntas configuradas para sesión questionnaire")
                return None
            
            logger.info(f"🤖 Creando agente con content completo (questions_data: {len(questions_data)} preguntas)")
            
            return QuestionnaireAgent(content=content)
        else:
            logger.error(f"❌ Tipo de agente no soportado: {agent_type}")
            return None
    
    async def _complete_session(self, id_session: str, agent: ConversationalAgent) -> Optional[Dict[str, Any]]:
        """Finalizes a session by updating state and sending notifications"""
        try:
            logger.info(f"📝 Finalizing session {id_session}...")
            
            # Get conversation summary
            conversation_summary = agent.get_conversation_summary()
            
            # Update session with summary
            updated_session = SessionService.complete_session_with_summary(id_session, conversation_summary)
            
            if updated_session:
                # Verificar configuración de notificaciones
                configs = updated_session.get('configs', {})
                emails = configs.get('emails', [])
                if emails:
                    logger.info(f"📧 Found {len(emails)} email recipients in config")
                    # Send notifications
                    try:
                        notification_results = await notification_service.send_completion_notifications(
                            id_session=id_session,
                            emails=emails,
                            conversation_summary=conversation_summary
                        )
                        
                        if notification_results.get("emails_sent"):
                            logger.info(f"📬 Notifications sent for session {id_session}")
                        
                        if notification_results.get("errors"):
                            logger.warning(f"⚠️ Notification errors: {notification_results['errors']}")
                            
                    except Exception as notification_error:
                        logger.error(f"❌ Error sending notifications: {str(notification_error)}")
                else:
                    logger.info(f"📭 No email recipients configured in config")
                
                return conversation_summary
            else:
                logger.warning(f"⚠️ Could not update session state: {id_session}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finalizing session {id_session}: {str(e)}")
            return None
    
    def _remove_agent(self, id_session: str):
        """Remueve un agente activo"""
        if id_session in self.active_agents:
            del self.active_agents[id_session]
            logger.info(f"🗑️ Agente removido para sesión: {id_session}")

# Instancia singleton para uso global
conversation_manager = ConversationManager() 