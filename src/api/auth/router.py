import logging
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from secrets import compare_digest
from datetime import datetime, timedelta
import json

from auth.db.database import USERS
from auth.db.sqlite_db import create_session_db, get_session_db, update_session_db
from auth.models.schemas import SessionResponse, InitiateServiceRequest, InitiateServiceResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Authentication router
auth_router = APIRouter(tags=["Authentication"])

# HTTP Basic Auth security
security = HTTPBasic()

@auth_router.post("/chat/session/auth", response_model=SessionResponse)
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
        return SessionResponse(**session)
        
    except Exception as e:
        logger.error(f"Error al crear sesión: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear sesión: {str(e)}"
        )

@auth_router.post("/chat/service/initiate", response_model=InitiateServiceResponse)
async def initiate_service(request: InitiateServiceRequest):
    """
    Inicializar un servicio según el tipo especificado.
    
    Controles:
    - Verificar tiempo de expiración (5 minutos)
    - Verificar status de sesión
    - Verificar estado (que no esté inicializada)
    - Verificar formato JSON
    - Establecer valores
    """
    session_id = request.id_session
    service_type = request.type
    metadata = request.metadata
    
    logger.info(f"Iniciando servicio '{service_type}' para sesión: {session_id}")
    
    try:
        # Obtener la sesión existente
        session = get_session_db(session_id)
        if not session:
            logger.warning(f"Sesión no encontrada: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        # Verificar tiempo de expiración (5 minutos)
        created_at = session['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        time_diff = datetime.utcnow() - created_at
        if time_diff > timedelta(minutes=5):
            logger.warning(f"Sesión expirada: {session_id}, creada hace {time_diff}")
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Sesión expirada. Máximo 5 minutos desde la creación"
            )
        
        # Verificar status de sesión
        if session['status'] != 1:
            logger.warning(f"Sesión inactiva: {session_id}, status: {session['status']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sesión inactiva"
            )
        
        # Verificar estado (que no esté ya inicializada)
        if session['state'] != 'new':
            logger.warning(f"Sesión ya inicializada: {session_id}, estado: {session['state']}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La sesión ya ha sido inicializada"
            )
        
        # Verificar formato JSON del metadata
        try:
            if not isinstance(metadata, dict):
                raise ValueError("Metadata debe ser un objeto JSON válido")
        except Exception as e:
            logger.error(f"Error en formato JSON del metadata: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato JSON inválido en metadata"
            )
        
        # Agregar resource_uri al metadata como URL WebSocket para el chat
        enhanced_metadata = metadata.copy()
        enhanced_metadata["resource_uri"] = f"ws://localhost:8000/api/chat/ws/{session_id}"
        
        # Actualizar la sesión en la base de datos
        updated_session = update_session_db(
            session_id=session_id,
            type_value=service_type,
            state="initiated",
            metadata=enhanced_metadata
        )
        
        if not updated_session:
            logger.error(f"Error al actualizar sesión: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar la sesión"
            )
        
        logger.info(f"Servicio '{service_type}' iniciado exitosamente para sesión: {session_id}")
        return InitiateServiceResponse(**updated_session)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error inesperado al iniciar servicio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        ) 


