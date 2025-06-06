from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import json
from datetime import datetime, timedelta
import logging

# Importar funciones de la base de datos de auth
from auth.db.sqlite_db import get_session_db, update_session_db, get_conversation_responses

# Importar modelos
from .models.schemas import StartServiceRequest, StartServiceResponse, InitiateServiceRequest, InitiateServiceResponse, ServiceUrls, WebSocketServiceResponse

# Importar WebSocket manager
from .websocket_manager import websocket_manager

# Configure logging
logger = logging.getLogger(__name__)

chat_router = APIRouter()

@chat_router.post("/questionnarie/initiate", response_model=InitiateServiceResponse)
async def initiate_questionnarie(request: InitiateServiceRequest):
    """
    Inicializar un cuestionario según el tipo especificado.
    
    Controles:
    - Verificar tiempo de expiración (5 minutos)
    - Verificar status de sesión (debe estar en 'new')
    - Verificar formato JSON
    - Establecer valores
    """
    session_id = request.id_session
    service_type = request.type
    content = request.content
    configs = request.configs
    
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
            # Actualizar status en BD como expired
            update_session_db(
                session_id=session_id,
                type_value=service_type,
                status="expired",
                content=content,
                configs=configs or {}
            )
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Sesión expirada. Máximo 5 minutos desde la creación"
            )
        
        # Verificar status de sesión (debe estar en 'new')
        if session['status'] != 'new':
            logger.warning(f"Sesión en estado inválido: {session_id}, status: {session['status']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La sesión debe estar en estado 'new'"
            )
        
        # Verificar formato JSON del content
        try:
            if not isinstance(content, dict):
                raise ValueError("Content debe ser un objeto JSON válido")
        except Exception as e:
            logger.error(f"Error en formato JSON del content: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato JSON inválido en content"
            )
        
        # Agregar resource_uri al content como endpoint para iniciar la conexión
        enhanced_content = content.copy()
        enhanced_content["resource_uri"] = f"http://localhost:8000/api/chat/questionnarie/start"
        
        # Configuraciones por defecto si no se proporcionan
        enhanced_configs = configs.copy() if configs else {}
        
        # Actualizar la sesión en la base de datos
        updated_session = update_session_db(
            session_id=session_id,
            type_value=service_type,
            status="initiated",
            content=enhanced_content,
            configs=enhanced_configs
        )
        
        if not updated_session:
            logger.error(f"Error al actualizar sesión: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar la sesión"
            )
        
        logger.info(f"Servicio '{service_type}' iniciado exitosamente para sesión: {session_id}")
        
        # Crear respuesta con URLs
        urls = ServiceUrls(
            resource_uri=f"http://localhost:8000/api/chat/questionnarie/start",
            webui="http://localhost:3000/"
        )
        
        return InitiateServiceResponse(
            id_session=session_id,
            urls=urls
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error inesperado al iniciar servicio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@chat_router.post("/questionnarie/start", response_model=WebSocketServiceResponse)
async def start_questionnarie(request: StartServiceRequest):
    """
    Iniciar un cuestionario conversacional.
    
    Controles:
    - Verificar tiempo de expiración (5 minutos)
    - Verificar status de sesión (debe estar en 'initiated')
    - Verificar existencia de preguntas
    - Verificar existencia de objeto JSON
    - Establecer valores
    - Crear WebSocket
    """
    session_id = request.id_session
    service_type = "questionnarie"
    
    logger.info(f"Iniciando servicio conversacional '{service_type}' para sesión: {session_id}")
    
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
            # Actualizar status en BD como expired
            update_session_db(
                session_id=session_id,
                type_value=service_type,
                status="expired",
                content=session.get('content', {}),
                configs=session.get('configs', {})
            )
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Sesión expirada. Máximo 5 minutos desde la creación"
            )
        
        # Verificar status de sesión (debe estar en 'initiated')
        if session['status'] != 'initiated':
            logger.warning(f"Estado de sesión inválido: {session_id}, status: {session['status']}")
            if session['status'] == 'new':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La sesión debe ser inicializada primero con /api/chat/questionnarie/initiate"
                )
            elif session['status'] == 'started':
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El cuestionario ya ha sido iniciado"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Estado de sesión inválido: {session['status']}"
                )
        
        # Verificar que el tipo sea questionnarie
        if session.get('type') != 'questionnarie':
            logger.error(f"Tipo de sesión inválido: {session.get('type')}. Se esperaba 'questionnarie'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta sesión debe ser de tipo 'questionnarie'"
            )
        
        # Verificar existencia de objeto JSON en content
        content = session.get('content')
        if not content or not isinstance(content, dict):
            logger.error(f"Content inválido o faltante en sesión: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La sesión debe tener content válido en formato JSON"
            )
        
        # Configurar agente de cuestionario
        questions = content.get("questions", [])
        if not questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El cuestionario requiere preguntas en el content"
            )
        
        # Agregar configuración del agente al content
        enhanced_content = content.copy()
        enhanced_content.update({
            "agent_class": "QuestionnarieAgent",
            "questions": questions,
            "total_questions": len(questions),
            "current_question": 0,
            "responses": {},
            "conversation_flow": "sequential"
        })
        enhanced_content["websocket_endpoint"] = f"/api/chat/ws/{session_id}"
        enhanced_content["agent_type"] = service_type
        enhanced_content["started_at"] = datetime.utcnow().isoformat()
        
        # Obtener configuraciones existentes
        configs = session.get('configs', {})
        
        # Actualizar la sesión en la base de datos con estado 'started'
        updated_session = update_session_db(
            session_id=session_id,
            type_value=service_type,
            status="started",
            content=enhanced_content,
            configs=configs
        )
        
        if not updated_session:
            logger.error(f"Error al actualizar sesión a estado 'started': {session_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar la sesión"
            )
        
        # Inicializar el agente y preparar el primer mensaje
        welcome_message = None
        try:
            agent_initialized = await websocket_manager.initialize_agent(session_id, updated_session)
            if agent_initialized:
                logger.info(f"Agente inicializado exitosamente para sesión: {session_id}")
                # Obtener el primer mensaje del agente
                welcome_message = websocket_manager.get_welcome_message(session_id)
                if welcome_message:
                    logger.info(f"Primer mensaje del agente preparado para sesión: {session_id}")
            else:
                logger.warning(f"No se pudo inicializar el agente para sesión: {session_id}")
        except Exception as e:
            logger.error(f"Error inicializando agente para sesión {session_id}: {str(e)}")
            # No fallar el endpoint por esto, el agente se puede inicializar cuando se conecte el WebSocket
        
        logger.info(f"Cuestionario con {len(questions)} preguntas iniciado exitosamente para sesión: {session_id}")
        logger.info(f"WebSocket disponible en: /api/chat/ws/{session_id}")
        logger.info(f"Agente listo para recibir conexiones en: ws://localhost:8000/api/chat/ws/{session_id}")
        
        # Crear respuesta simplificada con solo la información del WebSocket
        websocket_response = {
            "id_session": session_id,
            "websocket_endpoint": f"ws://localhost:8000/api/chat/ws/{session_id}",
            "status": "ready",
            "message": "Cuestionario iniciado exitosamente. Conéctate al WebSocket para comenzar.",
        }
        
        if welcome_message:
            websocket_response["welcome_message"] = welcome_message
        
        return WebSocketServiceResponse(**websocket_response)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error inesperado al iniciar servicio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )





@chat_router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Endpoint WebSocket para comunicación en tiempo real con el agente conversacional.
    
         URL: ws://localhost:8000/api/chat/ws/{session_id}
    
    Flujo:
    1. Verificar que la sesión existe y está en estado 'started'
    2. Conectar WebSocket y inicializar agente
    3. Manejar mensajes bidireccionales
    4. Procesar respuestas con QuestionarieRHAgent
    """
    logger.info(f"🔗 Nueva conexión WebSocket solicitada para sesión: {session_id}")
    
    try:
        # Verificar que la sesión existe y está iniciada
        session_data = get_session_db(session_id)
        
        if not session_data:
            logger.warning(f"❌ Intento de conexión WebSocket a sesión inexistente: {session_id}")
            await websocket.close(code=4004, reason="Sesión no encontrada")
            return
        
        if session_data.get('status') != 'started':
            logger.warning(f"❌ Intento de conexión WebSocket a sesión no iniciada: {session_id}, estado: {session_data.get('status')}")
            await websocket.close(code=4003, reason="La sesión debe estar en estado 'started'")
            return
        
        # Obtener el tipo de servicio de la sesión
        service_type = session_data.get('type')
        if not service_type:
            logger.warning(f"❌ Sesión sin tipo definido: {session_id}")
            await websocket.close(code=4001, reason="Sesión sin tipo definido")
            return
        
        # Conectar usando el manager
        await websocket_manager.connect(websocket, session_id)
        logger.info(f"✅ WebSocket conectado exitosamente para {service_type} en sesión: {session_id}")
        
        try:
            while True:
                # Esperar mensaje del cliente
                message_data = await websocket.receive_text()
                logger.debug(f"📨 Mensaje recibido de {session_id}: {message_data[:100]}...")
                
                try:
                    # Parsear mensaje JSON
                    message_json = json.loads(message_data)
                    user_message = message_json.get('content', '').strip()
                    
                    if user_message:
                        # Procesar mensaje con el agente
                        await websocket_manager.handle_user_message(session_id, user_message)
                    else:
                        logger.warning(f"⚠️ Mensaje vacío recibido de sesión: {session_id}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Error parseando JSON de sesión {session_id}: {str(e)}")
                    await websocket_manager.send_message(
                        session_id, 
                        "error", 
                        "Formato de mensaje inválido. Usa JSON: {\"content\": \"tu mensaje\"}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje de sesión {session_id}: {str(e)}")
                    await websocket_manager.send_message(
                        session_id, 
                        "error", 
                        f"Error procesando mensaje: {str(e)}"
                    )
                    
        except WebSocketDisconnect:
            logger.info(f"🔌 Cliente desconectado de sesión: {session_id}")
        except Exception as e:
            logger.error(f"❌ Error en conexión WebSocket de sesión {session_id}: {str(e)}")
        finally:
            # Limpiar conexión
            websocket_manager.disconnect(session_id)
            
    except Exception as e:
        logger.error(f"❌ Error fatal en WebSocket para sesión {session_id}: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Error interno del servidor")
        except:
            pass 
