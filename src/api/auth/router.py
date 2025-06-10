import logging
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

from typing import Optional, Dict, Any
from pydantic import BaseModel

class SessionConfigRequest(BaseModel):
    type: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    configs: Optional[Dict[str, Any]] = None

@auth_router.post("/session/auth")
async def create_session(
    session_config: Optional[SessionConfigRequest] = None,
    credentials: HTTPBasicCredentials = Depends(security)
) -> dict:
    """
    Crear una nueva sesión usando HTTP Basic Auth.
    
    Returns:
        dict: {"id_session": str}
    """
    username = credentials.username
    password = credentials.password

    logger.info(f"Intento de autenticación para usuario: {username}")

    # Validar credenciales usando el servicio
    if not AuthService.validate_credentials(username, password):
        logger.warning(f"Intento de autenticación inválido para usuario: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    logger.info(f"Usuario {username} autenticado exitosamente")
    
    # Crear sesión usando el servicio
    try:
        session = AuthService.create_user_session(
            username=username,
            session_type=session_config.type if session_config else None,
            content=session_config.content if session_config else None,
            configs=session_config.configs if session_config else None
        )
        
        return {"id_session": session['id_session']}
        
    except Exception as e:
        logger.error(f"Error al crear sesión: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear sesión: {str(e)}"
        )


