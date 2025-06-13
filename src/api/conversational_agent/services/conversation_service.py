import logging
from typing import Dict, Any, Protocol, Optional

from .session_service import SessionService
from ..notifications import notification_manager

logger = logging.getLogger(__name__)

class ConversationalAgent(Protocol):
    """Protocol that defines the interface for conversational agents"""
    def start_conversation(self, session_data: Dict = None) -> str:
        """Starts the conversation and returns the welcome message"""
        ...
    
    def process_user_input(self, user_input: str) -> str:
        """Processes user input and returns the agent's response"""
        ...
    
    def is_conversation_complete(self) -> bool:
        """Checks if the conversation has ended"""
        ...
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Gets a summary of the conversation"""
        ...

class ConversationManager:
    """Manages all conversational logic: agents, sessions and message processing"""
    
    def __init__(self):
        self.active_agents: Dict[str, ConversationalAgent] = {}
    
    async def initialize_conversation(self, id_session: str, session_data: Dict = None) -> Optional[str]:
        """Initializes a conversation by creating the agent and returning the welcome message"""
        try:
            # Use provided data or get from DB
            if not session_data:
                session_data = SessionService.get_session(id_session)
                
            if not session_data:
                logger.error(f"❌ Session not found in DB: {id_session}")
                return None
            
            # Create agent
            agent = self._create_agent(session_data)
            if not agent:
                return None
             
            # Save agent and get welcome message
            self.active_agents[id_session] = agent
            welcome_message = agent.start_conversation()
            
            logger.info(f"🤖 Conversation initialized for session: {id_session}")
            return welcome_message
            
        except Exception as e:
            logger.error(f"❌ Error initializing conversation {id_session}: {str(e)}")
            return None
    
    async def process_user_message(self, id_session: str, message: str) -> Dict[str, Any]:
        """Processes a user message and handles all conversational logic"""
        try:
            logger.info(f"💬 Processing user message in session {id_session}: {message[:50]}...")
            
            # Get agent
            agent = self.active_agents.get(id_session)
            if not agent:
                raise ValueError(f"No active agent for session: {id_session}")
            
            # Process message with agent
            agent_response = agent.process_user_input(message)
            is_complete = agent.is_conversation_complete()
            
            # If complete, finalize session
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
            logger.error(f"❌ Error processing user message in session {id_session}: {str(e)}")
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
        """Finalizes a session by updating state and sending notifications"""
        try:
            logger.info(f"📝 Finalizing session {id_session}...")
            
            # Get conversation summary
            conversation_summary = agent.get_conversation_summary()
            
            # Update session with summary
            updated_session = SessionService.complete_session_with_summary(id_session, conversation_summary)
            
            if updated_session:
                logger.info(f"✅ Session finalized: {id_session}")
                
                # Send notifications
                try:
                    notification_results = await notification_manager.send_completion_notifications(
                        id_session=id_session,
                        session_data=updated_session,
                        conversation_summary=conversation_summary
                    )
                    
                    if notification_results.get("emails_sent") or notification_results.get("webhook_sent"):
                        logger.info(f"📬 Notifications sent for session {id_session}")
                    
                    if notification_results.get("errors"):
                        logger.warning(f"⚠️ Notification errors: {notification_results['errors']}")
                        
                except Exception as notification_error:
                    logger.error(f"❌ Error sending notifications: {str(notification_error)}")
                
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