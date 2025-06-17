from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class LogStatus(str, Enum):
    """Estados posibles de un log de mensaje"""
    ANSWERED = "answered"
    RETRIED = "retried"
    SKIPPED = "skipped"

class MessageLog(BaseModel):
    """Modelo para los logs de mensajes"""
    id_session: str = Field(..., min_length=1)
    message_type: str  # "user" o "agent"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    status: LogStatus
    attempt_number: int = 1
    metadata: Optional[Dict[str, Any]] = None
    webhook_sent: bool = False
    webhook_response: Optional[Dict[str, Any]] = None 