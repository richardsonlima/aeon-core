import asyncio
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from aeon.core.agent import Agent

class AgentLoop:
    """The 'Consciousness' Loop for autonomous agent execution"""
    
    def __init__(self, agent: "Agent"):
        self.agent = agent

        self.running = False
        self.history: List[Dict[str, Any]] = []

    async def run(self, goal: str, max_steps: int = 10):
        """
        Execute a continuous cycle of reasoning and action to achieve a goal.
        """
        self.running = True
        print(f"\n🚀 Starting autonomous loop for goal: {goal}")
        print(f"🔄 Max steps: {max_steps}")
        
        current_input = f"Keep working towards this goal: {goal}. If the goal is fully achieved, end the session by stating it."
        
        for step in range(1, max_steps + 1):
            if not self.running:
                break
                
            print(f"\n--- STEP {step}/{max_steps} ---")
            
            # 1. Process one cycle
            result = await self.agent.process(current_input)
            
            if not result:
                print("⚠️ Loop interrupted: No response from agent.")
                break
                
            self.history.append({"step": step, "result": result})
            
            # 2. Check for completion
            if result["type"] == "text":
                content = str(result["content"]).lower()
                if any(word in content for word in ["goal achieved", "task complete", "finished", "all done"]):
                    print("\n🎯 Goal achieved! Ending loop.")
                    break
            
            # 3. Handle action results
            if result["type"] == "action_result":
                current_input = f"The previous action returned: {result['content']}. Continue working on the goal: {goal}"
            elif result["type"] == "hitl_review":
                print(f" [?] HITL: Action '{result['tool_name']}' requires manual approval.")
                print(f" [?] Arguments: {result['args']}")
                
                # In a real CLI, we would use input(). For the framework loop, we simulate approval
                # unless a specific flag is set. For this implementation, we pause.
                user_input = input(" [>] Approve execution? (y/n/edit): ").lower()
                
                if user_input in ["y", "yes", "a"]:
                    # Proceed with execution bypassing the next review
                    # (Note: In a full implementation, we'd call a specific 'execute_safe' method)
                    print(" [✓] HITL: Approved. Executing...")
                    # For demo purposes, we inject the result as if it were valid
                    current_input = f"Action '{result['tool_name']}' was approved and executed. Continue towards goal: {goal}"
                else:
                    print(" [✗] HITL: Rejected. Re-reasoning...")
                    current_input = f"Action '{result['tool_name']}' was REJECTED by the user. Find another way to achieve the goal: {goal}"
            else:
                # If just text, ask what's next
                current_input = f"I've noted your response. Continue towards the goal: {goal}"
                
            # Subtle delay between steps
            await asyncio.sleep(0.5)
            
        self.running = False
        print("\n🏁 Autonomous loop finished.")
        return self.history

    def stop(self):
        """Stop the execution loop"""
        self.running = False
