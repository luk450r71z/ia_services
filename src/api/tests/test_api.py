import pytest
from fastapi.testclient import TestClient
from fastapi import status
import sys
import os
import base64

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

# Inicializar TestClient - la forma correcta para la versión actualizada
client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.json()
    assert response.json()["message"] == "Welcome to IA Services API"

def test_session_auth_endpoint():
    """Test the authentication endpoint with Basic Auth"""
    # Caso 1: Credenciales válidas
    username = "fabian"
    password = "secure_password"
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {credentials}"
    }
    
    response = client.post("/api/chat/session/auth", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert "id_session" in response.json()
    
    # Caso 2: Credenciales inválidas
    username = "usuario_invalido"
    password = "contraseña_incorrecta"
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {credentials}"
    }
    
    response = client.post("/api/chat/session/auth", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
def test_questionnaire_initiate_endpoint():
    """Test the questionnaire initiation endpoint with proper payload"""
    # Corregir el payload según el modelo InitiateServiceRequest
    payload = {
        "id_session": "test_session",
        "type": "questionnarie",
        "content": {
            "questions": [
                {"id": "q1", "text": "¿Cuál es tu nombre?"}
            ]
        },
        "configs": {
            "max_attempts": 3
        }
    }
    
    response = client.post("/api/chat/questionnarie/initiate", json=payload)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND]

def test_questionnaire_start_endpoint():
    """Test the questionnaire start endpoint with proper payload"""
    # Corregir el payload según el modelo StartServiceRequest
    payload = {
        "id_session": "test_session"
    }
    
    response = client.post("/api/chat/questionnarie/start", json=payload)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND] 