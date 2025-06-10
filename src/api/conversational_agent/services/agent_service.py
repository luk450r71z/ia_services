import logging
from typing import Dict

logger = logging.getLogger(__name__)

class AgentService:
    """Servicio para manejar configuración de agentes"""
    
    @staticmethod
    def setup_questionnarie_agent(websocket_manager):
        """Configura y registra el agente de cuestionario"""
        from ..agents.questionarie_rh import QuestionarieRHAgent
        
        def create_questionnarie_agent(session_data: Dict) -> 'QuestionarieRHAgent':
            content = session_data.get('content', {})
            questions_data = content.get('questions', [])
            
            if not questions_data:
                logger.warning(f"⚠️ No hay preguntas configuradas para sesión questionnarie")
                return None
            
            # Extraer preguntas inteligentemente de cualquier formato
            questions = QuestionarieRHAgent.extract_questions(questions_data)
            logger.info(f"🤖 Agente extrajo {len(questions)} preguntas del JSON")
            
            return QuestionarieRHAgent(questions=questions)
        
        websocket_manager.register_agent_factory("questionnarie", create_questionnarie_agent)
        logger.info("🤖 Agente questionnarie registrado en websocket_manager") 