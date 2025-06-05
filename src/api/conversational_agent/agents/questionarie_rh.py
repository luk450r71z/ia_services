from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
import os
import datetime

from ..models.conversation_models import ConversationState
from .tools.email_tool import simulate_email_send_direct
from ..utils.env_utils import load_env_variables

# Cargar variables de entorno al importar el módulo
load_env_variables()


class QuestionarieRHAgent:
    """
    Agente conversacional de RRHH simplificado sin LangGraph.
    
    Este agente maneja entrevistas automatizadas de manera secuencial,
    recopila respuestas, decide cuándo repreguntar y envía resúmenes por correo.
    """
    
    def __init__(self, questions: List[str] = None):
        """
        Inicializa el agente de RRHH.
        
        Args:
            questions: Lista de preguntas específicas para la entrevista
        """
        self.state = ConversationState()
        self.initialized = False
        self.questions = questions or []
        
        # Guardar preguntas en metadatos
        if questions:
            self.state.metadata["custom_questions"] = questions
            print(f"🎯 Agente inicializado con {len(questions)} preguntas personalizadas")
        else:
            print("🎯 Agente inicializado sin preguntas específicas")
    
    def start_conversation(self) -> str:
        """
        Inicia una nueva conversación.
        
        Returns:
            Mensaje inicial del agente
        """
        print("🚀 Inicializando conversación...")
        
        # Usar preguntas proporcionadas o cargar preguntas por defecto
        if self.questions:
            questions = self.questions
        else:
            # No hay preguntas configuradas
            print("❌ No hay preguntas configuradas para esta sesión")
            return "Error: No se han configurado preguntas para esta entrevista. Por favor, contacta al administrador."
        


        self.state.pending_questions = questions
        self.state.current_question_index = 0
        
        if questions:
            self.state.current_question = questions[0]
            
            # Mensaje de bienvenida
            welcome_content = """¡Hola! Soy el asistente de RRHH de Adaptiera. 
Voy a realizarte algunas preguntas para conocerte mejor.
Responde con la mayor sinceridad posible.

Empecemos:"""
            
            welcome_message = AIMessage(content=welcome_content)
            self.state.messages.append(welcome_message)
            
            # Primera pregunta
            question_message = AIMessage(content=self.state.current_question)
            self.state.messages.append(question_message)
            
            self.initialized = True
            return f"{welcome_message.content}\n\n{self.state.current_question}"
        
        return "¡Hola! Soy el asistente de RRHH. ¿Cómo puedo ayudarte?"
    
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
            print("⚠️ Mensaje rechazado: la conversación ya está completa")
            return "La entrevista ya ha finalizado. ¡Gracias por tu participación!"
        
        # Agregar mensaje del usuario al estado
        user_message = HumanMessage(content=user_input)
        self.state.messages.append(user_message)
        
        print(f"🤔 Procesando respuesta del usuario: {user_input[:50]}...")
        
        # Evaluar la respuesta
        is_satisfactory, clarification_reason = self._evaluate_response(user_input)
        
        if is_satisfactory:
            # Guardar respuesta satisfactoria
            self.state.user_responses[self.state.current_question] = user_input
            
            # Crear nombre de archivo para respuestas
            if self.questions:
                # Usar timestamp para hacer el archivo único
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                response_file = f"data/user_responses_custom_{timestamp}.json"
            else:
                response_file = "data/user_responses.json"
            
            # Las respuestas se guardan automáticamente en la base de datos
            self.state.needs_clarification = False
            self.state.clarification_reason = None
            print(f"✅ Respuesta aceptada para: {self.state.current_question}")
            
            # Avanzar a la siguiente pregunta
            return self._next_question()
        else:
            # Solicitar aclaración
            self.state.needs_clarification = True
            self.state.clarification_reason = clarification_reason
            print(f"❓ Necesita clarificación: {clarification_reason}")
            
            clarification_message = AIMessage(content=f"""Me gustaría que puedas ampliar tu respuesta anterior.
{clarification_reason}

Por favor, proporciona más detalles sobre: {self.state.current_question}""")
            
            self.state.messages.append(clarification_message)
            return clarification_message.content
    
    def _evaluate_response(self, user_response: str) -> tuple[bool, str]:
        """
        Evalúa si la respuesta del usuario es satisfactoria.
        """
        current_question = self.state.current_question
        
        # Asegurar que las variables de entorno estén cargadas
        load_env_variables()
        
        # Configurar el LLM (Groq)
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            print("⚠️ GROQ_API_KEY no configurada, usando lógica simple")
            # Lógica simple sin LLM (más permisiva)
            is_satisfactory = len(user_response.strip()) > 3
            clarification_reason = "Por favor, proporciona una respuesta más detallada." if not is_satisfactory else ""
            return is_satisfactory, clarification_reason
        
        print(f"✅ GROQ_API_KEY encontrada, usando evaluación inteligente")
        
        try:
            # Usar Groq para evaluar la respuesta
            llm = ChatGroq(api_key=groq_api_key, model="llama-3.3-70b-versatile")
            
            evaluation_prompt = f"""
            Evalúa si la siguiente respuesta es satisfactoria para la pregunta planteada:
            
            Pregunta: {current_question}
            Respuesta: {user_response}
            
            Responde SOLO con:
            - "SATISFACTORIA" si la respuesta proporciona información básica relevante a la pregunta
            - "NECESITA_CLARIFICACION: [razón específica]" si la respuesta está completamente vacía, es irrelevante o muy confusa
            
            Sé PERMISIVO en tu evaluación. Acepta respuestas que tengan al menos alguna relación con la pregunta, 
            incluso si son breves o no muy detalladas. Solo solicita clarificación si la respuesta realmente 
            no tiene sentido o está completamente fuera de tema.
            """
            
            # ✅ SOLUCIÓN DEFINITIVA: Manejo seguro de la respuesta
            response = llm.invoke(evaluation_prompt)
            
            # Extraer contenido de forma segura - ESTO SOLUCIONA EL ERROR
            if hasattr(response, 'content') and response.content:
                evaluation = response.content.strip()
            elif isinstance(response, str):
                evaluation = response.strip()
            else:
                # Convertir a string de forma segura
                evaluation = str(response).strip()
            
            print(f"🔍 Evaluación recibida: {evaluation}")
            
            if evaluation.startswith("SATISFACTORIA"):
                return True, ""
            elif evaluation.startswith("NECESITA_CLARIFICACION"):
                reason = evaluation.replace("NECESITA_CLARIFICACION:", "").strip()
                return False, reason
            else:
                # Si la respuesta no tiene el formato esperado, ser permisivo
                print(f"⚠️ Formato inesperado: {evaluation}")
                return True, ""
                
        except Exception as e:
            print(f"Error al evaluar con Groq: {e}")
            print(f"Tipo de error: {type(e)}")
            # Fallback a lógica simple (más permisiva)
            is_satisfactory = len(user_response.strip()) > 3
            clarification_reason = "Por favor, proporciona una respuesta más detallada." if not is_satisfactory else ""
            return is_satisfactory, clarification_reason
    
    def _next_question(self) -> str:
        """
        Avanza a la siguiente pregunta o finaliza la conversación.
        
        Returns:
            Mensaje con la siguiente pregunta o finalización
        """
        print("➡️ Avanzando a la siguiente pregunta...")
        
        self.state.current_question_index += 1
        
        if self.state.current_question_index < len(self.state.pending_questions):
            # Hay más preguntas
            self.state.current_question = self.state.pending_questions[self.state.current_question_index]
            
            next_question_message = AIMessage(content=f"""Perfecto, gracias por tu respuesta.

Siguiente pregunta:
{self.state.current_question}""")
            
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
        print("🏁 Finalizando conversación...")
        
        self.state.conversation_complete = True
        self.state.current_question = None
        
        # Enviar correo
        email_success = simulate_email_send_direct(self.state.user_responses)
        
        if email_success:
            final_message = AIMessage(content="""¡Muchas gracias por tu tiempo! 

✅ Tus respuestas han sido guardadas correctamente
✅ Se ha enviado un resumen por correo electrónico

Nuestro equipo de RRHH revisará tu información y se pondrá en contacto contigo pronto.

¡Que tengas un excelente día!""")
        else:
            final_message = AIMessage(content="""Gracias por completar la entrevista. 
Hubo algunos problemas técnicos al procesar tu información, 
pero nuestro equipo se pondrá en contacto contigo pronto.""")
        
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
def create_questionarie_rh_agent(questions: List[str] = None) -> QuestionarieRHAgent:
    """
    Crea una nueva instancia del agente de RRHH simplificado.
    
    Args:
        questions: Lista de preguntas específicas para la entrevista
    
    Returns:
        Instancia del agente configurada
    """
    return QuestionarieRHAgent(questions) 