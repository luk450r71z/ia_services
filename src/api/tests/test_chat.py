import pytest
import sys
import importlib
from fastapi.testclient import TestClient
from main import app

# Enfoque flexible para diferentes versiones de FastAPI
try:
    # Intenta primero el enfoque moderno
    client = TestClient(transport=app)
except TypeError:
    try:
        # Intenta el enfoque clásico
        client = TestClient(app)
    except TypeError:
        # Último recurso: inspecciona los parámetros de TestClient
        import inspect
        sig = inspect.signature(TestClient.__init__)
        if 'app' in sig.parameters:
            client = TestClient(app=app)
        elif 'application' in sig.parameters:
            client = TestClient(application=app)
        else:
            raise ValueError("No se pudo determinar cómo inicializar TestClient")

def test_questionnaire_flow():
    """Test the complete questionnaire flow."""
    # 1. Create a new session
    session_response = client.post("/api/chat/session/auth")
    assert session_response.status_code == 200
    session_data = session_response.json()
    session_id = session_data["id_session"]
    
    # 2. Initiate the questionnaire
    initiate_response = client.post(
        "/api/chat/questionnarie/initiate",
        json={"id_session": session_id}
    )
    assert initiate_response.status_code == 200
    initiate_data = initiate_response.json()
    assert "message" in initiate_data
    assert initiate_data["status"] == "initiated"
    
    # 3. Start the questionnaire
    start_response = client.post(
        "/api/chat/questionnarie/start",
        json={"id_session": session_id}
    )
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert "question" in start_data
    assert start_data["status"] == "started"
    
def test_invalid_session_for_questionnaire():
    """Test starting questionnaire with invalid session."""
    invalid_session_id = "non_existent_session"
    
    response = client.post(
        "/api/chat/questionnarie/start",
        json={"id_session": invalid_session_id}
    )
    assert response.status_code == 404 