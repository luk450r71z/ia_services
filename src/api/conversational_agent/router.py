from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
import logging

# Importar modelos
from .models.schemas import (
    InitiateServiceRequest, 
    InitiateServiceResponse, 
    ServiceUrls
)
# Importar servicios
from .services.websocket_manager import websocket_manager
from .services.session_service import SessionService


# Configure logging
logger = logging.getLogger(__name__)

chat_router = APIRouter()

@chat_router.post("/questionnaire/initiate", response_model=InitiateServiceResponse)
async def initiate_questionnaire(request: InitiateServiceRequest):
    """
    Inicializar un cuestionario con configuración de sesión.
    
    Controles:
    - Verificar tiempo de expiración (5 minutes)  
    - Verificar status de sesión
    - Actualizar sesión con configuración proporcionada
    - Obtener content y configs de la BD
    """
    id_session = request.id_session
    service_type = "questionnaire"  # Tipo implícito en el endpoint
    
    try:
        # Inicializar la sesión con la configuración proporcionada
        session_data = SessionService.validate_and_initiate_session(
            id_session=id_session,
            new_content=request.content.model_dump() if request.content else None,
            new_configs=request.configs.model_dump() if request.configs else None,
            session_type=service_type
        )
        
        logger.info(f"Service '{service_type}' started successfully for session: {id_session}")
        
        # Crear respuesta con URLs
        urls = ServiceUrls(
            websocket_url=f"ws://localhost:8000/api/chat/questionnaire/start/{id_session}",
            webui_url=f"http://localhost:8080/{id_session}"
        )
        
        return InitiateServiceResponse(
            id_session=id_session,
            urls=urls
        )
        
    except ValueError as e:
        # Errores de validación del servicio
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "expired" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Unexpected error starting service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )



@chat_router.websocket("/questionnaire/start/{id_session}")
async def websocket_endpoint(websocket: WebSocket, id_session: str):
    """
    Endpoint WebSocket unificado para comunicación conversacional.
    
    URL: ws://localhost:8000/api/chat/questionnaire/start/{id_session}
    
    Flujo simplificado:
    1. Validar sesión (debe estar 'initiated')
    2. Conectar WebSocket e inicializar agente
    3. Si todo está bien, actualizar status a 'started'
    4. Manejar comunicación bidireccional
    """
    try:
        # Validación usando servicio
        session_data = SessionService.validate_and_start_session(id_session)
        
        if not session_data:
            logger.warning(f"❌ Invalid or expired session: {id_session}")
            await websocket.close(code=4004, reason="Invalid or expired session")
            return
        
        # Verificar que tenga contenido válido para cuestionario
        content = session_data.get('content')
        if not content or not isinstance(content, dict) or not content.get('questions'):
            logger.warning(f"❌ Invalid content in session: {id_session}")
            await websocket.close(code=4001, reason="Invalid session content")
            return
        
        try:
            # Conectar WebSocket e inicializar agente
            await websocket_manager.connect_and_initialize(websocket, id_session, session_data)
            # Manejar comunicación completa
            await websocket_manager.handle_connection_lifecycle(websocket, id_session)
            
        except Exception as e:
            logger.error(f"❌ Error en inicialización de WebSocket: {str(e)}")
            await websocket.close(code=1011, reason="Internal server error")
            return
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"❌ Fatal error in WebSocket {id_session}: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        websocket_manager.disconnect(id_session) 
