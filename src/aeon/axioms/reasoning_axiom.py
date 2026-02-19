from typing import Dict, Any, List, Optional

class ReasoningAxiom:
    """
    Executive Layer Axiom that ensures the agent performs internal reasoning
    before executing high-stakes tools (Shell, System commands, etc).
    """
    def __init__(self, high_stakes_tools: Optional[List[str]] = None):
        # macos_system is moved to low-stakes by default to improve UX for simple personal tasks
        self.high_stakes_tools = high_stakes_tools or ["shell", "file_tool"]

    def validate_reasoning(self, tool_name: str, thought: str) -> bool:
        """
        Returns True if the reasoning is sufficient for the given tool.
        """
        if tool_name not in self.high_stakes_tools:
            return True
            
        # If it's high stakes, thought must be present and non-trivial
        if not thought or len(thought) < 5:
            return False
            
        return True
