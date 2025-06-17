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
    
    # Flag to indicate if clarification is needed
    needs_clarification: bool = False
    
    # Reason why clarification is needed
    clarification_reason: Optional[str] = None
    
    # Flag to indicate if the conversation has ended
    conversation_complete: bool = False
    
    # Additional data that may be useful
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True 