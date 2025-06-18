from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
import os
import datetime
import json
import logging
from datetime import timezone

from ..models.conversation_models import ConversationState
from ..utils.env_utils import load_env_variables

logger = logging.getLogger(__name__)

# Cargar variables de entorno al importar el módulo
load_env_variables()


class QuestionnaireRHAgent:
    """
    Agente conversacional de RRHH.
    
    Este agente maneja entrevistas automatizadas de manera secuencial,
    recopila respuestas, decide cuándo repreguntar y envía resúmenes por correo.
    """
    
    def __init__(self, content: Dict[str, Any] = None):
        """
        Inicializa el agente de RRHH.
        
        Args:
            content: Contenido completo de la sesión (welcome_message, questions, etc.)
        """
        self.state = ConversationState()
        self.initialized = False
        self.content = content or {}  # Inicializar content como diccionario vacío si es None
        
        # Debug: Log del content recibido
        logger.info(f"🔧 DEBUG: Inicializando agente con questions_data={len(content.get('questions', []) if content else [])} preguntas")
        
        # Extraer y procesar questions del content
        questions_data = content.get('questions', []) if content else []
        try:
            if questions_data:
                self.questions_data = self.extract_questions(questions_data)
                self.questions = [q["question"] for q in self.questions_data]
                logger.info(f"✅ Preguntas extraídas exitosamente: {len(self.questions)} preguntas")
            else:
                self.questions_data = []
                self.questions = []
                logger.warning("⚠️ No se proporcionaron preguntas en el content")
        except Exception as e:
            logger.error(f"❌ Error extrayendo preguntas: {str(e)}")
            self.questions_data = []
            self.questions = []
        
        # Guardar preguntas en metadatos
        if self.questions:
            self.state.extra_data["questions_data"] = self.questions_data
    
    @staticmethod
    def extract_questions(questions_data: Any) -> List[Dict[str, Any]]:
        """
        Extrae preguntas inteligentemente de cualquier formato JSON usando LLM.
        
        Args:
            questions_data: Datos en cualquier formato (array, object, nested)
            
        Returns:
            Lista de diccionarios con pregunta y opciones (si las hay)
            Formato: [{"question": "¿Pregunta?", "options": ["a", "b"] o None}]
            
        Raises:
            ValueError: Si no se puede extraer preguntas o no hay LLM disponible
        """
        # Convertir a JSON string
        json_str = json.dumps(questions_data, indent=2, ensure_ascii=False)
        
        # Configurar LLM (obligatorio)
        load_env_variables()
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY es requerida para extraer preguntas inteligentemente")
        
        llm = ChatGroq(api_key=groq_api_key, model="llama3-8b-8192")
        
        prompt = f"""JSON_INPUT:
{json_str}

TASK: Extract questions and return JSON array only.

OUTPUT_FORMAT:
[{{"question": "text", "options": null}}, {{"question": "text", "options": ["a","b"]}}]

RETURN ONLY JSON ARRAY - NO OTHER TEXT"""
        
        response = llm.invoke(prompt)
        content = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        try:
            # Extraer JSON de la respuesta (puede haber texto adicional)
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No se encontró array JSON en la respuesta")
            
            json_content = content[json_start:json_end]
            questions_with_options = json.loads(json_content)
            
            if not questions_with_options:
                raise ValueError("No se encontraron preguntas en el JSON proporcionado")
            
            return questions_with_options
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parseando JSON: {json_content[:100]}...")
        except Exception as e:
            raise ValueError(f"Error procesando respuesta del LLM: {str(e)}")
    
    def _format_question_with_options(self, question_index: int) -> str:
        """
        Formatea una pregunta con sus opciones (si las tiene)
        
        Args:
            question_index: Índice de la pregunta
            
        Returns:
            Pregunta formateada con opciones
        """
        if not self.questions_data or question_index >= len(self.questions_data):
            return self.questions[question_index] if question_index < len(self.questions) else ""
        
        question_data = self.questions_data[question_index]
        question_text = question_data["question"]
        options = question_data.get("options")
        
        if options and isinstance(options, list):
            # Es pregunta de opción múltiple
            options_text = "\n".join([f"  • {option}" for option in options])
            return f"{question_text}\n\nOpciones:\n{options_text}\n\n"
        else:
            # Es pregunta abierta
            return question_text
    
    def start_conversation(self, session_data: Dict[str, Any] = None) -> str:
        """
        Inicia una nueva conversación.
        
        Args:
            session_data: Datos de la sesión (opcional)
        
        Returns:
            Mensaje inicial del agente
        """
        # Debug: Log del estado del agente
        logger.info(f"🔧 DEBUG: start_conversation - questions_count={len(self.questions)}")
        
        # Verificar que hay preguntas configuradas
        if not self.questions:
            logger.error("❌ No hay preguntas configuradas en el agente")
            return "Error: No questions have been configured for this interview. Please contact the administrator."
        
        # Configurar estado inicial
        self.state.pending_questions = self.questions
        self.state.current_question_index = 0
        self.state.current_question = self.questions[0]
        
        # Obtener mensaje de bienvenida del content y reemplazar variables
        welcome_content = self.content.get('welcome_message', """I am Adaptiera's HR Assistant. 
I will ask you some questions to get to know you better.
Please answer as honestly as possible.

Let's begin:""")
        
        # Reemplazar {client_name} con el nombre real del cliente
        client_name = self.content.get('client_name', '')
        welcome_content = welcome_content.replace('{client_name}', client_name)
        
        welcome_message = AIMessage(content=welcome_content)
        self.state.messages.append(welcome_message)
        
        # Primera pregunta con opciones (si las tiene)
        formatted_question = self._format_question_with_options(0)
        question_message = AIMessage(content=formatted_question)
        self.state.messages.append(question_message)
        
        self.initialized = True
        return f"{welcome_message.content}\n\n{formatted_question}"
    
    def process_user_input(self, user_input: str) -> str:
        """
        Procesa la entrada del usuario y retorna la respuesta del agente.
        
        Args:
            user_input: Mensaje del usuario
            
        Returns:
            Respuesta del agente
        """
        if not self.initialized:
            return self.start_conversation()
        
        # Verificar si la conversación ya está completa
        if self.state.conversation_complete:
            return "The interview has already ended. Thank you for your participation!"
        
        # Agregar mensaje del usuario al estado
        user_message = HumanMessage(content=user_input)
        self.state.messages.append(user_message)
        
        # Evaluar la respuesta
        is_satisfactory, clarification_reason = self._evaluate_response(user_input)
        
        if is_satisfactory:
            # Guardar respuesta satisfactoria
            self.state.user_responses[self.state.current_question] = user_input
            
            # Crear nombre de archivo para respuestas
            if self.questions:
                # Usar timestamp para hacer el archivo único
                timestamp = datetime.datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                response_file = f"data/user_responses_custom_{timestamp}.json"
            else:
                response_file = "data/user_responses.json"
            
            # Las respuestas se guardan automáticamente en la base de datos
            self.state.needs_clarification = False
            self.state.clarification_reason = None
            
            # Avanzar a la siguiente pregunta
            return self._next_question()
        else:
            # Solicitar aclaración
            self.state.needs_clarification = True
            self.state.clarification_reason = clarification_reason
            
            clarification_message = AIMessage(content=f"""I would like you to expand on your previous response.
{clarification_reason}

Please provide more details about: {self.state.current_question}""")
            
            self.state.messages.append(clarification_message)
            return clarification_message.content
    
    def _evaluate_response(self, user_response: str) -> tuple[bool, str]:
        """
        Evalúa si la respuesta del usuario es satisfactoria.
        Valida especialmente preguntas de opción múltiple.
        """
        current_question = self.state.current_question
        
        # Verificar si es pregunta de opción múltiple
        current_index = self.state.current_question_index
        if (self.questions_data and 
            current_index < len(self.questions_data)):
            
            question_data = self.questions_data[current_index]
            options = question_data.get("options")
            
            if options and isinstance(options, list):
                # Es pregunta de opción múltiple - validar respuesta
                return self._validate_multiple_choice(user_response, options)
        
        # Para preguntas abiertas, usar evaluación con LLM
        return self._evaluate_open_question(user_response, current_question)
    
    def _validate_multiple_choice(self, user_response: str, options: List[str]) -> tuple[bool, str]:
        """Validates multiple choice response using LLM"""
        # Configure LLM
        load_env_variables()
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY is required to validate multiple choice responses")
        
        llm = ChatGroq(api_key=groq_api_key, model="llama3-8b-8192")
        
        options_text = ", ".join(options)
        
        prompt = f"""
        Determine if the user's response corresponds to any of the valid options.
        
        Valid options: {options_text}
        User response: {user_response}
        
        Respond ONLY with:
        - "VALID" if the response matches any option (accepts variations, synonyms, etc.)
        - "INVALID" if it doesn't correspond to any option
        
        Be FLEXIBLE - accept responses that clearly refer to an option even if they're not exact.
        """
        
        response = llm.invoke(prompt)
        content = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        if content.startswith("VALID"):
            return True, ""
        else:
            options_list = "\n".join([f"  • {opt}" for opt in options])
            return False, f"Please choose one of the following options:\n{options_list}"
    
    def _evaluate_open_question(self, user_response: str, current_question: str) -> tuple[bool, str]:
        """Evaluates open-ended question with LLM"""
        load_env_variables()
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not groq_api_key:
            # Simple fallback for open questions
            is_satisfactory = len(user_response.strip()) > 3
            clarification_reason = "Please provide a more detailed response." if not is_satisfactory else ""
            return is_satisfactory, clarification_reason
        
        llm = ChatGroq(api_key=groq_api_key, model="llama3-8b-8192")
        
        prompt = f"""
        Evaluate if the following response is satisfactory for the given question:
        
        Question: {current_question}
        Response: {user_response}
        
        Respond ONLY with:
        - "SATISFACTORY" if the response provides basic relevant information
        - "NEEDS_CLARIFICATION: [specific reason]" if it's empty, irrelevant, or very confusing
        
        Be LENIENT in your evaluation. Accept responses that have at least some relation to the question, 
            even if they are brief or not very detailed. Only request clarification if the response really 
            doesn't make sense or is completely off-topic.
        """
        
        try:
            response = llm.invoke(prompt)
            content = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            
            if content.startswith("SATISFACTORY"):
                return True, ""
            elif content.startswith("NEEDS_CLARIFICATION"):
                reason = content.replace("NEEDS_CLARIFICATION:", "").strip()
                return False, reason
            else:
                # Formato inesperado, ser permisivo
                return True, ""
        except Exception as e:
            # Fallback simple
            is_satisfactory = len(user_response.strip()) > 3
            clarification_reason = "Please provide a more detailed response." if not is_satisfactory else ""
            return is_satisfactory, clarification_reason
    
    def _next_question(self) -> str:
        """
        Avanza a la siguiente pregunta o finaliza la conversación.
        
        Returns:
            Mensaje con la siguiente pregunta o finalización
        """
        self.state.current_question_index += 1
        
        if self.state.current_question_index < len(self.state.pending_questions):
            # Hay más preguntas
            self.state.current_question = self.state.pending_questions[self.state.current_question_index]
            
            # Formatear siguiente pregunta con opciones (si las tiene)
            formatted_question = self._format_question_with_options(self.state.current_question_index)
            
            next_question_message = AIMessage(content=f"""Perfect, thank you for your response.

Next question:
{formatted_question}""")
            
            self.state.messages.append(next_question_message)
            return next_question_message.content
        else:
            # No hay más preguntas, finalizar conversación
            return self._finalize_conversation()
    
    def _finalize_conversation(self) -> str:
        """
        Finaliza la conversación guardando respuestas y enviando correo.
        
        Returns:
            Mensaje de finalización
        """
        self.state.conversation_complete = True
        self.state.current_question = None
        
        # Las notificaciones ahora se manejan automáticamente por el websocket_manager
        # cuando la conversación se marca como completa - no necesitamos envío manual aquí
        
        final_message = AIMessage(content="""Thank you very much for your time! 

✅ Your responses have been successfully saved.

✅ Our HR team will review your information and contact you soon.

Have a great day!""")
        
        self.state.messages.append(final_message)
        return final_message.content
    
    def is_conversation_complete(self) -> bool:
        """
        Verifica si la conversación ha terminado.
        
        Returns:
            True si la conversación está completa
        """
        return self.state.conversation_complete
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de la conversación.
        
        Returns:
            Diccionario con el resumen de la conversación
        """
        return {
            "responses": self.state.user_responses,
            "questions_asked": len(self.state.user_responses),
            "total_questions": len(self.state.pending_questions),
            "complete": self.state.conversation_complete,
            "messages_count": len(self.state.messages)
        }
    
    def reset_conversation(self):
        """Reinicia la conversación"""
        self.state = ConversationState()
        self.initialized = False


# Función de conveniencia para crear una instancia del agente
def create_questionnaire_rh_agent(content: Dict[str, Any] = None) -> QuestionnaireRHAgent:
    """
    Crea una nueva instancia del agente de RRHH simplificado.
    
    Args:
        content: Contenido completo de la sesión (welcome_message, questions, etc.)
    
    Returns:
        Instancia del agente configurada
    """
    logger.info(f"🤖 Creando agente con content completo (questions_data: {len(content.get('questions', []) if content else [])} preguntas)")
    return QuestionnaireRHAgent(content) 