from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

class SessionStatus(str, Enum):
    """Estados posibles de una sesión"""
    NEW = "new"
    INITIATED = "initiated"
    STARTED = "started"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ERROR = "error"

class SessionIdResponse(BaseModel):
    """Response model que solo contiene el ID de sesión"""
    id_session: str

class AuthCredentials(BaseModel):
    """Model for authentication credentials"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)

 