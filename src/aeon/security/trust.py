from enum import Enum

class TrustLevel(Enum):
    """
    Security trust levels for agent capabilities.
    """
    ISOLATED = "isolated"   # No filesystem, network, or shell access. Safe for untrusted code/prompts.
    STANDARD = "standard"   # Read-only filesystem, safe network (HTTP GET), no shell.
    FULL = "full"           # Unrestricted access (Filesystem write, Shell, Browser). Admin only.

class SecurityContext:
    """
    Manages the current trust level and validates permission requests.
    """
    def __init__(self, level: TrustLevel):
        self.level = level

    def can_execute(self, tool_name: str) -> bool:
        """Check if a tool is allowed at the current trust level."""
        
        # High-risk tools requiring FULL trust
        high_risk = ["shell_command", "file_system", "web_browser"]
        
        # Medium-risk tools requiring STANDARD or FULL trust
        medium_risk = ["read_file", "search_web"]
        
        if self.level == TrustLevel.ISOLATED:
            return tool_name not in high_risk and tool_name not in medium_risk
            
        if self.level == TrustLevel.STANDARD:
            return tool_name not in high_risk
            
        return True  # FULL trust allows everything
