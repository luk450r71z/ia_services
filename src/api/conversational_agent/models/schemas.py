from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

# Importar SessionStatus desde auth
from auth.models.schemas import SessionStatus

class ServiceType(str, Enum):
    """Tipos de servicios disponibles"""
    QUESTIONNARIE = "questionnarie"

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
    """Request model for service initiation"""
    id_session: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1, max_length=50, pattern="^[a-zA-Z_][a-zA-Z0-9_]*$")
    content: Dict[str, Any]
    configs: Optional[Dict[str, Any]] = None

class ServiceUrls(BaseModel):
    """URLs for service access"""
    resource_uri: str = Field(..., min_length=1)
    webui: str = Field(..., min_length=1)

class InitiateServiceResponse(BaseModel):
    """Response model for service initiation"""
    id_session: str
    urls: ServiceUrls

class StartServiceRequest(BaseModel):
    """Request model for starting service"""
    id_session: str = Field(..., min_length=1)

class StartServiceResponse(BaseModel):
    """Response model for service start"""
    id_session: str
    type: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus
    content: Dict[str, Any]
    configs: Optional[Dict[str, Any]] = None
    welcome_message: Optional[str] = None

class WebSocketServiceResponse(BaseModel):
    """Simple response model for WebSocket service start"""
    id_session: str
    websocket_endpoint: str
    status: str
    message: str
    welcome_message: Optional[str] = None 