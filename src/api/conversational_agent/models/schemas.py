from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

# ===== Enums =====

class SessionStatus(str, Enum):
    """Estados posibles de una sesión"""
    NEW = "new"
    INITIATED = "initiated"
    STARTED = "started"
    ENDED = "ended"
    EXPIRED = "expired"

class AnswerType(str, Enum):
    """Tipos de respuestas válidas para preguntas"""
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"

# ===== Modelos de Cuestionario =====

class Question(BaseModel):
    """Modelo para una pregunta del cuestionario"""
    id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    answerType: AnswerType
    options: Optional[List[str]] = None

class QuestionnaireContent(BaseModel):
    """Modelo para el contenido del cuestionario"""
    questions: List[Question]
    client_name: str = Field(..., min_length=1)
    welcome_message: str = Field(..., min_length=1)

class QuestionnaireConfigs(BaseModel):
    """Modelo para las configuraciones del cuestionario"""
    webhook_url: str = Field(..., min_length=1)
    emails: List[str] = Field(..., min_length=1)
    avatar: Dict[str, Any] = Field(..., min_length=1)

# ===== Modelos de Servicio =====

class ServiceUrls(BaseModel):
    """URLs para acceso al servicio"""
    websocket_url: str = Field(..., min_length=1)
    webui_url: str = Field(..., min_length=1)

class InitiateServiceRequest(BaseModel):
    """Modelo de request para iniciar un servicio con configuración de sesión"""
    id_session: str = Field(..., min_length=1)
    content: Optional[QuestionnaireContent] = None
    configs: Optional[QuestionnaireConfigs] = None

class InitiateServiceResponse(BaseModel):
    """Modelo de respuesta para iniciar un servicio"""
    id_session: str
    urls: ServiceUrls

# ===== Modelos de WebSocket =====

class WebSocketMessageType(str, Enum):
    """Tipos de mensajes WebSocket"""
    AGENT_RESPONSE = "agent_response"
    USER_MESSAGE = "user_message"
    ERROR = "error"
    UI_CONFIG = "ui_config"

class WebSocketMessage(BaseModel):
    """Modelo para mensajes WebSocket"""
    type: WebSocketMessageType
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))