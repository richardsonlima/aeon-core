from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid

class BaseEvent(BaseModel):
    """Base class for all agent events"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    type: str

class AgentStartEvent(BaseEvent):
    """Event triggered when agent starts"""
    type: str = "agent_start"
    agent_name: str
    model: str

class UserMessageEvent(BaseEvent):
    """Event for user input"""
    type: str = "user_message"
    content: str

class ReasoningStepEvent(BaseEvent):
    """Event for Cortex reasoning"""
    type: str = "reasoning_step"
    thought: str
    tool_call: Optional[Dict[str, Any]] = None

class ToolExecutionEvent(BaseEvent):
    """Event for tool execution attempt"""
    type: str = "tool_execution"
    tool_name: str
    arguments: Dict[str, Any]
    status: str  # 'started', 'completed', 'failed', 'blocked'

class ToolResultEvent(BaseEvent):
    """Event for tool execution result"""
    type: str = "tool_result"
    tool_name: str
    output: str
    error: Optional[str] = None
