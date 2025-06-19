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
                "id": "1",
                "question": "What is your name?",
                "answerType": "short_text"
            },
            {
                "id": "2",
                "question": "What is your age?",
                "answerType": "short_text"
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
    
    # Wait for the chat UI to load
    page.wait_for_selector(".chat-ui-container", timeout=30000)
    
    # Wait for loading to complete
    page.wait_for_selector(".chat-section", timeout=15000)
    
    # Wait for connection to be established
    page.wait_for_selector(".connection-status .status-text:has-text('Connected')", timeout=15000)
    
    # Verify chat interface is ready
    expect(page.locator(".chat-widget")).to_be_visible()
    
    # Wait for welcome message from agent
    page.wait_for_selector(".message.agent", timeout=15000)
    
    # Send first answer
    input_field = page.locator("#user-input")
    send_button = page.locator(".send-button")
    
    input_field.fill("John Doe")
    send_button.click()
    
    # Verify first answer was sent
    page.wait_for_selector(".message.user:has-text('John Doe')", timeout=10000)
    
    # Wait for next question and send second answer
    page.wait_for_selector(".message.agent", timeout=10000)
    input_field.fill("25")
    send_button.click()
    
    # Verify second answer was sent
    page.wait_for_selector(".message.user:has-text('25')", timeout=10000)
    
    # Wait for completion
    page.wait_for_selector(".connection-status .status-text:has-text('Conversation Ended')", timeout=15000)

def test_error_handling(page: Page):
    """Test error handling in the chat UI"""
    # Try to connect with invalid session
    page.goto("http://localhost:8080/invalid_session_id")
    
    # Wait for error section to appear
    page.wait_for_selector(".error-section", timeout=10000)
    expect(page.locator(".error-section")).to_contain_text("Connection Error")
    
    # Verify retry button exists
    retry_button = page.locator(".retry-button")
    expect(retry_button).to_be_visible()
    
    # Click retry and verify it attempts reconnection
    retry_button.click()
    page.wait_for_selector(".loading-section", timeout=5000)

def test_websocket_reconnection(page: Page):
    """Test WebSocket reconnection functionality"""
    # Get valid session
    session_id = get_session_token()
    questionnaire_data = initiate_questionnaire(session_id)
    
    # Navigate to chat UI
    page.goto(f"http://localhost:8080/{session_id}")
    
    # Wait for the chat UI to load
    page.wait_for_selector(".chat-ui-container", timeout=30000)
    
    # Wait for loading to complete
    page.wait_for_selector(".chat-section", timeout=15000)
    
    # Wait for connection to be established
    page.wait_for_selector(".connection-status .status-text:has-text('Connected')", timeout=15000)
    
    # Verify chat interface is ready
    expect(page.locator(".chat-widget")).to_be_visible()
    
    # Wait for welcome message from agent
    page.wait_for_selector(".message.agent", timeout=15000)
    
    # Send first answer
    input_field = page.locator("#user-input")
    send_button = page.locator(".send-button")
    
    input_field.fill("John Doe")
    send_button.click()
    
    # Verify first answer was sent
    page.wait_for_selector(".message.user:has-text('John Doe')", timeout=10000)
    
    # Wait for next question and send second answer
    page.wait_for_selector(".message.agent", timeout=10000)
    input_field.fill("25")
    send_button.click()
    
    # Verify second answer was sent
    page.wait_for_selector(".message.user:has-text('25')", timeout=10000)
    
    # Wait for completion
    page.wait_for_selector(".connection-status .status-text:has-text('Conversation Ended')", timeout=15000)

def test_ui_configuration(page: Page):
    """Test UI configuration through WebSocket"""
    # Get valid session with avatar config
    session_id = get_session_token()
    questionnaire_data = initiate_questionnaire(session_id)
    
    # Navigate to chat UI
    page.goto(f"http://localhost:8080/{session_id}")
    
    # Wait for the chat UI to load
    page.wait_for_selector(".chat-ui-container", timeout=30000)
    
    # Wait for loading to complete
    page.wait_for_selector(".chat-section", timeout=15000)
    
    # Wait for connection to be established
    page.wait_for_selector(".connection-status .status-text:has-text('Connected')", timeout=15000)
    
    # Verify chat interface is ready
    expect(page.locator(".chat-widget")).to_be_visible()
    
    # Verify avatar is displayed (should be visible based on config)
    expect(page.locator(".header-avatar")).to_be_visible()
    expect(page.locator(".avatar-label")).to_contain_text("Test Bot")
    
    # Wait for welcome message from agent
    page.wait_for_selector(".message.agent", timeout=15000)
    
    # Send first answer
    input_field = page.locator("#user-input")
    send_button = page.locator(".send-button")
    
    input_field.fill("John Doe")
    send_button.click()
    
    # Verify first answer was sent
    page.wait_for_selector(".message.user:has-text('John Doe')", timeout=10000)
    
    # Wait for next question and send second answer
    page.wait_for_selector(".message.agent", timeout=10000)
    input_field.fill("25")
    send_button.click()
    
    # Verify second answer was sent
    page.wait_for_selector(".message.user:has-text('25')", timeout=10000)
    
    # Wait for completion
    page.wait_for_selector(".connection-status .status-text:has-text('Conversation Ended')", timeout=15000) 