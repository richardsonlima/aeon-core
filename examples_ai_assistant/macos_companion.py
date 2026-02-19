import asyncio
import os
from aeon import Agent
from aeon.tools.macos import MacOSTool
from aeon.core.config import AeonConfig, TrustLevel

async def run_macos_companion():
    print("🚀 Starting Aeon macOS Companion...")
    
    # 1. Setup the MacOSTool
    macos_tool = MacOSTool()
    
    # 2. Initialize Agent with the tool
    # Note: In v0.4.0, we can also register tools via config or manually
    agent = Agent(
        name="MacAssistant",
        role="Personal Assistant for macOS",
        trust_level=TrustLevel.FULL
    )
    
    # Manually register the tool for this demo
    agent.tools.register(macos_tool)
    
    # 3. Simulate a Personal Assistant Workflow
    print("\n--- Phase 1: Planning the day ---")
    
    # Task 1: Create a daily briefing in Notes
    prompt_notes = """
    Create a new Apple Note titled 'Daily Briefing - Feb 17' with the following content:
    - 09:00: Team Sync
    - 11:00: Deep Work (Aeon v0.5 development)
    - 13:00: Lunch
    - 15:00: Client Call
    """
    await agent.run(prompt_notes)
    
    # Task 2: Set a reminder
    prompt_reminder = "Set a reminder to 'Buy groceries' in my 'Personal' list for tomorrow at 6pm."
    await agent.run(prompt_reminder)
    
    print("\n--- Phase 2: Information Retrieval ---")
    
    # Task 3: Use Safari to find info and summarize it in a notification
    prompt_safari = "Open 'https://news.ycombinator.com' in Safari, look at the top story, and send me a system notification with the title."
    await agent.run(prompt_safari)
    
    print("\n✅ All tasks completed. Check your Notes, Reminders, and Notifications!")

if __name__ == "__main__":
    # Ensure subprocesses are handled correctly in async loop
    asyncio.run(run_macos_companion())
