import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from aeon.cortex.context import SituationalInjector
from aeon.executive.identity import IdentityAxiom

def verify_identity_system():
    print(" [~] Initiating Æon Identity & Situational Awareness Verification...")
    
    # 1. Test Situational Injector
    injector = SituationalInjector()
    ctx = injector.get_current_context(user_timezone="America/Los_Angeles")
    
    print(f"\n [1] Situational Awareness:")
    print(f"     - Local Time: {ctx['user_local_time']}")
    print(f"     - Location: {ctx['location']}")
    print(f"     - Status: {ctx['framework_status']}")
    
    prompt = "What should I do now?"
    injected_prompt = injector.inject(prompt, ctx)
    print(f"\n [2] Injected Prompt Sample:\n{injected_prompt[:150]}...")

    # 2. Test Identity Axiom
    axiom = IdentityAxiom()
    reinforcement = axiom.get_system_reinforcement()
    
    print(f"\n [3] Identity Reinforcement (SOUL.md detected):")
    if "Richardson Lima" in reinforcement:
        print("     [OK] Soul Manifest correctly loaded and linked to Richardson.")
    else:
        print("     [FAIL] Soul Manifest not found or incorrect.")

    # 3. Test Safety Constraint
    print(f"\n [4] Safety Validation:")
    is_safe = axiom.validate_plan("Delete everything", {"command": "rm -rf /"})
    if not is_safe:
        print("     [OK] Destructive command 'rm -rf' blocked by AGENTS.md constraints.")
    else:
        print("     [FAIL] Destructive command was not blocked.")

    print("\n [✓] Identity & Situational Awareness Verification Complete!")

if __name__ == "__main__":
    verify_identity_system()
