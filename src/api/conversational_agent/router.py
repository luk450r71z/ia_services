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

# Solo mantener agentes activos en memoria
active_agents: Dict[str, SimpleRRHHAgent] = {}

# Instancia global del manager mejorado
manager = ConnectionManager()

@chat_router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket simplificado integrado con SimpleRRHHAgent
    
    Parámetros:
    - session_id: ID único de la sesión
    """
    await manager.connect(websocket, session_id)
    
    try:
        # Crear agente si no existe
        if session_id not in active_agents:
            logger.info(f"🤖 Creando nuevo agente para sesión {session_id}")
            active_agents[session_id] = SimpleRRHHAgent()
            
            # Enviar mensaje de bienvenida
            welcome_message = active_agents[session_id].start_conversation()
            await manager.send_message(session_id, {
                "type": "agent_response",
                "content": welcome_message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "is_complete": False
            })
        else:
            # AGENTE YA EXISTE - Enviar mensaje de bienvenida almacenado
            logger.info(f"🔄 Reconectando a agente existente: {session_id}")
            agent = active_agents[session_id]
            
            if agent.initialized:
                # Recuperar mensaje de bienvenida almacenado
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
                logger.info(f"📤 Mensaje de bienvenida reenviado para sesión: {session_id}")
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
                
                agent_response = agent.process_user_input(user_input)
                is_complete = agent.is_conversation_complete()
                
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

@chat_router.get("/sessions/active")
async def get_active_sessions():
    """Endpoint para obtener información de sesiones activas"""
    try:
        # Obtener sesiones activas desde la base de datos
        db_sessions = manager.get_active_sessions_from_db()
        
        return {
            "active_sessions": len(db_sessions),
            "active_agents": len(active_agents),
            "active_connections": len(manager.active_connections),
            "sessions": [
                {
                    "session_id": session[0],
                    "created_at": session[1],
                    "status": session[2],
                    "has_agent": session[0] in active_agents,
                    "has_connection": session[0] in manager.active_connections
                }
                for session in db_sessions
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo sesiones activas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@chat_router.delete("/sessions/{session_id}")
async def close_session(session_id: str):
    """Endpoint para cerrar una sesión específica"""
    try:
        closed_agent = False
        closed_connection = False
        
        # Cerrar conexión WebSocket
        if session_id in manager.active_connections:
            manager.disconnect(session_id)
            closed_connection = True
            logger.info(f"🔌 Conexión WebSocket cerrada: {session_id}")
        
        # Cerrar agente
        if session_id in active_agents:
            del active_agents[session_id]
            closed_agent = True
            logger.info(f"🤖 Agente cerrado manualmente: {session_id}")
        
        return {
            "message": f"Sesión {session_id} cerrada exitosamente",
            "closed_agent": closed_agent,
            "closed_connection": closed_connection,
            "db_updated": True
        }
    except Exception as e:
        logger.error(f"❌ Error cerrando sesión {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@chat_router.post("/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    """Endpoint para reiniciar una sesión específica"""
    try:
        if session_id in active_agents:
            active_agents[session_id].reset_conversation()
            logger.info(f"🔄 Sesión reiniciada: {session_id}")
            return {"message": f"Sesión {session_id} reiniciada exitosamente"}
        else:
            return {"message": f"Sesión {session_id} no encontrada"}
    except Exception as e:
        logger.error(f"❌ Error reiniciando sesión {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@chat_router.post("/sessions/{session_id}/start")
async def start_conversation_with_questions(session_id: str, request_data: dict):
    """
    Endpoint para iniciar una conversación con preguntas personalizadas
    
    Body JSON:
    {
        "questions": ["¿Cuál es tu experiencia?", "¿Por qué quieres trabajar aquí?"]
    }
    """
    try:
        questions = request_data.get("questions", [])
        
        if not isinstance(questions, list):
            raise HTTPException(status_code=400, detail="Las preguntas deben ser una lista")
        
        # Crear agente con preguntas personalizadas
        if session_id not in active_agents:
            active_agents[session_id] = SimpleRRHHAgent(questions=questions if questions else None)
            logger.info(f"🤖 Agente creado con {len(questions)} preguntas personalizadas")
            
            # Iniciar conversación y almacenar mensaje de bienvenida
            welcome_message = active_agents[session_id].start_conversation()
            
            # Almacenar mensaje de bienvenida en metadatos para fácil acceso
            active_agents[session_id].state.metadata["welcome_message"] = welcome_message
            
            return {
                "message": "Conversación iniciada exitosamente",
                "session_id": session_id,
                "welcome_message": welcome_message,
                "questions_count": len(questions),
                "has_custom_questions": len(questions) > 0,
                "agent_initialized": active_agents[session_id].initialized
            }
        else:
            # Agente ya existe, obtener estado actual
            agent = active_agents[session_id]
            welcome_message = agent.state.metadata.get("welcome_message", "Agente ya inicializado")
            
            return {
                "message": f"La sesión {session_id} ya existe",
                "session_id": session_id,
                "welcome_message": welcome_message,
                "agent_initialized": agent.initialized,
                "current_question": agent.state.current_question if agent.initialized else None
            }
            
    except Exception as e:
        logger.error(f"❌ Error iniciando conversación {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@chat_router.get("/health")
async def health_check():
    """Endpoint de verificación de salud del servicio"""
    return {
        "status": "healthy",
        "active_agents": len(active_agents),
        "active_connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    } 
