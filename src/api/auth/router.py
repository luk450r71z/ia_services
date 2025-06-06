import logging
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from secrets import compare_digest
from datetime import datetime

from auth.db.database import USERS
from auth.db.sqlite_db import create_session_db, get_session_db
from auth.models.schemas import SessionIdResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Authentication router
auth_router = APIRouter(tags=["Authentication"])

# HTTP Basic Auth security
security = HTTPBasic()

@auth_router.post("/session/auth", response_model=SessionIdResponse)
async def create_session(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Crear una nueva sesión usando HTTP Basic Auth.
    Valida las credenciales de usuario y contraseña contra la base de datos USERS.
    
    Controles:
    - Verificar credenciales de usuario
    - Crear nueva sesión con estado 'new'
    - Establecer valores iniciales
    """
    username = credentials.username
    password = credentials.password

    logger.info(f"Intento de autenticación para usuario: {username}")

    # Validar credenciales contra el diccionario USERS
    if username not in USERS or not compare_digest(USERS[username], password):
        logger.warning(f"Intento de autenticación inválido para usuario: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    logger.info(f"Usuario {username} autenticado exitosamente")
    
    # Crear una nueva sesión en la base de datos
    try:
        session = create_session_db()
        if not session:
            logger.error("Error al crear sesión - no se retornó sesión")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear sesión"
            )
        
        logger.info(f"Nueva sesión creada para usuario {username}: {session['id_session']}")
        return SessionIdResponse(**session)
        
    except Exception as e:
        logger.error(f"Error al crear sesión: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear sesión: {str(e)}"
        )


# TODO: Implementar endpoint para helpdesk en el futuro
# @auth_router.post("/chat/helpdesk/initiate", response_model=InitiateServiceResponse)
# async def initiate_helpdesk(request: InitiateServiceRequest):
#     """Inicializar un servicio de helpdesk según el tipo especificado."""
#     # Lógica similar pero específica para helpdesk
#     pass


