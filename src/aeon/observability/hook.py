"""Lifecycle hooks for agent execution monitoring and instrumentation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel


class EventType(str, Enum):
    """Agent lifecycle events."""
    
    # Execution events
    EXECUTION_START = "execution.start"
    EXECUTION_END = "execution.end"
    EXECUTION_ERROR = "execution.error"
    
    # Interaction events
    INTERACTION_START = "interaction.start"
    INTERACTION_END = "interaction.end"
    INTERACTION_ERROR = "interaction.error"
    
    # Reasoning events
    REASONING_START = "reasoning.start"
    REASONING_END = "reasoning.end"
    
    # Tool events
    TOOL_CALL_START = "tool.call.start"
    TOOL_CALL_END = "tool.call.end"
    TOOL_CALL_ERROR = "tool.call.error"
    
    # Validation events
    VALIDATION_START = "validation.start"
    VALIDATION_END = "validation.end"
    VALIDATION_FAILED = "validation.failed"
    
    # Safety events
    SAFETY_CHECK_START = "safety.check.start"
    SAFETY_CHECK_PASSED = "safety.check.passed"
    SAFETY_CHECK_FAILED = "safety.check.failed"
    
    # State events
    STATE_CHANGE = "state.change"
    STATE_ERROR = "state.error"


@dataclass
class ExecutionContext:
    """Context information for a single execution cycle."""
    
    execution_id: str
    agent_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: EventType = EventType.EXECUTION_START
    
    # Execution metadata
    interaction_count: int = 0
    tool_calls: int = 0
    reasoning_steps: int = 0
    validation_checks: int = 0
    safety_checks: int = 0
    
    # Resource tracking
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    result: Optional[Any] = None
    status: str = "pending"  # pending, running, completed, failed
    
    duration_ms: Optional[float] = None
    
    def add_error(self, error: str) -> None:
        """Record an error during execution."""
        self.errors.append(f"[{datetime.utcnow().isoformat()}] {error}")
        self.status = "failed"
    
    def add_warning(self, warning: str) -> None:
        """Record a warning during execution."""
        self.warnings.append(f"[{datetime.utcnow().isoformat()}] {warning}")
    
    def increment_interaction(self) -> None:
        """Increment interaction counter."""
        self.interaction_count += 1
    
    def increment_tool_call(self) -> None:
        """Increment tool call counter."""
        self.tool_calls += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "execution_id": self.execution_id,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "interaction_count": self.interaction_count,
            "tool_calls": self.tool_calls,
            "reasoning_steps": self.reasoning_steps,
            "validation_checks": self.validation_checks,
            "safety_checks": self.safety_checks,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "cached_tokens": self.cached_tokens,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "result": str(self.result) if self.result else None,
            "status": self.status,
            "duration_ms": self.duration_ms,
        }


class AgentLifecycleHook(ABC):
    """Abstract base class for lifecycle hooks."""
    
    @abstractmethod
    async def on_execution_start(self, context: ExecutionContext) -> None:
        """Called when execution starts.
        
        Args:
            context: Execution context
        """
        pass
    
    @abstractmethod
    async def on_execution_end(self, context: ExecutionContext) -> None:
        """Called when execution ends.
        
        Args:
            context: Execution context
        """
        pass
    
    @abstractmethod
    async def on_event(self, context: ExecutionContext, event: EventType) -> None:
        """Called for any event.
        
        Args:
            context: Execution context
            event: Event type
        """
        pass
    
    @abstractmethod
    async def on_tool_call(self, context: ExecutionContext, tool_name: str, args: Dict[str, Any]) -> None:
        """Called when a tool is invoked.
        
        Args:
            context: Execution context
            tool_name: Name of tool being called
            args: Tool arguments
        """
        pass
    
    @abstractmethod
    async def on_error(self, context: ExecutionContext, error: Exception) -> None:
        """Called when an error occurs.
        
        Args:
            context: Execution context
            error: Exception that occurred
        """
        pass


class HookRegistry:
    """Registry for lifecycle hooks."""
    
    def __init__(self):
        """Initialize hook registry."""
        self.hooks: List[AgentLifecycleHook] = []
    
    def register(self, hook: AgentLifecycleHook) -> None:
        """Register a lifecycle hook.
        
        Args:
            hook: Hook to register
        """
        if hook not in self.hooks:
            self.hooks.append(hook)
    
    def unregister(self, hook: AgentLifecycleHook) -> None:
        """Unregister a lifecycle hook.
        
        Args:
            hook: Hook to unregister
        """
        if hook in self.hooks:
            self.hooks.remove(hook)
    
    async def emit_execution_start(self, context: ExecutionContext) -> None:
        """Emit execution start event to all hooks."""
        for hook in self.hooks:
            try:
                await hook.on_execution_start(context)
            except Exception as e:
                print(f"Error in hook {hook.__class__.__name__}: {e}")
    
    async def emit_execution_end(self, context: ExecutionContext) -> None:
        """Emit execution end event to all hooks."""
        for hook in self.hooks:
            try:
                await hook.on_execution_end(context)
            except Exception as e:
                print(f"Error in hook {hook.__class__.__name__}: {e}")
    
    async def emit_event(self, context: ExecutionContext, event: EventType) -> None:
        """Emit generic event to all hooks."""
        for hook in self.hooks:
            try:
                await hook.on_event(context, event)
            except Exception as e:
                print(f"Error in hook {hook.__class__.__name__}: {e}")
    
    async def emit_tool_call(self, context: ExecutionContext, tool_name: str, args: Dict[str, Any]) -> None:
        """Emit tool call event to all hooks."""
        for hook in self.hooks:
            try:
                await hook.on_tool_call(context, tool_name, args)
            except Exception as e:
                print(f"Error in hook {hook.__class__.__name__}: {e}")
    
    async def emit_error(self, context: ExecutionContext, error: Exception) -> None:
        """Emit error event to all hooks."""
        for hook in self.hooks:
            try:
                await hook.on_error(context, error)
            except Exception as e:
                print(f"Error in hook {hook.__class__.__name__}: {e}")
