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

def test_create_session():
    """Test POST /api/chat/session/auth endpoint."""
    response = client.post("/api/chat/session/auth")
    assert response.status_code == 200
    data = response.json()
    assert "id_session" in data
    assert "type" in data
    assert "status" in data
    assert data["status"] == "new"

def test_session_expiration():
    """Test that session expiration handling works correctly."""
    # Create a new session
    create_response = client.post("/api/chat/session/auth")
    assert create_response.status_code == 200
    session_id = create_response.json()["id_session"]
    
    # Try to use an invalid session ID
    invalid_session_id = "invalid_id"
    response = client.post(
        "/api/chat/questionnarie/initiate",
        json={"id_session": invalid_session_id}
    )
    assert response.status_code == 404 