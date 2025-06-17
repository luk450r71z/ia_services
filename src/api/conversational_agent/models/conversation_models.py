from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class ConversationState(BaseModel):
    """Conversational agent state that maintains the conversation context"""
    
    # Conversation message history
    messages: List[BaseMessage] = Field(default_factory=list)
    
    # Pending questions to be asked
    pending_questions: List[str] = Field(default_factory=list)
    
    # User responses collected
    user_responses: Dict[str, str] = Field(default_factory=dict)
    
    # Current question being processed
    current_question: Optional[str] = None
    
    # Index of the current question
    current_question_index: int = 0
    
    # Flag to indicate if the conversation has ended
    conversation_complete: bool = False
    
    # Extra data for agent-specific information
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Clarification flags
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True 