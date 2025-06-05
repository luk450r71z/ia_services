from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any
import json
from datetime import datetime, timedelta
import logging

# Importar funciones de la base de datos de auth
from auth.db.sqlite_db import get_session_db, update_session_db

# Importar WebSocket manager
from .websocket_manager import websocket_manager

# Configure logging
logger = logging.getLogger(__name__)

chat_router = APIRouter()

class StartServiceRequest(BaseModel):
    """Request model for starting service"""
    id_session: str
    type: str

class StartServiceResponse(BaseModel):
    """Response model for service start"""
    id_session: str
    type: str
    created_at: datetime
    updated_at: datetime
    state: str
    status: int
    metadata: Dict[str, Any]

@chat_router.post("/service/start", response_model=StartServiceResponse)
async def start_service(request: StartServiceRequest):
    """
    Iniciar un servicio conversacional.
    
    Controles:
    - Verificar tiempo de expiración (5 minutos)
    - Verificar status de sesión
    - Verificar estado (que no esté inicializada)
    - Verificar existencia de type
    - Verificar existencia de objeto JSON
    - Establecer valores
    - Enrutar agente por tipo
    - Crear WebSocket
    """
    session_id = request.id_session
    service_type = request.type
    
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
        
        # Verificar estado (debe estar 'initiated', no 'new' ni 'started')
        if session['state'] not in ['initiated']:
            logger.warning(f"Estado de sesión inválido: {session_id}, estado: {session['state']}")
            if session['state'] == 'new':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La sesión debe ser inicializada primero con /api/chat/service/initiate"
                )
            elif session['state'] == 'started':
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El servicio ya ha sido iniciado"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Estado de sesión inválido: {session['state']}"
                )
        
        # Verificar existencia de type
        if not session.get('type'):
            logger.error(f"Sesión sin tipo definido: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La sesión debe tener un tipo definido"
            )
        
        # Verificar que el type coincida
        if session['type'] != service_type:
            logger.warning(f"Tipo de servicio no coincide: sesión={session['type']}, solicitado={service_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de servicio no coincide. Esperado: {session['type']}, recibido: {service_type}"
            )
        
        # Verificar existencia de objeto JSON en metadata
        metadata = session.get('metadata')
        if not metadata or not isinstance(metadata, dict):
            logger.error(f"Metadata inválido o faltante en sesión: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La sesión debe tener metadata válido en formato JSON"
            )
        
        # Enrutar agente por tipo
        agent_config = _route_agent_by_type(service_type, metadata)
        
        # Agregar configuración del agente al metadata
        enhanced_metadata = metadata.copy()
        enhanced_metadata.update(agent_config)
        enhanced_metadata["websocket_endpoint"] = f"/api/chat/ws/{session_id}"
        enhanced_metadata["agent_type"] = service_type
        enhanced_metadata["started_at"] = datetime.utcnow().isoformat()
        
        # Actualizar la sesión en la base de datos con estado 'started'
        updated_session = update_session_db(
            session_id=session_id,
            type_value=service_type,
            state="started",
            metadata=enhanced_metadata
        )
        
        if not updated_session:
            logger.error(f"Error al actualizar sesión a estado 'started': {session_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar la sesión"
            )
        
        logger.info(f"Servicio '{service_type}' iniciado exitosamente para sesión: {session_id}")
        logger.info(f"WebSocket disponible en: /api/chat/ws/{session_id}")
        
        return StartServiceResponse(**updated_session)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error inesperado al iniciar servicio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

def _route_agent_by_type(service_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrutar y configurar agente según el tipo de servicio.
    
    Args:
        service_type: Tipo de servicio ('questionary' o 'help_desk')
        metadata: Metadata existente de la sesión
    
    Returns:
        Dict con configuración específica del agente
    """
    agent_config = {}
    
    if service_type == "questionary":
        # Configuración para agente de cuestionario
        questions = metadata.get("questions", [])
        if not questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tipo 'questionary' requiere preguntas en el metadata"
            )
        
        agent_config = {
            "agent_class": "QuestionaryAgent",
            "questions": questions,
            "total_questions": len(questions),
            "current_question": 0,
            "responses": {},
            "conversation_flow": "sequential"
        }
        
        logger.info(f"Configurado agente de cuestionario con {len(questions)} preguntas")
        
    elif service_type == "help_desk":
        # Configuración para agente de help desk
        categories = metadata.get("categories", ["general", "technical", "billing"])
        knowledge_base = metadata.get("knowledge_base", {})
        
        agent_config = {
            "agent_class": "HelpDeskAgent",
            "categories": categories,
            "knowledge_base": knowledge_base,
            "conversation_flow": "free_form",
            "escalation_enabled": True
        }
        
        logger.info(f"Configurado agente de help desk con categorías: {categories}")
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de servicio no soportado: {service_type}"
        )
    
    return agent_config

@chat_router.get("/health")
async def health_check():
    """Endpoint de salud del servicio conversacional"""
    try:
        return {
            "status": "healthy",
            "service": "conversational_agent",
            "timestamp": datetime.now().isoformat(),
            "endpoints": [
                "/api/chat/service/start"
            ]
        }
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@chat_router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Endpoint WebSocket para comunicación en tiempo real con el agente conversacional.
    
         URL: ws://localhost:8000/ws/chat/{service_type}/{session_id}
    
    Flujo:
    1. Verificar que la sesión existe y está en estado 'started'
    2. Conectar WebSocket y inicializar agente
    3. Manejar mensajes bidireccionales
    4. Procesar respuestas con SimpleRRHHAgent
    """
    logger.info(f"🔗 Nueva conexión WebSocket solicitada para sesión: {session_id}")
    
    try:
        # Verificar que la sesión existe y está iniciada
        session_data = get_session_db(session_id)
        
        if not session_data:
            logger.warning(f"❌ Intento de conexión WebSocket a sesión inexistente: {session_id}")
            await websocket.close(code=4004, reason="Sesión no encontrada")
            return
        
        if session_data.get('state') != 'started':
            logger.warning(f"❌ Intento de conexión WebSocket a sesión no iniciada: {session_id}, estado: {session_data.get('state')}")
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
