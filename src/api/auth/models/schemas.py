from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class SessionResponse(BaseModel):
    """Response model for session"""
    id_session: str
    type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    state: str
    status: int
    metadata: Optional[Dict[str, Any]] = None

class AuthCredentials(BaseModel):
    """Model for authentication credentials"""
    username: str
    password: str

class InitiateServiceRequest(BaseModel):
    """Request model for service initiation"""
    id_session: str
    type: str = Field(..., pattern="^(questionary|help_desk)$")
    metadata: Dict[str, Any]

class InitiateServiceResponse(BaseModel):
    """Response model for service initiation"""
    id_session: str
    type: str
    created_at: datetime
    updated_at: datetime
    state: str
    status: int
    metadata: Dict[str, Any] 