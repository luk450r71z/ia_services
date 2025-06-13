from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
import logging

# Importar modelos
from .models.schemas import InitiateServiceRequest, InitiateServiceResponse, ServiceUrls
# Importar WebSocket manager
from .websocket_manager import websocket_manager
# Importar servicios
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
    - Verificar status de sesión (debe estar en 'new')
    - Actualizar sesión con configuración proporcionada
    - Obtener content y configs de la BD
    """
    id_session = request.id_session
    service_type = "questionnaire"  # Tipo implícito en el endpoint
    
    # Validación simple: content 
    if request.content:
        required_content_fields = ['questions', 'client_name', 'welcome_message']
        missing_fields = [field for field in required_content_fields if field not in request.content]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El content debe contener los campos: {', '.join(missing_fields)}"
            )
        
        # Validación de la estructura de questions
        questions = request.content.get('questions', [])
        valid_answer_types = ['short_text', 'long_text', 'multiple_choice', 'single_choice']
        
        for i, question in enumerate(questions):
            # Validar campos requeridos
            required_question_fields = ['id', 'question', 'answerType']
            missing_question_fields = [field for field in required_question_fields if field not in question]
            if missing_question_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La pregunta {i+1} debe contener los campos: {', '.join(missing_question_fields)}"
                )
            
            # Validar tipo de respuesta
            if question['answerType'] not in valid_answer_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La pregunta {i+1} tiene un tipo de respuesta inválido. Debe ser uno de: {', '.join(valid_answer_types)}"
                )
            
            # Validar opciones para preguntas de opción múltiple o única
            if question['answerType'] in ['multiple_choice', 'single_choice']:
                if 'options' not in question or not isinstance(question['options'], list) or len(question['options']) < 2:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"La pregunta {i+1} de tipo {question['answerType']} debe tener al menos 2 opciones"
                    )
    # Validación de campos requeridos en configs
    if request.configs:
        required_fields = ['webhook_url', 'email', 'avatar']
        missing_fields = [field for field in required_fields if field not in request.configs] 
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El campo configs debe contener los campos: {', '.join(missing_fields)}"
            )
    
    try:
        # Actualizar la sesión con la configuración proporcionada
        if request.content or request.configs:
            SessionService.update_session_content_and_configs(
                id_session=id_session,
                new_content=request.content,
                new_configs=request.configs,
                session_type=service_type
            )
            logger.info(f"Session {id_session} updated with new configuration")
        
        # Usar servicio para inicializar la sesión en la base de datos
        session_data = SessionService.initiate_session(id_session)
        
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
    2. Actualizar status a 'started'  
    3. Conectar WebSocket e inicializar agente
    4. Manejar comunicación bidireccional
    """
    logger.info(f"🔗 New WebSocket connection for session: {id_session}")
    
    try:
        # Validación usando servicio
        session_data = SessionService.validate_session_for_start(id_session)
        
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
        
        # Marcar sesión como iniciada usando servicio
        SessionService.mark_session_as_started(id_session, session_data)
        
        # Conectar WebSocket e inicializar agente
        await websocket_manager.connect_and_initialize(websocket, id_session, session_data)
        logger.info(f"✅ WebSocket connected and initialized for session: {id_session}")
        
        # Manejar comunicación completa
        await websocket_manager.handle_connection_lifecycle(websocket, id_session)
                    
    except WebSocketDisconnect:
        logger.info(f"🔌 Client disconnected from session: {id_session}")
    except Exception as e:
        logger.error(f"❌ Fatal error in WebSocket {id_session}: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        websocket_manager.disconnect(id_session) 
