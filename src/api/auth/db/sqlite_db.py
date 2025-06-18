import sqlite3
import json
from datetime import datetime
from uuid import UUID, uuid4
import logging
from pathlib import Path
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Método 1: Directorio actual
CWD = Path(os.getcwd())
logger.info(f"Current working directory: {CWD}")

# Método 2: Ruta absoluta explícita
try:
    # Ruta explícita a envs/data
    BASE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
    ROOT_PATH = BASE_PATH
    
    # Navegar hacia arriba hasta encontrar el directorio raíz
    while ROOT_PATH.name != 'ia_services' and ROOT_PATH.parent != ROOT_PATH:
        ROOT_PATH = ROOT_PATH.parent
        
    logger.info(f"Root path: {ROOT_PATH}")
    
    # Directorio de datos
    DATA_DIR = ROOT_PATH / "envs" / "data"
except Exception as e:
    logger.error(f"Error finding root path: {e}")
    # Fallback a la ubicación relativa
    DATA_DIR = CWD.parent.parent.parent.parent / "envs" / "data"

# Asegurar que el directorio exista
DATA_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Data directory: {DATA_DIR}")

# Ruta a la base de datos
DATABASE_PATH = DATA_DIR / "sessions.db"
logger.info(f"Database path: {DATABASE_PATH.absolute()}")

def dict_factory(cursor, row):
    """Convert database row to dictionary"""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

def get_db():
    """Get database connection with row factory"""
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        conn.row_factory = dict_factory
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        raise

def init_db():
    """Initialize database tables - Usa el esquema existente"""
    logger.info(f"Verificando base de datos en {DATABASE_PATH}")
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Verificar si la tabla sessions existe con el esquema correcto
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id_session TEXT PRIMARY KEY,
            type TEXT CHECK(length(type) > 0 AND length(type) <= 50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT CHECK(status IN ('new', 'initiated', 'started', 'ended', 'expired')),
            content JSON DEFAULT '{}',
            configs JSON DEFAULT '{}',
            logs JSON DEFAULT '[]'          
        )
        """)

        conn.commit()
        conn.close()
        logger.info("Base de datos verificada exitosamente")
    except Exception as e:
        logger.error(f"Error al verificar base de datos: {e}")
        raise

def create_session_db(type_value=None, content=None, configs=None):
    """Create a new session in SQLite database usando el esquema completo"""
    logger.info("Creando nueva sesión en base de datos")
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        id_session = str(uuid4())
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convertir content y configs a JSON si se proporcionan
        content_json = json.dumps(content, ensure_ascii=False) if content else '{}'
        configs_json = json.dumps(configs, ensure_ascii=False) if configs else '{}'
        
        logger.info(f"Insertando sesión con ID: {id_session}")
        cursor.execute("""
        INSERT INTO sessions (id_session, type, created_at, updated_at, status, content, configs)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            id_session,
            type_value,  # type proporcionado o None
            created_at,
            created_at,  # updated_at igual a created_at inicialmente
            'new',  # status por defecto
            content_json,  # content como JSON
            configs_json  # configs como JSON
        ))
        conn.commit()

        # Obtener la sesión creada
        cursor.execute("SELECT * FROM sessions WHERE id_session = ?", (id_session,))
        session = cursor.fetchone()
        
        if session:
            # Convertir los timestamps a datetime para consistencia
            session['created_at'] = datetime.strptime(session['created_at'], "%Y-%m-%d %H:%M:%S")
            session['updated_at'] = datetime.strptime(session['updated_at'], "%Y-%m-%d %H:%M:%S")
            # Convertir content y configs de JSON string a dict
            try:
                if session['content'] and session['content'] != '{}':
                    session['content'] = json.loads(session['content'])
                else:
                    session['content'] = None
            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando content JSON para sesión nueva: {e}")
                session['content'] = None
                
            try:
                if session['configs'] and session['configs'] != '{}':
                    session['configs'] = json.loads(session['configs'])
                else:
                    session['configs'] = None
            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando configs JSON para sesión nueva: {e}")
                session['configs'] = None
            logger.info(f"Sesión creada en base de datos: {session}")
            return session
        else:
            logger.error("La sesión fue insertada pero no se pudo recuperar")
            return None

    except sqlite3.Error as e:
        logger.error(f"Error de base de datos al crear sesión: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear sesión: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_session_db(id_session: str):
    """Get a session from SQLite database"""
    logger.info(f"Obteniendo sesión con ID: {id_session}")
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sessions WHERE id_session = ?", (id_session,))
        session = cursor.fetchone()

        if session:
            # Convertir timestamps a datetime
            session['created_at'] = datetime.strptime(session['created_at'], "%Y-%m-%d %H:%M:%S")
            session['updated_at'] = datetime.strptime(session['updated_at'], "%Y-%m-%d %H:%M:%S")
            # Convertir content y configs de JSON string a dict
            try:
                if session['content'] and session['content'] != '{}':
                    session['content'] = json.loads(session['content'])
                else:
                    session['content'] = None
            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando content JSON para sesión {id_session}: {e}")
                session['content'] = None
                
            try:
                if session['configs'] and session['configs'] != '{}':
                    session['configs'] = json.loads(session['configs'])
                else:
                    session['configs'] = None
            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando configs JSON para sesión {id_session}: {e}")
                session['configs'] = None
            logger.info(f"Sesión encontrada: {session}")
        else:
            logger.warning(f"Sesión no encontrada con ID: {id_session}")

        return session

    except sqlite3.Error as e:
        logger.error(f"Error de base de datos al obtener sesión: {e}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener sesión: {e}")
        raise
    finally:
        if conn:
            conn.close()

def update_session_db(id_session: str, type_value: str, status: str, content: dict, configs: dict = None):
    """Update a session in SQLite database"""
    logger.info(f"Actualizando sesión con ID: {id_session}")
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content_json = json.dumps(content, ensure_ascii=False) if content else '{}'
        configs_json = json.dumps(configs, ensure_ascii=False) if configs else '{}'
        
        cursor.execute("""
        UPDATE sessions 
        SET type = ?, status = ?, content = ?, configs = ?, updated_at = ?
        WHERE id_session = ?
        """, (type_value, status, content_json, configs_json, updated_at, id_session))
        
        if cursor.rowcount == 0:
            logger.warning(f"No se encontró sesión con ID: {id_session}")
            return None
            
        conn.commit()

        # Obtener la sesión actualizada
        cursor.execute("SELECT * FROM sessions WHERE id_session = ?", (id_session,))
        session = cursor.fetchone()
        
        if session:
            # Convertir timestamps a datetime
            session['created_at'] = datetime.strptime(session['created_at'], "%Y-%m-%d %H:%M:%S")
            session['updated_at'] = datetime.strptime(session['updated_at'], "%Y-%m-%d %H:%M:%S")
            # Convertir content y configs de JSON string a dict
            try:
                session['content'] = json.loads(session['content']) if session['content'] else None
            except json.JSONDecodeError:
                session['content'] = None
                
            try:
                session['configs'] = json.loads(session['configs']) if session['configs'] else None
            except json.JSONDecodeError:
                session['configs'] = None
            logger.info(f"Sesión actualizada: {session}")
            return session
        else:
            logger.error("Error al recuperar la sesión actualizada")
            return None

    except sqlite3.Error as e:
        logger.error(f"Error de base de datos al actualizar sesión: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado al actualizar sesión: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def save_message_log(log_data: dict):
    """Guarda un log de mensaje en la base de datos"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Convertir metadata y webhook_response a JSON
        metadata_json = json.dumps(log_data.get('metadata', {}), ensure_ascii=False)
        webhook_response_json = json.dumps(log_data.get('webhook_response', {}), ensure_ascii=False)

        cursor.execute("""
        INSERT INTO message_logs (
            id_session, message_type, content, timestamp, status,
            attempt_number, metadata, webhook_sent, webhook_response
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_data['id_session'],
            log_data['message_type'],
            log_data['content'],
            log_data['timestamp'],
            log_data['status'],
            log_data['attempt_number'],
            metadata_json,
            log_data['webhook_sent'],
            webhook_response_json
        ))

        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error guardando log de mensaje: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def update_session_logs(id_session: str, log_data: dict):
    """Actualiza los logs de una sesión"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Obtener logs actuales
        cursor.execute("SELECT logs FROM sessions WHERE id_session = ?", (id_session,))
        result = cursor.fetchone()
        
        if not result:
            raise ValueError(f"Sesión no encontrada: {id_session}")
        
        # Convertir logs actuales a lista
        try:
            current_logs = json.loads(result['logs'] or '[]')
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando logs JSON para sesión {id_session}: {e}")
            current_logs = []
        
        # Si el último log tiene el mismo contenido y tipo, actualizarlo
        if current_logs and current_logs[-1].get('content') == log_data.get('content') and current_logs[-1].get('message_type') == log_data.get('message_type'):
            current_logs[-1] = log_data
        else:
            # Si es un log diferente, agregarlo
            current_logs.append(log_data)
        
        # Actualizar logs en la base de datos
        cursor.execute("""
        UPDATE sessions 
        SET logs = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id_session = ?
        """, (json.dumps(current_logs, ensure_ascii=False), id_session))
        
        conn.commit()
        return len(current_logs)
    except sqlite3.Error as e:
        logger.error(f"Error de SQLite actualizando logs de sesión: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado actualizando logs de sesión: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_session_logs(id_session: str) -> list:
    """Obtiene todos los logs de una sesión"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT logs FROM sessions WHERE id_session = ?", (id_session,))
        result = cursor.fetchone()
        
        if not result:
            return []
            
        try:
            return json.loads(result['logs'] or '[]')
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando logs JSON para sesión {id_session}: {e}")
            return []
    except sqlite3.Error as e:
        logger.error(f"Error de SQLite obteniendo logs de sesión: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado obteniendo logs de sesión: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Initialize database when module is imported
init_db() 