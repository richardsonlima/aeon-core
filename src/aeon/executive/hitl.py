from typing import Dict, Any, List, Optional

class HITLAxiom:
    """
    Executive Layer (L3) Axiom for Human-in-the-loop validation.
    Triggers a manual review cycle for critical tool executions.
    """
    
    def __init__(self, critical_tools: Optional[List[str]] = None):
        # Tools that ALWAYS require human approval
        self.critical_tools = critical_tools or ["shell_tool", "file_tool", "macos_tool"]

    def requires_review(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """
        Determines if a proposed tool call requires human oversight.
        """
        if tool_name in self.critical_tools:
            return True
            
        # Example: Potential destructive patterns in non-critical tools
        if "delete" in str(args).lower() or "remove" in str(args).lower():
            return True
            
        return False

    def validate_approval(self, user_decision: str) -> bool:
        """
        Validates the human input (Approve/Reject).
        """
        return user_decision.lower() in ["approve", "yes", "y", "a"]
