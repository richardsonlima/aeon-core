"""Command interface for agent execution and management."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import asyncio


class CommandStatus(str, Enum):
    """Command execution status."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CommandResult:
    """Result of command execution."""
    
    status: CommandStatus
    output: Any
    message: str = ""
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    
    def is_success(self) -> bool:
        """Check if command succeeded."""
        return self.status == CommandStatus.COMPLETED
    
    def is_error(self) -> bool:
        """Check if command failed."""
        return self.status == CommandStatus.FAILED


class CLICommand(ABC):
    """Abstract base class for CLI commands."""
    
    def __init__(self, name: str, description: str = ""):
        """Initialize command.
        
        Args:
            name: Command name
            description: Command description
        """
        self.name = name
        self.description = description
        self.options: Dict[str, Any] = {}
    
    @abstractmethod
    async def execute(self, **kwargs) -> CommandResult:
        """Execute the command.
        
        Args:
            **kwargs: Command-specific arguments
            
        Returns:
            CommandResult
        """
        pass
    
    async def run(self, **kwargs) -> CommandResult:
        """Run command with error handling.
        
        Args:
            **kwargs: Command arguments
            
        Returns:
            CommandResult
        """
        try:
            return await self.execute(**kwargs)
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                output=None,
                message=f"Command failed: {self.name}",
                error=str(e),
            )


class CommandRegistry:
    """Registry of available commands."""
    
    def __init__(self):
        """Initialize command registry."""
        self.commands: Dict[str, CLICommand] = {}
    
    def register(self, command: CLICommand) -> None:
        """Register a command.
        
        Args:
            command: Command to register
        """
        self.commands[command.name] = command
    
    def unregister(self, name: str) -> None:
        """Unregister a command.
        
        Args:
            name: Command name
        """
        if name in self.commands:
            del self.commands[name]
    
    def get(self, name: str) -> Optional[CLICommand]:
        """Get a command by name.
        
        Args:
            name: Command name
            
        Returns:
            Command or None
        """
        return self.commands.get(name)
    
    def list_commands(self) -> List[str]:
        """List all registered commands.
        
        Returns:
            List of command names
        """
        return list(self.commands.keys())
    
    async def execute(self, name: str, **kwargs) -> CommandResult:
        """Execute a command by name.
        
        Args:
            name: Command name
            **kwargs: Command arguments
            
        Returns:
            CommandResult
        """
        command = self.get(name)
        if not command:
            return CommandResult(
                status=CommandStatus.FAILED,
                output=None,
                message=f"Unknown command: {name}",
                error=f"Command not found: {name}",
            )
        
        return await command.run(**kwargs)


class CommandInterface:
    """Main CLI interface for agent commands."""
    
    def __init__(self):
        """Initialize command interface."""
        self.registry = CommandRegistry()
        self.history: List[Dict[str, Any]] = []
    
    def register_command(self, command: CLICommand) -> None:
        """Register a command.
        
        Args:
            command: Command to register
        """
        self.registry.register(command)
    
    async def execute_command(self, name: str, **kwargs) -> CommandResult:
        """Execute a command.
        
        Args:
            name: Command name
            **kwargs: Command arguments
            
        Returns:
            CommandResult
        """
        result = await self.registry.execute(name, **kwargs)
        
        # Record in history
        self.history.append({
            "command": name,
            "kwargs": kwargs,
            "result": result.status.value,
            "timestamp": None,  # Add real timestamp if needed
        })
        
        return result
    
    def get_command_help(self, name: str) -> Optional[str]:
        """Get help for a command.
        
        Args:
            name: Command name
            
        Returns:
            Help text or None
        """
        command = self.registry.get(name)
        if not command:
            return None
        
        help_text = f"Command: {command.name}\n"
        help_text += f"Description: {command.description}\n"
        
        if command.options:
            help_text += "Options:\n"
            for opt_name, opt_desc in command.options.items():
                help_text += f"  {opt_name}: {opt_desc}\n"
        
        return help_text
    
    def list_commands(self) -> List[str]:
        """List all available commands.
        
        Returns:
            List of command names
        """
        return self.registry.list_commands()
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get command history.
        
        Returns:
            List of executed commands
        """
        return self.history.copy()
    
    def clear_history(self) -> None:
        """Clear command history."""
        self.history.clear()
