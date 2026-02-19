"""
Verification script for Æon Core Browser Capabilities.
The agent will attempt to:
1. Navigate to a website (https://agents.md)
2. Extract the page title and content
3. Verify that the content was retrieved
"""
import asyncio
from aeon import Agent
from aeon.tools.browser import PLAYWRIGHT_AVAILABLE

if not PLAYWRIGHT_AVAILABLE:
    print("❌ Playwright not installed. Skipping browser test.")
    exit(1)

async def main():
    print("=" * 60)
    print("🚀 AEON CORE - BROWSER TOOL VERIFICATION")
    print("=" * 60)

    # Initialize Agent with BrowserTool (enabled by default in new Agent)
    agent = Agent(
        name="BrowserBot",
        model="ollama/phi3.5",
        protocols=[]
    )

    # Define the goal
    goal = """
    Navigate to 'https://agents.md'.
    Extract the text content of the page.
    If you see 'Example Domain', state 'Goal achieved'.
    """

    # Run the autonomous loop
    print(f"🤖 Agent {agent.name} starting browser task...")
    await agent.run(goal, max_steps=5)
    
    # Verify memory recorded the tool use
    print("\n" + "=" * 60)
    print("📊 MEMORY VERIFICATION")
    print("=" * 60)
    
    found_browser_event = False
    for event in agent.memory.get_history():
        if event.type == "tool_execution" and event.tool_name == "web_browser":
            print(f"✅ Found browser execution event: {event.arguments}")
            found_browser_event = True
            
    if not found_browser_event:
        print("❌ FAILED: No browser execution recorded in memory.")

if __name__ == "__main__":
    asyncio.run(main())
