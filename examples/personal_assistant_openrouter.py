import sys
import os
import asyncio

# Ensure the local 'src' directory is in the Python path for development
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from aeon.core.agent import Agent
from aeon.security.trust import TrustLevel
from aeon.tools.macos import MacOSTool
from aeon.tools.search import SearchTool

async def main():
    """
    Main execution loop for the Aeon Personal Assistant.
    Handles user interaction and agent processing.
    """
    print("="*60)
    print(" 💡 ÆON PERSONAL ASSISTANT (Native macOS + OpenRouter)")
    print("="*60)
    print(f" [i] Model: deepseek/deepseek-r1-0528:free (Cloud)")
    print(" [i] Native Platform: macOS")
    print("="*60)

    # 1. Agent Initialization
    # TrustLevel.FULL grants access to native macOS automation tools
    agent = Agent(
        name="AeonCloud",
        model="deepseek/deepseek-r1-0528:free",
        protocols=[],
        trust_level=TrustLevel.FULL
    )
    
    # 2. Capability Registration
    # MacOSTool: Interface with Reminders, Calendar, and System Settings
    # SearchTool: Web search capabilities for external knowledge
    agent.tools.register(MacOSTool())
    agent.tools.register(SearchTool())
    
    print("\n [!] Assistant Ready! Type your command (e.g., 'Create a reminder for the 3pm meeting').")
    print(" [!] Press Ctrl+C to exit.\n")

    try:
        while True:
            # Capture user input from the terminal
            user_input = input(" [User] > ")
            
            if not user_input.strip():
                continue
                
            if user_input.lower() in ["exit", "quit", "sair"]:
                break

            print(f"\n [~] Aeon is reasoning (Cloud)...")
            
            try:
                # Core Agent Loop processing
                # This call may trigger the 'matches' UnboundLocalError in v0.4.0 
                # if the LLM output does not follow the tool-call protocol.
                result = await agent.process(user_input)
                
                if not result:
                    print(" [!] Warning: The model returned an empty response.")
                    continue

                # Handle different result types from the Agent
                if result.get("type") == "action_result":
                    print(f" [✓] Result: {result['content']}")
                
                elif result.get("type") == "hitl_review":
                    print(f" [?] HITL: Review required for '{result['tool_name']}'.")
                    confirm = input("     [A]pprove / [R]eject? ").lower()
                    if confirm in ["a", "y", "yes"]:
                        res = await agent.tools.execute_tool(result['tool_name'], **result['args'])
                        print(f" [✓] Executed: {res}")
                    else:
                        print(" [✗] Action rejected by user.")
                
                elif result.get("type") == "text":
                    print(f" [Aeon] > {result['content']}")

            except UnboundLocalError:
                # Specific catch for the v0.4.0 initialization bug
                print(f" [!] Parser Error: The model failed to follow the tool protocol.")
                print(f"     Note: Ensure the model is correctly generating <tool_call> tags.")
            except Exception as e:
                print(f" [!] Processing Error: {str(e)}")
            
            print("-" * 30)

    except KeyboardInterrupt:
        print("\n [!] Ending assistant session. Goodbye!")
    except Exception as e:
        print(f" [!] Global Application Error: {str(e)}")

if __name__ == "__main__":
    # OS validation
    if sys.platform != "darwin":
        print(" [!] Warning: This demo is designed specifically for macOS.")
    
    # Environment variable check (inherited from shell)
    # This prevents hardcoding sensitive keys in the source code
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print(" [!] Error: OPENROUTER_API_KEY not found in environment.")
        print("     Please run: export OPENROUTER_API_KEY='your_key_here'")
        sys.exit(1)
    
    # Execute the asynchronous main loop
    try:
        asyncio.run(main())
    except Exception as e:
        print(f" [!] Fatal Error: {e}")