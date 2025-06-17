import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulated user database (replace with real DB in production)
USERS = {
    "test_user": "test_password",
    "fabian": "secure_password"
} 