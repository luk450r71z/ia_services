import logging
from secrets import compare_digest
from typing import Optional, Dict, Any

from auth.db.database import USERS
from auth.db.sqlite_db import create_session_db

logger = logging.getLogger(__name__)

class AuthService:
    """Service for handling authentication and session creation"""
    
    @staticmethod
    def validate_credentials(username: str, password: str) -> bool:
        """
        Validates user credentials
        
        Args:
            username: Username
            password: Password
            
        Returns:
            bool: True if credentials are valid
        """
        return username in USERS and compare_digest(USERS[username], password)
    
    @staticmethod
    def create_user_session(
        session_type: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
        configs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates a new session for an authenticated user
        
        Args:
            session_type: Optional session type
            content: Session content
            configs: Session configurations
            
        Returns:
            Dict with created session information
            
        Raises:
            Exception: If there's an error creating the session
        """
        logger.info("Creating new session")
        
        session = create_session_db(
            type_value=session_type,
            content=content,
            configs=configs
        )
        
        if not session:
            raise Exception("Could not create session in database")
        
        logger.info(f"Session created successfully: {session['id_session']}")
        return session 