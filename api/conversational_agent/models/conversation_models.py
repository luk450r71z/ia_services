from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class ConversationState(BaseModel):
    """Estado del agente conversacional que mantiene el contexto de la conversación"""
    
    # Historial de mensajes de la conversación
    messages: List[BaseMessage] = Field(default_factory=list)
    
    # Preguntas pendientes por hacer
    pending_questions: List[str] = Field(default_factory=list)
    
    # Respuestas del usuario recopiladas
    user_responses: Dict[str, str] = Field(default_factory=dict)
    
    # Pregunta actual que se está procesando
    current_question: Optional[str] = None
    
    # Índice de la pregunta actual
    current_question_index: int = 0
    
    # Flag para indicar si necesita repreguntar
    needs_clarification: bool = False
    
    # Razón por la cual necesita aclaración
    clarification_reason: Optional[str] = None
    
    # Flag para indicar si la conversación ha terminado
    conversation_complete: bool = False
    
    # Datos adicionales que pueden ser útiles
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True 