from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class LogStatus(str, Enum): #TODO
    """Estados posibles de un log de mensaje"""
    ANSWERED = "answered"
    RETRIED = "retried"
    SKIPPED = "skipped"

class WebhookLog(BaseModel):
    """Modelo para el formato de webhook y base de datos"""
    event: str = "onEvent"
    datetime: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    status: str = "Success"
    message: str
    data: Dict[str, Any] = Field(default_factory=dict) 