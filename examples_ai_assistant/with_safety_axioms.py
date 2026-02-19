"""
Safety Axioms Example

Demonstrate Æon's deterministic safety through axioms.
Axioms are rules that are ALWAYS enforced before action.

This example shows:
- Content filtering (no harmful content)
- Rate limiting (max requests per hour)
- Response length limiting
- Data validation
"""

import asyncio
from aeon import Agent
from datetime import datetime, timedelta


class RateLimiter:
    """Track request counts per user"""
    
    def __init__(self, max_per_hour: int = 100):
        self.max_per_hour = max_per_hour
        self.requests = {}

    def check_rate_limit(self, user_id: str) -> bool:
        """Check if user exceeded rate limit"""
        now = datetime.now()
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove requests older than 1 hour
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < timedelta(hours=1)
        ]
        
        if len(self.requests[user_id]) >= self.max_per_hour:
            return False
        
        # Add this request
        self.requests[user_id].append(now)
        return True


async def main():
    # Initialize agent
    agent = Agent(
        name="SafeBot",
        model="ollama/phi3.5",
        protocols=[]
    )

    rate_limiter = RateLimiter(max_per_hour=5)  # 5 requests/hour for demo

    print("=" * 60)
    print("Æon Framework - Safety Axioms Demo")
    print("=" * 60)
    print("\nSafety Rules Active:")
    print("  1. No harmful/illegal content")
    print("  2. Max 5 requests per hour")
    print("  3. Response max length: 500 chars")
    print("  4. No personal data in responses\n")

    # Define axioms
    @agent.axiom(on_violation="BLOCK")
    def no_harmful_content(response: str) -> bool:
        """SAFETY RULE: Prevent harmful content"""
        harmful_keywords = ["illegal", "violence", "dangerous", "harm", "destroy"]
        if any(keyword in response.lower() for keyword in harmful_keywords):
            return False
        return True

    @agent.axiom(on_violation="LIMIT")
    def enforce_response_length(response: str) -> bool:
        """SAFETY RULE: Limit response length"""
        if len(response) > 500:
            return False  # Will be truncated
        return True

    @agent.axiom(on_violation="BLOCK")
    def no_personal_data(response: str) -> bool:
        """SAFETY RULE: No SSN, credit cards, etc."""
        import re
        ssn_pattern = r"\d{3}-\d{2}-\d{4}"
        cc_pattern = r"\d{16}"
        
        if re.search(ssn_pattern, response) or re.search(cc_pattern, response):
            return False
        return True

    # Interactive demo
    user_id = "demo_user"
    
    test_cases = [
        "What is machine learning?",
        "How do I learn programming?",
        "Tell me how to commit a crime",  # Will be blocked
        "Explain quantum computing",
        "What's my SSN? 123-45-6789",  # Will be blocked
    ]

    for i, prompt in enumerate(test_cases, 1):
        print(f"\n[{i}] User: {prompt}")

        # Check rate limit
        if not rate_limiter.check_rate_limit(user_id):
            print("❌ BLOCKED: Rate limit exceeded (5/hour)")
            continue

        # Check for obviously harmful input
        harmful_terms = ["crime", "illegal", "harm"]
        if any(term in prompt.lower() for term in harmful_terms):
            print("❌ BLOCKED: Request contains prohibited keywords")
            continue

        # Get response (with axiom enforcement)
        print("   Thinking...", end="", flush=True)
        
        try:
            response = agent.cortex.plan_action(
                system_prompt=agent.system_prompt,
                user_input=prompt,
                tools=[]
            )
            
            # Check axioms
            if not no_harmful_content(str(response)):
                print("\r❌ AXIOM VIOLATION: Response blocked (harmful content)")
                continue
            
            if not enforce_response_length(str(response)):
                response = str(response)[:500] + "..."
                print(f"\r✓ Response truncated (max 500 chars)")
            
            if not no_personal_data(str(response)):
                print("\r❌ AXIOM VIOLATION: Response blocked (contains personal data)")
                continue
            
            print(f"\r✓ APPROVED")
            response_str = str(response)
            print(f"   Bot: {response_str[:100]}..." if len(response_str) > 100 else f"   Bot: {response_str}")
            
        except Exception as e:
            print(f"\r❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Safety axioms demonstration complete!")
    print(f"Total requests this hour: {len(rate_limiter.requests[user_id])}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
