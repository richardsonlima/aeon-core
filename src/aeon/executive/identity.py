from typing import Dict, Any, List
import os

class IdentityAxiom:
    """
    Executive Layer (L3) Axiom that enforces identity alignment.
    Ensures that the agent's actions are consistent with the SOUL.md.
    """
    
    def __init__(self, vault_path: str = "src/aeon/core/vault"):
        self.vault_path = vault_path
        self.soul_content = self._load_manifest("SOUL.md")
        self.user_content = self._load_manifest("USER.md")
        self.agent_content = self._load_manifest("AGENTS.md")

    def _load_manifest(self, filename: str) -> str:
        path = os.path.join(self.vault_path, filename)
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read()
        return ""

    def validate_plan(self, thought: str, action: Dict[str, Any]) -> bool:
        """
        Check if the proposed action violates any core identity axioms.
        Internal method for the Executive layer to perform pre-flight checks.
        """
        # For v0.4.0, we perform basic sanity checks.
        # Future versions will use the LLM to validate the thought against the SOUL.
        
        # Example: Prevent destructive commands mentioned in AGENTS.md
        if "rm -rf" in str(action).lower():
            return False
            
        return True

    def get_system_reinforcement(self) -> str:
        """
        Provides a condensed version of the SOUL to be injected into the system prompt.
        """
        return (
            f"\n### IDENTITY REINFORCEMENT (SOUL.md)\n"
            f"{self.soul_content[:500]}...\n\n"
            f"### USER CONTEXT (USER.md)\n"
            f"{self.user_content[:500]}...\n"
        )
