"""Token tracking and event logging hooks."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field

from .hook import AgentLifecycleHook, ExecutionContext, EventType


@dataclass
class TokenUsage:
    """Token usage metrics."""
    
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, other: "TokenUsage") -> None:
        """Accumulate token usage."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.reasoning_tokens += other.reasoning_tokens
        self.cached_tokens += other.cached_tokens
        self.total_tokens += other.total_tokens
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "cached_tokens": self.cached_tokens,
            "total_tokens": self.total_tokens,
        }


class TokenTrackingHook(AgentLifecycleHook):
    """Tracks token usage across executions."""
    
    def __init__(self):
        """Initialize token tracker."""
        self.logger = logging.getLogger(__name__)
        self.executions: List[ExecutionContext] = []
        self.total_usage = TokenUsage()
        self.execution_count = 0
    
    async def on_execution_start(self, context: ExecutionContext) -> None:
        """Track execution start."""
        context.status = "running"
        self.logger.info(f"Execution started: {context.execution_id}")
    
    async def on_execution_end(self, context: ExecutionContext) -> None:
        """Track execution end and accumulate tokens."""
        context.status = "completed"
        self.executions.append(context)
        self.execution_count += 1
        
        # Accumulate tokens
        usage = TokenUsage(
            input_tokens=context.input_tokens,
            output_tokens=context.output_tokens,
            reasoning_tokens=context.reasoning_tokens,
            cached_tokens=context.cached_tokens,
        )
        usage.total_tokens = (
            usage.input_tokens + usage.output_tokens + usage.reasoning_tokens
        )
        self.total_usage.add(usage)
        
        self.logger.info(
            f"Execution completed: {context.execution_id} | "
            f"Tokens: input={usage.input_tokens}, output={usage.output_tokens}, "
            f"reasoning={usage.reasoning_tokens}, cached={usage.cached_tokens}"
        )
    
    async def on_event(self, context: ExecutionContext, event: EventType) -> None:
        """Track events."""
        if event == EventType.REASONING_START:
            context.reasoning_steps += 1
        elif event == EventType.VALIDATION_START:
            context.validation_checks += 1
        elif event == EventType.SAFETY_CHECK_START:
            context.safety_checks += 1
    
    async def on_tool_call(self, context: ExecutionContext, tool_name: str, args: Dict[str, Any]) -> None:
        """Track tool invocations."""
        context.increment_tool_call()
        self.logger.debug(f"Tool called: {tool_name} with args: {args}")
    
    async def on_error(self, context: ExecutionContext, error: Exception) -> None:
        """Track errors."""
        context.add_error(str(error))
        self.logger.error(f"Error in execution {context.execution_id}: {error}")
    
    def get_total_usage(self) -> TokenUsage:
        """Get total token usage across all executions."""
        return self.total_usage
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of all executions."""
        return {
            "execution_count": self.execution_count,
            "total_usage": self.total_usage.to_dict(),
            "executions": [ctx.to_dict() for ctx in self.executions],
        }


class EventLogger(AgentLifecycleHook):
    """Logs all events for debugging and auditing."""
    
    def __init__(self, verbose: bool = False):
        """Initialize event logger.
        
        Args:
            verbose: Whether to log all events (True) or only important ones (False)
        """
        self.logger = logging.getLogger(__name__)
        self.verbose = verbose
        self.events: List[Dict[str, Any]] = []
    
    async def on_execution_start(self, context: ExecutionContext) -> None:
        """Log execution start."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "execution_start",
            "execution_id": context.execution_id,
            "agent": context.agent_name,
        }
        self.events.append(event)
        self.logger.info(f"[{context.execution_id}] Execution started: {context.agent_name}")
    
    async def on_execution_end(self, context: ExecutionContext) -> None:
        """Log execution end."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "execution_end",
            "execution_id": context.execution_id,
            "agent": context.agent_name,
            "status": context.status,
            "duration_ms": context.duration_ms,
        }
        self.events.append(event)
        self.logger.info(
            f"[{context.execution_id}] Execution ended: {context.status} "
            f"({context.duration_ms}ms)"
        )
    
    async def on_event(self, context: ExecutionContext, event: EventType) -> None:
        """Log events."""
        if self.verbose:
            log_event = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "event",
                "execution_id": context.execution_id,
                "event": event.value,
            }
            self.events.append(log_event)
            self.logger.debug(f"[{context.execution_id}] Event: {event.value}")
    
    async def on_tool_call(self, context: ExecutionContext, tool_name: str, args: Dict[str, Any]) -> None:
        """Log tool calls."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "tool_call",
            "execution_id": context.execution_id,
            "tool": tool_name,
            "args": str(args)[:200],  # Truncate for logging
        }
        self.events.append(event)
        if self.verbose:
            self.logger.debug(f"[{context.execution_id}] Tool: {tool_name}")
    
    async def on_error(self, context: ExecutionContext, error: Exception) -> None:
        """Log errors."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "error",
            "execution_id": context.execution_id,
            "error": str(error),
        }
        self.events.append(event)
        self.logger.error(f"[{context.execution_id}] Error: {error}")
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all logged events."""
        return self.events
    
    def clear_events(self) -> None:
        """Clear event log."""
        self.events.clear()
