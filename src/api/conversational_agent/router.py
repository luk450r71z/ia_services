from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
import logging

# Importar modelos
from .models.schemas import InitiateServiceRequest, InitiateServiceResponse, ServiceUrls
# Importar WebSocket manager
from .websocket_manager import websocket_manager
# Importar servicios
from .services.session_service import SessionService
from .services.agent_service import AgentService
from .services.websocket_service import WebSocketService

# Configure logging
logger = logging.getLogger(__name__)

chat_router = APIRouter()

# Configurar agentes al cargar el módulo
AgentService.setup_questionnarie_agent(websocket_manager)



@chat_router.post("/questionnarie/initiate", response_model=InitiateServiceResponse)
async def initiate_questionnarie(request: InitiateServiceRequest):
    """
    Inicializar un cuestionario obteniendo toda la información de la BD.
    
    Controles:
    - Verificar tiempo de expiración (5 minutos)  
    - Verificar status de sesión (debe estar en 'new')
    - Obtener content y configs de la BD
    """
    session_id = request.id_session
    
    try:
        # Usar servicio para inicializar la sesión
        session_data = SessionService.initiate_session(session_id)
        service_type = session_data.get('type')
        
        logger.info(f"Servicio '{service_type}' iniciado exitosamente para sesión: {session_id}")
        
        # Crear respuesta con URLs
        urls = ServiceUrls(
            websocket_url=f"ws://localhost:8000/api/chat/questionnarie/start/{session_id}",
            api_base_url="http://localhost:8000",
            webui_url="http://localhost:3000/"
        )
        
        return InitiateServiceResponse(
            id_session=session_id,
            urls=urls
        )
        
    except ValueError as e:
        # Errores de validación del servicio
        if "no encontrada" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "expirada" in str(e):
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
        logger.error(f"Error inesperado al iniciar servicio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@chat_router.websocket("/questionnarie/start/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Endpoint WebSocket unificado para comunicación conversacional.
    
    URL: ws://localhost:8000/api/chat/questionnarie/start/{session_id}
    
    Flujo simplificado:
    1. Validar sesión (debe estar 'initiated')
    2. Actualizar status a 'started'  
    3. Conectar WebSocket e inicializar agente
    4. Manejar comunicación bidireccional
    """
    logger.info(f"🔗 Nueva conexión WebSocket para sesión: {session_id}")
    
    try:
        # Validación usando servicio
        session_data = SessionService.validate_session_for_websocket(session_id)
        
        if not session_data:
            logger.warning(f"❌ Sesión inválida o expirada: {session_id}")
            await websocket.close(code=4004, reason="Sesión inválida o expirada")
            return
        
        # Verificar que tenga contenido válido para cuestionario
        content = session_data.get('content')
        if not content or not isinstance(content, dict) or not content.get('questions'):
            logger.warning(f"❌ Contenido inválido en sesión: {session_id}")
            await websocket.close(code=4001, reason="Contenido de cuestionario inválido")
            return
        
        # Marcar sesión como iniciada usando servicio
        SessionService.start_session(session_id, session_data)
        
        # Conectar WebSocket
        await websocket_manager.connect(websocket, session_id)
        logger.info(f"✅ WebSocket conectado para sesión: {session_id}")
        
        # Inicializar agente usando servicio
        await WebSocketService.initialize_agent_and_send_welcome(
            websocket_manager, session_id, session_data
        )
        
        # Manejar comunicación usando servicio
        await WebSocketService.handle_message_loop(
            websocket_manager, websocket, session_id
        )
                    
    except WebSocketDisconnect:
        logger.info(f"🔌 Cliente desconectado de sesión: {session_id}")
    except Exception as e:
        logger.error(f"❌ Error fatal en WebSocket {session_id}: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Error interno del servidor")
        except:
            pass
    finally:
        websocket_manager.disconnect(session_id) 
