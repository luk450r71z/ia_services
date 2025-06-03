from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceData(BaseModel):
    """Data model for service-specific data"""
    questions: List[Dict[str, Any]] = []


class AIService(BaseModel):
    """Data model for AI services"""
    id_service: UUID
    name_service: str
    auth_required: bool
    auth_type: str
    data: Dict[str, Any]


class AuthRequest(BaseModel):
    """Request model for authentication"""
    id_service: UUID
    password: str
    user: str


class AuthResponse(BaseModel):
    """Response model for authentication"""
    access_token: str
    token_type: str
    expires_at: datetime


class ServiceRequest(BaseModel):
    """Request model for service session creation"""
    data: Dict[str, Any]


class ServiceSession(BaseModel):
    """Response model for service session"""
    id_session: UUID
    id_service: UUID
    resource_uri: str
    client_id: str
    data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"


class TokenData(BaseModel):
    """Data model for JWT token payload"""
    sub: str
    service_id: str
    permissions: List[str]
    exp: Optional[datetime] = None 