from typing import List
from uuid import uuid4, UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from auth.session.jwt import create_access_token, verify_token
from auth.db.database import get_all_services, get_service_by_id, create_session, authenticate_user
from auth.models.schemas import AIService, ServiceRequest, ServiceSession, AuthRequest, AuthResponse

# Configure logging
logger = logging.getLogger(__name__)

# Authentication router
auth_router = APIRouter(tags=["Authentication"])

# Services router
services_router = APIRouter(prefix="/services", tags=["Services"])


@auth_router.post("/session/token", response_model=AuthResponse)
async def authenticate_service(auth_request: AuthRequest):
    """
    Authenticate a client to use a specific AI service
    """
    logger.info(f"Auth request for service ID: {auth_request.id_service} by user: {auth_request.user}")
    
    # Validate user credentials
    if not authenticate_user(auth_request.user, auth_request.password):
        logger.warning(f"Invalid credentials provided by user: {auth_request.user}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Check if service exists
    service = get_service_by_id(auth_request.id_service)
    if not service:
        logger.warning(f"Service with ID {auth_request.id_service} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with ID {auth_request.id_service} not found",
        )
    
    # Generate a client ID (in a real app, this would be from your auth system)
    client_id = f"client_{uuid4()}"
    logger.info(f"Generated client ID: {client_id} for user: {auth_request.user}")
    
    # Create access token with service permissions
    token_data = {
        "sub": client_id,
        "user": auth_request.user,
        "service_id": str(auth_request.id_service),
        "permissions": ["access"]
    }
    
    logger.info(f"Creating token with data: {token_data}")
    access_token, expire = create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expire
    }


@auth_router.post("/session/init", response_model=ServiceSession)
async def create_service_session(service_request: ServiceRequest, token_data: dict = Depends(verify_token)):
    """
    Create a session for an AI service using the access token
    """
    service_id = token_data.get("service_id")
    client_id = token_data.get("sub")
    
    # Check if service exists - convert string to UUID
    service = get_service_by_id(UUID(service_id))
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with ID {service_id} not found",
        )
    
    # In a real application, validate the data against the service requirements
    
    # Generate session
    session_id = uuid4()
    
    # Create a resource URI for the service
    if service["name_service"] == "chatbot-interview":
        resource_uri = f"https://localhost:8000/chatbot/{session_id}"
    else:
        resource_uri = f"https://localhost:8000/services/{service_id}/{session_id}"
    
    # Create and store the session
    session = create_session(
        session_id=session_id,
        service_id=UUID(service_id),
        client_id=client_id,
        resource_uri=resource_uri
    )
    
    return session


@services_router.get("/discovery", response_model=List[AIService])
async def discover_services():
    """
    Endpoint to discover available AI services
    """
    return get_all_services() 