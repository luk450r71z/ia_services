import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulated user database (replace with real DB in production)
USERS = {
    "test_user": "test_password",
    "fabian": "secure_password"
}

def authenticate_user(username: str, password: str):
    """Authenticate a user"""
    if username not in USERS or USERS[username] != password:
        return False
    return True 