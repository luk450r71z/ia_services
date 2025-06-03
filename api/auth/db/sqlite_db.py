import sqlite3
import json
from datetime import datetime
from uuid import UUID
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Ensure the data directory exists in envs
DATA_DIR = Path("envs/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
DATABASE_PATH = DATA_DIR / "sessions.db"

def dict_factory(cursor, row):
    """Convert database row to dictionary"""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

def get_db():
    """Get database connection with row factory"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = dict_factory
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()

    # Create sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id_session TEXT PRIMARY KEY,
        id_service TEXT NOT NULL,
        client_id TEXT NOT NULL,
        resource_uri TEXT NOT NULL,
        data JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'active'
    )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def create_session_db(session_id: UUID, service_id: UUID, client_id: str, resource_uri: str, data: dict = None):
    """Create a new session in SQLite database"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO sessions (id_session, id_service, client_id, resource_uri, data, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(session_id),
            str(service_id),
            client_id,
            resource_uri,
            json.dumps(data or {}),
            datetime.utcnow().isoformat(),
            'active'
        ))
        conn.commit()

        # Fetch the created session
        cursor.execute("SELECT * FROM sessions WHERE id_session = ?", (str(session_id),))
        session = cursor.fetchone()
        
        if session:
            session['data'] = json.loads(session['data'])
            session['id_session'] = UUID(session['id_session'])
            session['id_service'] = UUID(session['id_service'])
            session['created_at'] = datetime.fromisoformat(session['created_at'])

        logger.info(f"Created new session in database: {session}")
        return session

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def get_session_db(session_id: UUID):
    """Get a session from SQLite database"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM sessions WHERE id_session = ?", (str(session_id),))
        session = cursor.fetchone()

        if session:
            session['data'] = json.loads(session['data'])
            session['id_session'] = UUID(session['id_session'])
            session['id_service'] = UUID(session['id_service'])
            session['created_at'] = datetime.fromisoformat(session['created_at'])

        return session

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def update_session_data_db(session_id: UUID, data: dict):
    """Update session data in SQLite database"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Get current data
        cursor.execute("SELECT data FROM sessions WHERE id_session = ?", (str(session_id),))
        current = cursor.fetchone()
        
        if current:
            current_data = json.loads(current['data'])
            current_data.update(data)
            
            # Update the session
            cursor.execute("""
            UPDATE sessions 
            SET data = ?
            WHERE id_session = ?
            """, (json.dumps(current_data), str(session_id)))
            
            conn.commit()
            
            # Return updated session
            return get_session_db(session_id)
            
        return None

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

# Initialize database when module is imported
init_db() 