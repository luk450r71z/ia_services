import pytest
from fastapi.testclient import TestClient
import json
from fastapi.websockets import WebSocketDisconnect
import base64

def test_initiate_questionnaire_success(test_client, auth_headers, valid_session_id, valid_questionnaire_content, valid_questionnaire_configs):
    """Test successful questionnaire initiation"""
    response = test_client.post(
        f"/api/chat/questionnaire/initiate",
        headers=auth_headers,
        json={
            "id_session": valid_session_id,
            "content": valid_questionnaire_content,
            "configs": valid_questionnaire_configs
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id_session" in data
    assert "urls" in data
    assert "websocket_url" in data["urls"]
    assert "webui_url" in data["urls"]
    assert valid_session_id in data["urls"]["websocket_url"]
    assert valid_session_id in data["urls"]["webui_url"]

def test_initiate_questionnaire_invalid_session(test_client, auth_headers):
    """Test questionnaire initiation with invalid session"""
    response = test_client.post(
        f"/api/chat/questionnaire/initiate",
        headers=auth_headers,
        json={
            "id_session": "invalid_session_id",
            "content": {},
            "configs": {}
        }
    )
    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]

def test_initiate_questionnaire_invalid_content(test_client, auth_headers, valid_session_id):
    """Test questionnaire initiation with invalid content"""
    response = test_client.post(
        f"/api/chat/questionnaire/initiate",
        headers=auth_headers,
        json={
            "id_session": valid_session_id,
            "content": {"invalid": "content"},
            "configs": {}
        }
    )
    assert response.status_code == 400
    assert "validation error" in response.json()["detail"].lower()

def test_initiate_questionnaire_invalid_configs(test_client, auth_headers, valid_session_id, valid_questionnaire_content):
    """Test questionnaire initiation with invalid configs structure"""
    response = test_client.post(
        f"/api/chat/questionnaire/initiate",
        headers=auth_headers,
        json={
            "id_session": valid_session_id,
            "content": valid_questionnaire_content,
            "configs": {
                "invalid_field": "invalid_value",
                "webhook_url": 123,  # should be string
                "emails": "not_an_array",  # should be array
                "avatar": "not_an_object"  # should be object
            }
        }
    )
    assert response.status_code == 400
    assert "validation error" in response.json()["detail"].lower()

def test_websocket_connection_success(test_client, valid_session_id, valid_questionnaire_content, valid_questionnaire_configs):
    """Test successful WebSocket connection"""
    # First initiate the questionnaire
    test_client.post(
        f"/api/chat/questionnaire/initiate",
        headers={"Authorization": f"Basic {base64.b64encode(b'test_user:test_password').decode()}"},
        json={
            "id_session": valid_session_id,
            "content": valid_questionnaire_content,
            "configs": valid_questionnaire_configs
        }
    )
    
    # Then connect via WebSocket
    with test_client.websocket_connect(f"/api/chat/questionnaire/start/{valid_session_id}") as websocket:
        # Should receive welcome message and UI config
        data = json.loads(websocket.receive_text())
        assert data["type"] == "ui_config"
        assert "avatar" in data["data"]
        
        data = json.loads(websocket.receive_text())
        assert data["type"] == "agent_response"
        assert "Welcome" in data["content"]

def test_websocket_invalid_session(test_client):
    """Test WebSocket connection with invalid session"""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with test_client.websocket_connect("/api/chat/questionnaire/start/invalid_session_id"):
            pass
    assert exc_info.value.code == 4004

def test_websocket_conversation_flow(test_client, valid_session_id, valid_questionnaire_content, valid_questionnaire_configs):
    """Test complete conversation flow through WebSocket"""
    # Initiate questionnaire
    test_client.post(
        f"/api/chat/questionnaire/initiate",
        headers={"Authorization": f"Basic {base64.b64encode(b'test_user:test_password').decode()}"},
        json={
            "id_session": valid_session_id,
            "content": valid_questionnaire_content,
            "configs": valid_questionnaire_configs
        }
    )
    
    with test_client.websocket_connect(f"/api/chat/questionnaire/start/{valid_session_id}") as websocket:
        # Skip initial messages (ui_config and welcome)
        websocket.receive_text()
        websocket.receive_text()
        
        # Answer first question
        websocket.send_text(json.dumps({"content": "John Doe"}))
        response = json.loads(websocket.receive_text())
        assert response["type"] == "agent_response"
        assert "next question" in response["content"].lower()
        
        # Answer second question
        websocket.send_text(json.dumps({"content": "25"}))
        response = json.loads(websocket.receive_text())
        assert response["type"] == "agent_response"
        assert "thank you" in response["content"].lower()
        assert response["data"]["is_complete"] is True 