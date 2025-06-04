import logging
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from secrets import compare_digest

from auth.db.database import USERS
from auth.db.sqlite_db import create_session_db, get_session_db
from auth.models.schemas import SessionResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Authentication router
auth_router = APIRouter(tags=["Authentication"])

# HTTP Basic Auth security
security = HTTPBasic()

@auth_router.post("/chat/session/auth", response_model=SessionResponse)
async def create_session(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Create a new session using HTTP Basic Auth.
    Validates username and password against the USERS database.
    """
    username = credentials.username
    password = credentials.password

    logger.info(f"Authentication attempt for user: {username}")

    # Validate credentials against the USERS dictionary
    if username not in USERS or not compare_digest(USERS[username], password):
        logger.warning(f"Invalid authentication attempt for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    logger.info(f"User {username} authenticated successfully")
    
    # Create a new session in the database
    try:
        session = create_session_db()
        if not session:
            logger.error("Failed to create session - no session returned")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )
        
        logger.info(f"Created new session for user {username}: {session['id_session']}")
        return SessionResponse(**session)
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        ) 