import pytest
from fastapi.testclient import TestClient
import base64

def test_auth_success(test_client, auth_headers):
    """Test successful authentication"""
    response = test_client.post("/api/chat/session/auth", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "id_session" in data
    assert isinstance(data["id_session"], str)

def test_auth_invalid_credentials(test_client):
    """Test authentication with invalid credentials"""
    invalid_credentials = base64.b64encode(b"invalid:password").decode()
    headers = {"Authorization": f"Basic {invalid_credentials}"}
    response = test_client.post("/api/chat/session/auth", headers=headers)
    assert response.status_code == 401
    assert "Invalid authentication credentials" in response.json()["detail"]

def test_auth_missing_credentials(test_client):
    """Test authentication without credentials"""
    response = test_client.post("/api/chat/session/auth")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

def test_auth_malformed_credentials(test_client):
    """Test authentication with malformed credentials"""
    headers = {"Authorization": "Basic invalid_base64"}
    response = test_client.post("/api/chat/session/auth", headers=headers)
    assert response.status_code == 401
    assert "Invalid authentication credentials" in response.json()["detail"] 