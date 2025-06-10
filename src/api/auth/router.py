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
    Crear una nueva sesión usando HTTP Basic Auth.
    Solo maneja autenticación - la configuración se envía al endpoint de inicialización.
    
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
    
    # Crear sesión básica usando el servicio (solo con credenciales)
    try:
        session = AuthService.create_user_session(username=username)
        
        return {"id_session": session['id_session']}
        
    except Exception as e:
        logger.error(f"Error al crear sesión: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear sesión: {str(e)}"
        )


