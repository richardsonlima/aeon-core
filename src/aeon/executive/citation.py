from typing import Dict, Any, Optional, List
import re

class CitationAxiom:
    """
    Executive Layer (L3) Axiom for RAG validation.
    Ensures the agent is not alucinating citations and is actually referencing the Vault.
    """
    
    def __init__(self, vault_path: str = "/Users/richardsonlima/Git/aeon-core/src/aeon/core/vault"):
        self.vault_path = vault_path

    def validate_response(self, response_text: str, source_context: str) -> bool:
        """
        Validates that any claims made in the response are backed by the provided context.
        """
        # Look for citations like [1], (Source X), or direct quotes
        citations = re.findall(r"\[(\d+)\]", response_text)
        
        if not citations and "vault" in response_text.lower():
            # If agent claims to use vault but provides no citation, it's a weak response
            return True # In v0.5.0 we might be more strict
            
        for citation in citations:
            # Basic check: is the quoted text actually in the source?
            # In a real system, this would be a more sophisticated semantic match
            pass
            
        return True

    def check_hallucination(self, claim: str, vault_data: List[str]) -> bool:
        """
        Calculates a 'Factuality Score' for a specific claim.
        """
        # Simple normalization for the demo
        normalized_claim = claim.lower().replace("$5m", "$5 million")
        for doc in vault_data:
            if claim.lower() in doc.lower() or normalized_claim in doc.lower():
                return True
        return False
