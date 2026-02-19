import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from aeon.core.agent import Agent
from aeon.security.trust import TrustLevel
from aeon.tools.macos import MacOSTool
from aeon.tools.search import SearchTool

async def main():
    print("="*60)
    print(" 💡 ÆON PERSONAL ASSISTANT (Native macOS + Ollama)")
    print("="*60)
    print(" [i] Model: ollama/phi3.5 (Local)")
    print(" [i] Native Platform: macOS")
    print("="*60)

    # 1. Initialize the Personal Assistant Agent
    # We use TrustLevel.FULL to allow native system access
    agent = Agent(
        name="AeonAssistant",
        model="ollama/phi3.5", # Ensure you have 'ollama pull phi3.5' run
        protocols=[],
        trust_level=TrustLevel.FULL
    )
    
    # 2. Add macOS specific and search capabilities
    agent.tools.register(MacOSTool())
    agent.tools.register(SearchTool())
    
    print("\n [!] Assistant Ready! Type your command (e.g., 'Crie um lembrete para a reunião às 15h').")
    print(" [!] Press Ctrl+C to exit.\n")

    try:
        while True:
            user_input = input(" [User] > ")
            if not user_input.strip():
                continue
                
            if user_input.lower() in ["exit", "quit", "sair"]:
                break

            # Process the command via the Agent Loop
            # The agent will reason using Ollama and decide to use 'macos_system'
            print(f"\n [~] Aeon is thinking...")
            result = await agent.process(user_input)
            
            if result and result.get("type") == "action_result":
                print(f" [✓] Result: {result['content']}")
            elif result and result.get("type") == "hitl_review":
                # If HITL is triggered, handle it
                print(f" [?] HITL: Review required for '{result['tool_name']}'.")
                confirm = input("     [A]pprove / [R]eject? ").lower()
                if confirm in ["a", "y", "yes"]:
                    # In this simple demo, we execute it directly through the tool registry
                    # to keep the demo flow concise.
                    res = await agent.tools.execute_tool(result['tool_name'], **result['args'])
                    print(f" [✓] Executed: {res}")
                else:
                    print(" [✗] Action rejected by user.")
            elif result and result.get("type") == "text":
                print(f" [Aeon] > {result['content']}")
            
            print("-" * 30)

    except KeyboardInterrupt:
        print("\n [!] Ending assistant session. Goodbye!")
    except Exception as e:
        print(f" [!] Error: {str(e)}")

if __name__ == "__main__":
    if sys.platform != "darwin":
        print(" [!] Warning: This demo is designed specifically for macOS.")
    
    asyncio.run(main())
