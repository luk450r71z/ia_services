import pytest
import base64
from fastapi import status
import json
import os
import sys
from pathlib import Path
import httpx
import time

# Importar los usuarios de prueba desde la base de datos
from src.api.auth.db.database import USERS

# URL de la API en el contenedor Docker
API_URL = "http://api:8000"

def get_basic_auth_header(username, password):
    """
    Genera el encabezado de autenticación básica para las pruebas.
    """
    auth_str = f"{username}:{password}"
    auth_bytes = auth_str.encode('utf-8')
    auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
    return {"Authorization": f"Basic {auth_b64}"}

def test_auth_endpoint_valid_credentials():
    """
    Prueba de autenticación con credenciales válidas.
    Debe devolver un código 200 y una sesión válida.
    """
    # Tomamos un usuario válido de la base de datos
    username = list(USERS.keys())[0]
    password = USERS[username]
    
    headers = get_basic_auth_header(username, password)
    
    # Esperar a que la API esté disponible
    retries = 5
    while retries > 0:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(f"{API_URL}/api/chat/session/auth", headers=headers)
                break
        except httpx.RequestError:
            retries -= 1
            time.sleep(1)
            if retries == 0:
                pytest.fail("No se pudo conectar a la API después de varios intentos")
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verificar que la respuesta contiene los campos esperados
    data = response.json()
    assert "id_session" in data
    assert "created_at" in data
    assert "status" in data
    assert data["status"] == "active"

def test_auth_endpoint_invalid_credentials():
    """
    Prueba de autenticación con credenciales inválidas.
    Debe devolver un código 401 Unauthorized.
    """
    headers = get_basic_auth_header("invalid_user", "invalid_password")
    
    with httpx.Client(timeout=5.0) as client:
        response = client.post(f"{API_URL}/api/chat/session/auth", headers=headers)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_auth_endpoint_no_credentials():
    """
    Prueba de autenticación sin credenciales.
    Debe devolver un código 401 Unauthorized.
    """
    with httpx.Client(timeout=5.0) as client:
        response = client.post(f"{API_URL}/api/chat/session/auth")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_auth_endpoint_creates_db_file():
    """
    Prueba que la sesión se crea en el archivo de base de datos correcto.
    """
    # Tomamos un usuario válido de la base de datos
    username = list(USERS.keys())[0]
    password = USERS[username]
    
    headers = get_basic_auth_header(username, password)
    
    with httpx.Client(timeout=5.0) as client:
        response = client.post(f"{API_URL}/api/chat/session/auth", headers=headers)
    
    # Verificar que el archivo de base de datos existe
    db_path = Path("/app/envs/data/session.db")
    assert db_path.exists(), "El archivo de base de datos no se creó correctamente" 