import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from auth.services.auth_service import AuthService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Authentication router
auth_router = APIRouter(tags=["Authentication"])

# HTTP Basic Auth security
security = HTTPBasic()

@auth_router.post("/session/auth")
async def create_session(
    credentials: HTTPBasicCredentials = Depends(security)
) -> dict:
    """
    Create a new session using HTTP Basic Auth.
    Only handles authentication - configuration is sent to the initialization endpoint.
    
    Returns:
        dict: {"id_session": str}
    """
    username = credentials.username
    password = credentials.password

    logger.info(f"Authentication attempt for user: {username}")

    # Validate credentials using the service
    if not AuthService.validate_credentials(username, password):
        logger.warning(f"Invalid authentication attempt for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    logger.info(f"User {username} successfully authenticated")
    
    # Create basic session using the service (only with credentials)
    try:
        session = AuthService.create_user_session()
        
        return {"id_session": session['id_session']}
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )


