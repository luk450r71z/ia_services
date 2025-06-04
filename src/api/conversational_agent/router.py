from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict
import json
from datetime import datetime
import logging
import asyncio
from .agents.simple_agent import SimpleRRHHAgent
from .utils.connection_manager import ConnectionManager

# Configure logging
logger = logging.getLogger(__name__)

chat_router = APIRouter()

# Solo mantener agentes activos en memoria (estado conversacional complejo)
active_agents: Dict[str, SimpleRRHHAgent] = {}

# Instancia global del manager mejorado
manager = ConnectionManager()

@chat_router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket simplificado que requiere inicialización previa
    
    Parámetros:
    - session_id: ID único de la sesión (debe estar inicializado previamente)
    """
    logger.info(f"🔌 Intento de conexión WebSocket para sesión: {session_id}")
    
    # VALIDACIÓN: La sesión debe estar inicializada
    session_exists = manager.session_exists(session_id)
    logger.info(f"🔍 Verificando sesión {session_id} - Existe: {session_exists}")
    
    if not session_exists:
        logger.warning(f"❌ Sesión {session_id} no encontrada en base de datos")
        await websocket.accept()
        await websocket.send_text(json.dumps({
            "type": "error",
            "content": "Sesión no inicializada. Llama primero al endpoint /sessions/{session_id}/start",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "error_code": "SESSION_NOT_INITIALIZED"
        }))
        await websocket.close()
        return
    
    logger.info(f"✅ Sesión {session_id} verificada, procediendo a conectar WebSocket")
    await manager.connect(websocket, session_id)
    
    try:
        # Crear agente si no existe en memoria
        if session_id not in active_agents:
            logger.info(f"🤖 Recreando agente para sesión existente {session_id}")
            
            # Recuperar las preguntas almacenadas en la base de datos
            stored_questions = manager.get_session_questions(session_id)
            logger.info(f"📋 Preguntas recuperadas: {len(stored_questions)} preguntas")
            
            active_agents[session_id] = SimpleRRHHAgent(questions=stored_questions)
            
            # Inicializar con estado base
            welcome_message = active_agents[session_id].start_conversation()
            await manager.send_message(session_id, {
                "type": "agent_response",
                "content": welcome_message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "is_complete": False,
                "reconnected": True
            })
            logger.info(f"📤 Agente recreado y mensaje enviado para sesión: {session_id}")
        else:
            # AGENTE YA EXISTE EN MEMORIA - Enviar estado actual
            logger.info(f"🔄 Reconectando a agente existente: {session_id}")
            agent = active_agents[session_id]
            
            if agent.initialized:
                # Recuperar mensaje de bienvenida o estado actual
                welcome_message = agent.state.metadata.get("welcome_message", "¡Hola! Continuemos con la conversación.")
                
                # Si hay una pregunta actual pendiente, agregarla
                if agent.state.current_question and agent.state.current_question not in welcome_message:
                    welcome_message += f"\n\nPregunta actual:\n{agent.state.current_question}"
                
                await manager.send_message(session_id, {
                    "type": "agent_response",
                    "content": welcome_message,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "is_complete": agent.is_conversation_complete(),
                    "reconnected": True
                })
                logger.info(f"📤 Estado actual reenviado para sesión: {session_id}")
            else:
                # Si el agente no está inicializado, inicializarlo ahora
                welcome_message = agent.start_conversation()
                agent.state.metadata["welcome_message"] = welcome_message
                
                await manager.send_message(session_id, {
                    "type": "agent_response",
                    "content": welcome_message,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "is_complete": False,
                    "late_initialization": True
                })
                logger.info(f"📤 Agente inicializado tardíamente para sesión: {session_id}")
        
        # LOOP PRINCIPAL DE CONVERSACIÓN
        while True:
            try:
                # Recibir mensaje del usuario con timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)  # 5 minutos timeout
                message_data = json.loads(data)
                
                # Validar estructura del mensaje
                if not isinstance(message_data, dict) or 'content' not in message_data:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "content": "Formato de mensaje inválido. Se requiere un objeto con 'content'",
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    continue
                
                user_input = message_data.get('content', '').strip()
                
                # Validar que el mensaje no esté vacío
                if not user_input:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "content": "El mensaje no puede estar vacío",
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    continue
                
                logger.info(f"💬 Usuario ({session_id}): {user_input[:100]}...")
                
                # Mostrar indicador de escritura
                await manager.send_typing_indicator(session_id, True)
                
                # PROCESAR CON EL AGENTE
                agent = active_agents[session_id]
                
                # Simular tiempo de procesamiento
                await asyncio.sleep(0.5)
                
                # Guardar estado anterior para detectar respuestas nuevas
                previous_responses = dict(agent.state.user_responses)
                
                agent_response = agent.process_user_input(user_input)
                is_complete = agent.is_conversation_complete()
                
                # DETECTAR SI SE ACEPTÓ UNA NUEVA RESPUESTA Y GUARDAR EN BD
                current_responses = agent.state.user_responses
                new_responses = {q: r for q, r in current_responses.items() if q not in previous_responses}
                
                if new_responses:
                    # Se aceptó una nueva respuesta, guardar en base de datos
                    for question, response in new_responses.items():
                        try:
                            manager.save_user_response(session_id, question, response)
                            logger.info(f"💾 Respuesta guardada en BD: {session_id} - {question[:50]}...")
                        except Exception as e:
                            logger.error(f"❌ Error guardando respuesta en BD: {str(e)}")
                
                # Quitar indicador de escritura
                await manager.send_typing_indicator(session_id, False)
                
                # Preparar respuesta
                response = {
                    "type": "agent_response", 
                    "content": agent_response,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "is_complete": is_complete
                }
                
                # Si la conversación está completa, agregar resumen
                if is_complete:
                    response["summary"] = agent.get_conversation_summary()
                    logger.info(f"✅ Conversación completada para sesión: {session_id}")
                
                await manager.send_message(session_id, response)
                
                # Si la conversación está completa, cerrar la conexión limpiamente
                if is_complete:
                    await asyncio.sleep(2)  # Dar tiempo para que el cliente procese
                    break
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout en sesión {session_id}")
                await manager.send_message(session_id, {
                    "type": "timeout",
                    "content": "La sesión ha expirado por inactividad",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                })
                break
                
            except json.JSONDecodeError:
                logger.error(f"❌ JSON inválido recibido en sesión {session_id}")
                await manager.send_message(session_id, {
                    "type": "error",
                    "content": "Formato JSON inválido",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                })
                continue
                
    except WebSocketDisconnect:
        logger.info(f"🔌 Cliente desconectado: {session_id}")
    except Exception as e:
        logger.error(f"❌ Error inesperado en sesión {session_id}: {str(e)}")
        try:
            await manager.send_message(session_id, {
                "type": "error",
                "content": f"Error interno del servidor: {str(e)}",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass  # Si no se puede enviar el error, no hacer nada
    finally:
        # Limpieza final
        manager.disconnect(session_id)
        if session_id in active_agents:
            del active_agents[session_id]
            logger.info(f"🤖 Agente limpiado: {session_id}")

@chat_router.post("/sessions/{session_id}/start")
async def start_conversation_with_questions(session_id: str, request_data: dict):
    """
    Inicializa una nueva sesión de conversación con preguntas específicas
    
    Body esperado:
    {
        "questions": ["¿pregunta1?", "¿pregunta2?", ...]
    }
    """
    try:
        logger.info(f"🚀 Iniciando POST /sessions/{session_id}/start")
        
        # Validar que existan preguntas
        questions = request_data.get("questions", [])
        if not questions or not isinstance(questions, list):
            raise HTTPException(status_code=400, detail="Se requiere una lista de 'questions' no vacía")
        
        logger.info(f"📝 Preguntas recibidas: {len(questions)} preguntas")
        
        # Registrar la sesión en base de datos
        logger.info(f"💾 Guardando sesión {session_id} en base de datos...")
        try:
            manager._update_session_status(session_id, 'active')
            manager.save_session_questions(session_id, questions)
        except Exception as db_error:
            logger.error(f"❌ ERROR EN BASE DE DATOS: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"Error al guardar sesión en base de datos: {str(db_error)}")
        
        # Verificar que se guardó correctamente
        session_exists = manager.session_exists(session_id)
        logger.info(f"✅ Verificación inmediata - Sesión existe: {session_exists}")
        
        if not session_exists:
            logger.error(f"❌ PROBLEMA: La sesión {session_id} no se guardó correctamente")
            raise HTTPException(status_code=500, detail="Error al guardar la sesión")
        
        # Crear agente en memoria con las preguntas proporcionadas
        if session_id not in active_agents:
            active_agents[session_id] = SimpleRRHHAgent(questions=questions)
            
        agent = active_agents[session_id]
        
        # Las preguntas ya están configuradas en el constructor
        
        logger.info(f"✅ Sesión {session_id} inicializada con {len(questions)} preguntas")
        
        return {
            "message": f"Sesión {session_id} inicializada correctamente",
            "session_id": session_id,
            "questions_count": len(questions),
            "status": "ready",
            "next_step": f"Conectar al WebSocket: /ws/{session_id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error al inicializar sesión {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@chat_router.get("/health")
async def health_check():
    """Endpoint de salud del servicio"""
    try:
        # Obtener información básica
        all_sessions = manager.get_all_sessions_from_db()
        active_sessions = [s for s in all_sessions if s['status'] == 'active']
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "total_sessions": len(all_sessions),
            "active_sessions": len(active_sessions),
            "active_agents_in_memory": len(active_agents),
            "active_websocket_connections": len(manager.active_connections)
        }
    except Exception as e:
        logger.error(f"❌ Error en health check: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}") 
