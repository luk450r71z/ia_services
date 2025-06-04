from fastapi import WebSocket
from typing import Dict, Any
import json
import sqlite3
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Maneja las conexiones WebSocket con persistencia en base de datos"""
    
    def __init__(self, db_path: str = "envs/data/session.db"):
        self.active_connections: Dict[str, WebSocket] = {}
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Inicializa la base de datos y crea las tablas si no existen"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Crear tabla de sesiones (compatible con sistema de autenticación)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id_session TEXT PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'active'
                    )
                ''')
                
                # Crear tabla para preguntas y respuestas (solo para conversaciones)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        questions TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions (id_session)
                    )
                ''')
                
                # Crear tabla para almacenar respuestas de usuarios (solo para conversaciones)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_responses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        response TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions (id_session)
                    )
                ''')
                
                conn.commit()
                logger.info("✅ Base de datos inicializada correctamente con todas las tablas")
        except Exception as e:
            logger.error(f"❌ Error al inicializar la base de datos: {str(e)}")
            raise

    def _update_session_status(self, session_id: str, status: str):
        """Actualiza el status de una sesión en la base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO sessions (id_session, status, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (session_id, status))
                conn.commit()
                logger.debug(f"📊 Sesión {session_id} actualizada a status: {status}")
        except Exception as e:
            logger.error(f"❌ Error al actualizar sesión {session_id}: {str(e)}")
            raise

    def save_session_questions(self, session_id: str, questions: list):
        """Guarda las preguntas para una sesión específica"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Eliminar preguntas anteriores para esta sesión (si existen)
                cursor.execute('DELETE FROM conversation_questions WHERE session_id = ?', (session_id,))
                
                # Guardar las nuevas preguntas como JSON
                questions_json = json.dumps(questions, ensure_ascii=False)
                cursor.execute('''
                    INSERT INTO conversation_questions (session_id, questions)
                    VALUES (?, ?)
                ''', (session_id, questions_json))
                
                conn.commit()
                logger.info(f"📋 Guardadas {len(questions)} preguntas para sesión {session_id}")
        except Exception as e:
            logger.error(f"❌ Error al guardar preguntas para sesión {session_id}: {str(e)}")
            raise

    def get_session_questions(self, session_id: str) -> list:
        """Obtiene las preguntas almacenadas para una sesión"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT questions FROM conversation_questions 
                    WHERE session_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (session_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    return json.loads(row[0])
                return []
        except Exception as e:
            logger.error(f"❌ Error al obtener preguntas de sesión {session_id}: {str(e)}")
            return []

    def save_user_response(self, session_id: str, question: str, response: str):
        """Guarda una respuesta de usuario"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversation_responses (session_id, question, response)
                    VALUES (?, ?, ?)
                ''', (session_id, question, response))
                conn.commit()
                logger.debug(f"💬 Respuesta guardada para sesión {session_id}")
        except Exception as e:
            logger.error(f"❌ Error al guardar respuesta para sesión {session_id}: {str(e)}")
            raise

    def get_session_responses(self, session_id: str) -> Dict[str, str]:
        """Obtiene todas las respuestas de una sesión"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT question, response FROM conversation_responses 
                    WHERE session_id = ? 
                    ORDER BY created_at
                ''', (session_id,))
                rows = cursor.fetchall()
                return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"❌ Error al obtener respuestas de sesión {session_id}: {str(e)}")
            return {}

    def session_exists(self, session_id: str) -> bool:
        """Verifica si una sesión fue inicializada previamente"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id_session FROM sessions WHERE id_session = ?', (session_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"❌ Error al verificar sesión {session_id}: {str(e)}")
            return False

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Obtiene información de una sesión específica"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id_session, status, created_at 
                    FROM sessions WHERE id_session = ?
                ''', (session_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "id_session": row[0],
                        "status": row[1], 
                        "created_at": row[2]
                    }
                return {}
        except Exception as e:
            logger.error(f"❌ Error al obtener info de sesión {session_id}: {str(e)}")
            return {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Acepta una nueva conexión WebSocket y actualiza la base de datos"""
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket
            self._update_session_status(session_id, 'active')
            logger.info(f"✅ WebSocket conectado exitosamente: {session_id}")
        except Exception as e:
            logger.error(f"❌ Error al conectar WebSocket {session_id}: {str(e)}")
            raise

    def disconnect(self, session_id: str):
        """Desconecta una sesión WebSocket y actualiza la base de datos"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            self._update_session_status(session_id, 'inactive')
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

    def get_all_sessions_from_db(self):
        """Obtiene todas las sesiones desde la base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id_session, status, created_at 
                    FROM sessions 
                    ORDER BY created_at DESC
                ''')
                return [
                    {
                        "id_session": row[0],
                        "status": row[1], 
                        "created_at": row[2]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"❌ Error al obtener todas las sesiones: {str(e)}")
            return [] 