import pytest
from playwright.sync_api import Page, expect
import requests
import base64
import json
import time

def get_session_token():
    """Helper function to get a session token"""
    credentials = base64.b64encode(b"test_user:test_password").decode()
    response = requests.post(
        "http://localhost:8000/api/chat/session/auth",
        headers={"Authorization": f"Basic {credentials}"}
    )
    return response.json()["id_session"]

def initiate_questionnaire(session_id):
    """Helper function to initiate a questionnaire"""
    credentials = base64.b64encode(b"test_user:test_password").decode()
    content = {
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
    configs = {
        "webhook_url": "http://test.webhook.url",
        "emails": ["test@example.com"],
        "avatar": {
            "show": True,
            "url": "http://test.avatar.url",
            "name": "Test Bot"
        }
    }
    response = requests.post(
        "http://localhost:8000/api/chat/questionnaire/initiate",
        headers={"Authorization": f"Basic {credentials}"},
        json={
            "id_session": session_id,
            "content": content,
            "configs": configs
        }
    )
    return response.json()

def test_complete_chat_flow(page: Page):
    """Test the complete chat flow from authentication to conversation completion"""
    # Get session token
    session_id = get_session_token()
    
    # Initiate questionnaire
    questionnaire_data = initiate_questionnaire(session_id)
    
    # Navigate to chat UI
    page.goto(f"http://localhost:8080/{session_id}")
    
    # Wait for chat to load and connect
    page.wait_for_selector(".chat-container")
    
    # Verify initial UI state
    expect(page.locator(".connection-status")).to_contain_text("Connected")
    expect(page.locator(".messages-area")).to_be_visible()
    
    # Wait for welcome message
    page.wait_for_selector(".message.agent")
    welcome_message = page.locator(".message.agent").first
    expect(welcome_message).to_contain_text("Welcome to the test questionnaire!")
    
    # Answer first question
    input_field = page.locator("textarea#user-input")
    send_button = page.locator("button.send-button")
    
    input_field.fill("John Doe")
    send_button.click()
    
    # Verify first answer was sent
    page.wait_for_selector(".message.user")
    user_message = page.locator(".message.user").last
    expect(user_message).to_contain_text("John Doe")
    
    # Wait for next question
    page.wait_for_selector(".message.agent >> text=next question")
    
    # Answer second question
    input_field.fill("25")
    send_button.click()
    
    # Verify second answer was sent
    page.wait_for_selector(".message.user >> text=25")
    
    # Wait for completion message
    page.wait_for_selector(".message.agent >> text=thank you", timeout=10000)
    
    # Verify conversation completed state
    page.wait_for_selector(".completion-status")
    expect(page.locator(".completion-status")).to_contain_text("Conversation completed")
    
    # Verify input is disabled
    expect(input_field).to_be_disabled()
    expect(send_button).to_be_disabled()

def test_error_handling(page: Page):
    """Test error handling in the chat UI"""
    # Try to connect with invalid session
    page.goto("http://localhost:8080/invalid_session_id")
    
    # Wait for error message
    page.wait_for_selector(".error-section")
    expect(page.locator(".error-section")).to_contain_text("Connection Error")
    
    # Verify retry button exists
    retry_button = page.locator(".retry-button")
    expect(retry_button).to_be_visible()
    
    # Click retry and verify it attempts reconnection
    retry_button.click()
    expect(page.locator(".connection-status")).to_contain_text("Connecting")

def test_websocket_reconnection(page: Page):
    """Test WebSocket reconnection functionality"""
    # Get valid session
    session_id = get_session_token()
    questionnaire_data = initiate_questionnaire(session_id)
    
    # Navigate to chat UI
    page.goto(f"http://localhost:8080/{session_id}")
    
    # Wait for initial connection
    page.wait_for_selector(".connection-status >> text=Connected")
    
    # Simulate connection loss (stop backend server temporarily)
    # Note: This would require actual server control in real testing
    
    # Verify reconnection attempt
    page.wait_for_selector(".connection-status >> text=Retrying")
    
    # Verify max reconnection attempts
    time.sleep(10)  # Wait for reconnection attempts
    expect(page.locator(".message.system")).to_contain_text("Could not restore connection")

def test_ui_configuration(page: Page):
    """Test UI configuration through WebSocket"""
    # Get valid session with avatar config
    session_id = get_session_token()
    questionnaire_data = initiate_questionnaire(session_id)
    
    # Navigate to chat UI
    page.goto(f"http://localhost:8080/{session_id}")
    
    # Wait for UI to load
    page.wait_for_selector(".chat-container")
    
    # Verify avatar is displayed
    expect(page.locator(".header-avatar")).to_be_visible()
    expect(page.locator(".avatar-label")).to_contain_text("Test Bot") 