from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class WebSocketMessage(BaseModel):
    """Modelo para mensajes WebSocket"""
    type: str
    content: Optional[str] = None
    session_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class ChatSession(BaseModel):
    """Modelo para sesiones de chat"""
    session_id: str
    created_at: datetime
    is_active: bool = True 