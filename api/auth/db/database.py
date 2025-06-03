from uuid import UUID
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory database (replace with real DB in production)
AI_SERVICES = [
    {
        "id_service": UUID("3f91e6c2-1d43-4a77-9c17-6ab872a4b2db"),
        "name_service": "chatbot-interview",
        "auth_required": True,
        "auth_type": "jwt",
        "data": {
            "questions": []
        }
    }
]

# Simulated user database (replace with real DB in production)
USERS = {
    "test_user": "test_password",
    "fabian": "secure_password"
}

# Simulated sessions database (replace with real DB in production)
SESSIONS = {}


def get_all_services():
    """Get all AI services"""
    logger.info(f"Returning all services: {AI_SERVICES}")
    return AI_SERVICES


def get_service_by_id(service_id: UUID):
    """Get a service by ID"""
    logger.info(f"Looking for service with ID: {service_id}, Type: {type(service_id)}")
    logger.info(f"Available services: {AI_SERVICES}")
    
    service = next((s for s in AI_SERVICES if s["id_service"] == service_id), None)
    logger.info(f"Found service: {service}")
    return service


def authenticate_user(username: str, password: str):
    """Authenticate a user"""
    if username not in USERS or USERS[username] != password:
        return False
    return True


def create_session(session_id: UUID, service_id: UUID, client_id: str, resource_uri: str, data: dict = None):
    """Create a new service session"""
    session = {
        "id_session": session_id,
        "id_service": service_id,
        "resource_uri": resource_uri,
        "client_id": client_id,
        "data": data or {},
        "created_at": datetime.utcnow(),
        "status": "active"
    }
    SESSIONS[str(session_id)] = session
    logger.info(f"Created new session: {session}")
    return session


def get_session(session_id: UUID):
    """Get a session by ID"""
    return SESSIONS.get(str(session_id))


def update_session_data(session_id: UUID, data: dict):
    """Update session data"""
    if str(session_id) in SESSIONS:
        SESSIONS[str(session_id)]["data"].update(data)
        return SESSIONS[str(session_id)]
    return None 