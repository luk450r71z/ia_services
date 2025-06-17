import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
from pathlib import Path
import asyncio
import json
from datetime import datetime, timedelta

# Add src directory to Python path
src_path = Path(__file__).parent.parent.parent
sys.path.append(str(src_path))

from api.main import app
from api.auth.db.sqlite_db import init_db, get_db
from api.auth.db.database import USERS

# Test database path
TEST_DB_PATH = Path("envs/data/test_sessions.db")

@pytest.fixture(scope="session")
def test_db():
    """Create a test database and initialize it"""
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    
    # Initialize test database
    os.environ["DATABASE_PATH"] = str(TEST_DB_PATH)
    init_db()
    
    yield TEST_DB_PATH
    
    # Cleanup
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

@pytest.fixture
def test_client(test_db):
    """Create a test client using the test database"""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def auth_headers():
    """Create authentication headers for test user"""
    import base64
    credentials = base64.b64encode(b"test_user:test_password").decode()
    return {"Authorization": f"Basic {credentials}"}

@pytest.fixture
def valid_session_id(test_client, auth_headers):
    """Create a valid session for testing"""
    response = test_client.post("/api/chat/session/auth", headers=auth_headers)
    assert response.status_code == 200
    return response.json()["id_session"]

@pytest.fixture
def valid_questionnaire_content():
    """Create valid questionnaire content for testing"""
    return {
        "questions": [
            {
                "text": "What is your name?",
                "answerType": "text"
            },
            {
                "text": "What is your age?",
                "answerType": "number"
            }
        ],
        "client_name": "Test Client",
        "welcome_message": "Welcome to the test questionnaire!"
    }

@pytest.fixture
def valid_questionnaire_configs():
    """Create valid questionnaire configuration for testing"""
    return {
        "webhook_url": "http://test.webhook.url",
        "emails": ["test@example.com"],
        "avatar": {
            "show": True,
            "url": "http://test.avatar.url",
            "name": "Test Bot"
        }
    }

@pytest.fixture
def websocket_url(valid_session_id):
    """Create a valid WebSocket URL for testing"""
    return f"ws://testserver/api/chat/questionnaire/start/{valid_session_id}"

@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close() 