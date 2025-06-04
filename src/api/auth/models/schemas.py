from datetime import datetime
from typing import Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

class SessionResponse(BaseModel):
    """Response model for session"""
    id_session: str
    created_at: datetime
    status: str = "active"

class AuthCredentials(BaseModel):
    """Model for authentication credentials"""
    username: str
    password: str 