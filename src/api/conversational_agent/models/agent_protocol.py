from typing import Dict, Any, Protocol

class ConversationalAgent(Protocol):
    """Protocol that defines the interface for conversational agents"""
    def start_conversation(self, session_data: Dict = None) -> str:
        """Starts the conversation and returns the welcome message"""
        ...
    
    def process_user_input(self, user_input: str) -> str:
        """Processes user input and returns the agent's response"""
        ...
    
    def is_conversation_complete(self) -> bool:
        """Checks if the conversation has ended"""
        ...
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Gets a summary of the conversation"""
        ... 