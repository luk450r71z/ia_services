from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ServiceType(str, Enum):
    """Tipos de servicios disponibles"""
    QUESTIONNARIE = "questionnarie"

class SessionStatus(str, Enum):
    """Estados posibles de una sesión"""
    NEW = "new"
    INITIATED = "initiated"
    STARTED = "started"
    COMPLETED = "completed"
    EXPIRED = "expired"

class QuestionnaireResponse(BaseModel):
    """Response for questionnaire answers"""
    session_id: str
    question: str
    answer: str
    question_number: int
    total_questions: int
    timestamp: datetime

class ConversationSummary(BaseModel):
    """Summary of the entire conversation"""
    session_id: str
    service_type: str
    questions_count: int
    responses: list[QuestionnaireResponse]
    completion_time: datetime
    status: SessionStatus

class WebSocketMessageType(str, Enum):
    """Tipos de mensajes WebSocket"""
    USER_MESSAGE = "user_message"
    AGENT_RESPONSE = "agent_response"
    QUESTION = "question"
    ERROR = "error"
    SYSTEM = "system"
    STATUS = "status"
    TYPING = "typing"

class WebSocketMessage(BaseModel):
    """Modelo para mensajes WebSocket"""
    type: WebSocketMessageType
    content: Optional[str] = None
    session_id: Optional[str] = Field(None, min_length=1)
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

class ChatSession(BaseModel):
    """Modelo para sesiones de chat"""
    session_id: str = Field(..., min_length=1)
    created_at: datetime
    is_active: bool = True
    last_activity: Optional[datetime] = None
    message_count: int = Field(default=0, ge=0)

# Esquemas para servicios conversacionales
class InitiateServiceRequest(BaseModel):
    """Request model for service initiation with session configuration"""
    id_session: str = Field(..., min_length=1)
    content: Optional[Dict[str, Any]] = None
    configs: Optional[Dict[str, Any]] = None

class ServiceUrls(BaseModel):
    """URLs for service access"""
    websocket_url: str = Field(..., min_length=1)
    api_base_url: str = Field(..., min_length=1)
    webui_url: str = Field(..., min_length=1)

class InitiateServiceResponse(BaseModel):
    """Response model for service initiation"""
    id_session: str
    urls: ServiceUrls 