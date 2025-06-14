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
DATABASE_PATH = DATA_DIR / "session.db"
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
    """Initialize database tables"""
    logger.info(f"Initializing database at {DATABASE_PATH}")
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Create sessions table with simplified structure
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id_session TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
        """)

        conn.commit()
        conn.close()
        logger.info("Session database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def create_session_db():
    """Create a new session in SQLite database"""
    logger.info("Creating new session in database")
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        session_id = str(uuid4())
        
        logger.info(f"Inserting session with ID: {session_id}")
        cursor.execute("""
        INSERT INTO sessions (id_session, created_at, status)
        VALUES (?, ?, ?)
        """, (
            session_id,
            datetime.utcnow().isoformat(),
            'active'
        ))
        conn.commit()

        # Fetch the created session
        cursor.execute("SELECT * FROM sessions WHERE id_session = ?", (session_id,))
        session = cursor.fetchone()
        
        if session:
            session['created_at'] = datetime.fromisoformat(session['created_at'])
            logger.info(f"Created new session in database: {session}")
            return session
        else:
            logger.error("Session was inserted but could not be retrieved")
            return None

    except sqlite3.Error as e:
        logger.error(f"Database error creating session: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating session: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_session_db(session_id: str):
    """Get a session from SQLite database"""
    logger.info(f"Getting session with ID: {session_id}")
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sessions WHERE id_session = ?", (session_id,))
        session = cursor.fetchone()

        if session:
            session['created_at'] = datetime.fromisoformat(session['created_at'])
            logger.info(f"Found session: {session}")
        else:
            logger.warning(f"Session not found with ID: {session_id}")

        return session

    except sqlite3.Error as e:
        logger.error(f"Database error getting session: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting session: {e}")
        raise
    finally:
        if conn:
            conn.close()

# Initialize database when module is imported
init_db() 