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
        """Inicializa la base de datos y crea la tabla si no existe"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id_session TEXT PRIMARY KEY,
                        status TEXT NOT NULL DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
                logger.info("✅ Base de datos inicializada correctamente")
        except Exception as e:
            logger.error(f"❌ Error al inicializar la base de datos: {str(e)}")
            raise

    def _update_session_status(self, session_id: str, status: str):
        """Actualiza el status de una sesión en la base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO sessions (id_session, status, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (session_id, status))
                conn.commit()
                logger.debug(f"📊 Sesión {session_id} actualizada a status: {status}")
        except Exception as e:
            logger.error(f"❌ Error al actualizar sesión {session_id}: {str(e)}")

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

    def get_active_sessions_from_db(self):
        """Obtiene todas las sesiones activas desde la base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id_session, created_at, status 
                    FROM sessions 
                    WHERE status = 'active'
                    ORDER BY created_at DESC
                ''')
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Error al obtener sesiones activas: {str(e)}")
            return [] 