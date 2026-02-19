import subprocess
from typing import Any
from aeon.tools.base import BaseTool

class ShellTool(BaseTool):
    """System tool for shell command execution"""
    
    def __init__(self):
        super().__init__(
            name="shell_command",
            description="Execute shell commands on the local system."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 30
                }
            },
            "required": ["command"]
        }

    async def execute(self, **kwargs) -> Any:
        command = kwargs.get("command")
        timeout = kwargs.get("timeout", 30)
        
        try:
            # Run command synchronously as it's a wrapper
            # In production, this should use asyncio.create_subprocess_shell
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            error = result.stderr
            
            if result.returncode == 0:
                return f"Output:\n{output}"
            else:
                return f"Error (code {result.returncode}):\n{error}\nOutput:\n{output}"
                
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"
