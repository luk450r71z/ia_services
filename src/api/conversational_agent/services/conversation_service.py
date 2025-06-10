import logging
from typing import Dict, Any, Protocol

from auth.db.sqlite_db import get_session_db, update_session_db
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

class ConversationService:
    """Servicio para manejar lógica de conversación y persistencia"""
    
    @staticmethod
    async def process_user_message(session_id: str, agent: ConversationalAgent, message: str) -> Dict[str, Any]:
        """
        Procesa un mensaje del usuario con el agente y maneja el guardado
        
        Args:
            session_id: ID de la sesión
            agent: Instancia del agente
            message: Mensaje del usuario
            
        Returns:
            Dict con respuesta del agente y datos adicionales
        """
        try:
            logger.info(f"💬 Procesando mensaje de usuario en sesión {session_id}: {message[:50]}...")
            
            # Procesar mensaje con el agente
            agent_response = agent.process_user_input(message)
            

            
            # Verificar si la conversación se completó
            is_complete = agent.is_conversation_complete()
            
            # Si está completa, finalizar sesión
            if is_complete:
                await ConversationService.complete_session(session_id, agent)
            
            return {
                "response": agent_response,
                "is_complete": is_complete,
                "summary": agent.get_conversation_summary() if is_complete else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje de usuario en sesión {session_id}: {str(e)}")
            raise
    

    
    @staticmethod
    async def complete_session(session_id: str, agent: ConversationalAgent):
        """
        Finaliza una sesión actualizando estado y enviando notificaciones
        
        Args:
            session_id: ID de la sesión
            agent: Instancia del agente con los datos de la conversación
        """
        try:
            logger.info(f"📝 Finalizando sesión {session_id}...")
            
            # Obtener sesión actual
            session_data = get_session_db(session_id)
            if not session_data:
                logger.error(f"❌ No se pudo obtener datos de sesión: {session_id}")
                return
            
            # Obtener resumen de la conversación
            conversation_summary = agent.get_conversation_summary()
            
            # Actualizar content con resumen
            original_content = session_data.get('content', {})
            final_content = original_content.copy()
            final_content["summary"] = conversation_summary
            
            # Actualizar estado en BD
            updated_session = update_session_db(
                session_id=session_id,
                type_value=session_data.get('type', 'unknown'),
                status="complete",
                content=final_content,
                configs=session_data.get('configs', {})
            )
            
            if updated_session:
                logger.info(f"✅ Sesión finalizada: {session_id}")
                
                # Enviar notificaciones
                try:
                    notification_results = await notification_manager.send_completion_notifications(
                        session_id=session_id,
                        session_data=updated_session,
                        conversation_summary=conversation_summary
                    )
                    
                    if notification_results.get("emails_sent") or notification_results.get("webhook_sent"):
                        logger.info(f"📬 Notificaciones enviadas para sesión {session_id}")
                    
                    if notification_results.get("errors"):
                        logger.warning(f"⚠️ Errores en notificaciones: {notification_results['errors']}")
                        
                except Exception as notification_error:
                    logger.error(f"❌ Error enviando notificaciones: {str(notification_error)}")
                
            else:
                logger.warning(f"⚠️ No se pudo actualizar estado de sesión: {session_id}")
                
        except Exception as e:
            logger.error(f"❌ Error finalizando sesión {session_id}: {str(e)}")

class AgentManager:
    """Maneja la inicialización y gestión de agentes conversacionales"""
    
    def __init__(self):
        self.active_agents: Dict[str, ConversationalAgent] = {}
    
    async def initialize_agent(self, session_id: str, session_data: Dict = None) -> bool:
        """
        Inicializa un agente conversacional basado en el tipo de sesión
        
        Args:
            session_id: ID de la sesión
            session_data: Datos de la sesión (opcional)
            
        Returns:
            bool: True si se inicializó correctamente
        """
        try:
            # Usar datos proporcionados o obtener de BD
            if not session_data:
                session_data = get_session_db(session_id)
                
            if not session_data:
                logger.error(f"❌ No se encontró sesión en BD: {session_id}")
                return False
            
            # Obtener tipo de agente
            agent_type = session_data.get('type')
            if not agent_type:
                logger.error(f"❌ No se especificó tipo de agente para sesión: {session_id}")
                return False
            
            # Crear agente directamente según el tipo
            agent = None
            if agent_type == "questionnarie":
                from ..agents.questionarie_rh import QuestionarieRHAgent
                
                content = session_data.get('content', {})
                questions_data = content.get('questions', [])
                
                if not questions_data:
                    logger.warning(f"⚠️ No hay preguntas configuradas para sesión questionnarie")
                    return False
                
                # Extraer preguntas inteligentemente de cualquier formato
                questions = QuestionarieRHAgent.extract_questions(questions_data)
                logger.info(f"🤖 Agente extrajo {len(questions)} preguntas del JSON")
                
                agent = QuestionarieRHAgent(questions=questions)
            else:
                logger.error(f"❌ Tipo de agente no soportado: {agent_type}")
                return False
            
            if agent:
                self.active_agents[session_id] = agent
                logger.info(f"🤖 Agente tipo '{agent_type}' inicializado para sesión {session_id}")
                return True
            else:
                logger.error(f"❌ No se pudo crear agente para sesión: {session_id}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error inicializando agente para sesión {session_id}: {str(e)}")
            return False
    
    def get_agent(self, session_id: str) -> ConversationalAgent:
        """Obtiene el agente activo para una sesión"""
        return self.active_agents.get(session_id)
    
    def get_welcome_message(self, session_id: str) -> str:
        """Obtiene el mensaje de bienvenida del agente"""
        agent = self.get_agent(session_id)
        if agent:
            try:
                welcome_message = agent.start_conversation()
                logger.info(f"🤖 Mensaje de bienvenida obtenido para sesión: {session_id}")
                return welcome_message
            except Exception as e:
                logger.error(f"❌ Error obteniendo mensaje de bienvenida: {str(e)}")
                return None
        else:
            logger.warning(f"⚠️ No hay agente inicializado para sesión: {session_id}")
            return None
    
    def remove_agent(self, session_id: str):
        """Remueve un agente activo"""
        if session_id in self.active_agents:
            del self.active_agents[session_id] 