from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Any, Optional
import json
import uuid
from datetime import datetime
import logging
import asyncio

# IMPORTAR TU AGENTE
from .agents.simple_agent import SimpleRRHHAgent

from .models.schemas import WebSocketMessage, ChatSession

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Diccionario para sesiones activas (en producción usar Redis o DB)
active_sessions: Dict[str, ChatSession] = {}
active_agents: Dict[str, SimpleRRHHAgent] = {}

class ConnectionManager:
    """Maneja las conexiones WebSocket de forma avanzada"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Acepta una nueva conexión WebSocket"""
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket
            logger.info(f"✅ WebSocket conectado exitosamente: {session_id}")
        except Exception as e:
            logger.error(f"❌ Error al conectar WebSocket {session_id}: {str(e)}")
            raise

    def disconnect(self, session_id: str):
        """Desconecta una sesión WebSocket"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"🔌 WebSocket desconectado: {session_id}")

    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Envía un mensaje a través del WebSocket"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
                logger.debug(f"📤 Mensaje enviado a {session_id}: {message.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"❌ Error enviando mensaje a {session_id}: {str(e)}")
                # Si hay error enviando, desconectar la sesión
                self.disconnect(session_id)
        else:
            logger.warning(f"⚠️ Intento de enviar mensaje a sesión inexistente: {session_id}")

    async def send_typing_indicator(self, session_id: str, is_typing: bool = True):
        """Envía indicador de que el agente está escribiendo"""
        await self.send_message(session_id, {
            "type": "typing_indicator",
            "is_typing": is_typing,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })

# Instancia global del manager
manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket simplificado integrado con SimpleRRHHAgent
    
    Parámetros:
    - session_id: ID único de la sesión
    """
    await manager.connect(websocket, session_id)
    
    try:
        # Crear sesión si no existe
        if session_id not in active_sessions:
            active_sessions[session_id] = ChatSession(
                session_id=session_id,
                created_at=datetime.now()
            )
            logger.info(f"🆕 Nueva sesión creada: {session_id}")
        
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
        if session_id in active_sessions:
            del active_sessions[session_id]
            logger.info(f"🧹 Sesión limpiada: {session_id}")
        if session_id in active_agents:
            del active_agents[session_id]
            logger.info(f"🤖 Agente limpiado: {session_id}")

@router.get("/sessions/active")
async def get_active_sessions():
    """Endpoint para obtener información de sesiones activas"""
    try:
        return {
            "active_sessions": len(active_sessions),
            "active_agents": len(active_agents),
            "sessions": [
                {
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "is_active": session.is_active,
                    "has_agent": session.session_id in active_agents
                }
                for session in active_sessions.values()
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo sesiones activas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/sessions/{session_id}")
async def close_session(session_id: str):
    """Endpoint para cerrar una sesión específica"""
    try:
        closed_session = False
        closed_agent = False
        
        if session_id in active_sessions:
            manager.disconnect(session_id)
            del active_sessions[session_id]
            closed_session = True
            logger.info(f"🗑️ Sesión cerrada manualmente: {session_id}")
        
        if session_id in active_agents:
            del active_agents[session_id]
            closed_agent = True
            logger.info(f"🤖 Agente cerrado manualmente: {session_id}")
        
        if closed_session or closed_agent:
            return {
                "message": f"Sesión {session_id} cerrada exitosamente",
                "closed_session": closed_session,
                "closed_agent": closed_agent
            }
        else:
            return {
                "message": f"Sesión {session_id} no encontrada",
                "closed_session": False,
                "closed_agent": False
            }
    except Exception as e:
        logger.error(f"❌ Error cerrando sesión {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/sessions/{session_id}/reset")
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

@router.post("/sessions/{session_id}/start")
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
        
        # Crear sesión si no existe
        if session_id not in active_sessions:
            active_sessions[session_id] = ChatSession(
                session_id=session_id,
                created_at=datetime.now()
            )
            logger.info(f"🆕 Nueva sesión creada via POST: {session_id}")
        
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

@router.get("/health")
async def health_check():
    """Endpoint de verificación de salud del servicio"""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "active_agents": len(active_agents),
        "timestamp": datetime.now().isoformat()
    } 
