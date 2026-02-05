"""
Executive Layer: Corresponds to the Prefrontal Cortex.
Responsible for deterministic controls, safety gates, and axioms.
"""
from typing import Callable, Any, Dict, Union, Optional
from pydantic import BaseModel

class AxiomViolationError(Exception):
    """Custom exception raised when an Action is blocked by an Axiom."""
    pass

class AxiomViolation(BaseModel):
    """Data model representing a violation of a safety axiom."""
    axiom_name: str
    reason: str
    remediation: Optional[Dict[str, Any]] = None

class Axiom:
    """
    Represents a deterministic logic gate that validates agent output.
    """
    def __init__(self, name: str, handler: Callable, on_violation: str = "OVERRIDE"):
        self.name = name
        self.handler = handler
        self.on_violation = on_violation  # modes: BLOCK, OVERRIDE, LOG

    def execute(self, payload: Dict[str, Any]) -> Union[bool, Dict[str, Any]]:
        """
        Executes the axiom logic against the payload.
        Returns:
            True: Pass
            False: Block
            Dict: Override/Patch
        """
        return self.handler(payload)

class ExecutiveRegistry:
    """
    Manages the registration and execution of axioms for an agent.
    """
    def __init__(self):
        self._axioms: Dict[str, Axiom] = {}

    def register(self, name: str, on_violation: str) -> Callable:
        """
        Decorator to register a new axiom.
        """
        def decorator(func: Callable):
            axiom = Axiom(name=func.__name__, handler=func, on_violation=on_violation)
            self._axioms[func.__name__] = axiom
            return func
        return decorator

    def validate_output(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the payload through all registered axioms.
        Returns the sanitized payload or raises AxiomViolationError.
        """
        sanitized_payload = payload.copy()
        
        for name, axiom in self._axioms.items():
            result = axiom.execute(sanitized_payload)
            
            # Logic: If True, pass. If Dict, override. If False, block.
            if result is True:
                continue
                
            if isinstance(result, dict):
                # AXIOM OVERRIDE triggered
                # We update the payload so subsequent axioms validate the NEW data
                print(f"[!] AXIOM INTERVENTION: {name} modified the output.")
                sanitized_payload = result
                continue
                
            if result is False:
                # AXIOM BLOCK triggered
                # We raise an exception to HALT the agent execution loop immediately
                msg = f"Operation blocked by safety axiom: {name}"
                print(f"[!] AXIOM BLOCK: {msg}")
                raise AxiomViolationError(msg)
                
        return sanitized_payload