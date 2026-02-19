"""
Verification script for Æon Core Autonomous Loop and Native Tools.
The agent will attempt to:
1. Create a directory
2. Create a file with specific content
3. List the directory to verify
4. Read the file to verify
"""
import asyncio
import os
import shutil
from aeon import Agent

async def main():
    print("=" * 60)
    print("🚀 AEON CORE - AUTONOMOUS LOOP VERIFICATION")
    print("=" * 60)

    # 1. Setup clean environment
    test_dir = os.path.abspath("autonomous_test_dir")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    # 2. Initialize Agent
    # Note: Using Ollama with phi3.5 which we know exists
    agent = Agent(
        name="AutoVerifyBot",
        model="ollama/phi3.5",
        protocols=[]
    )


    # 3. Define the goal
    goal = f"""
    Create a new directory called '{test_dir}'.
    Inside that directory, create a file called 'hello.txt' with the content 'Æon is now autonomous!'.
    Verification: List the directory and then read the file to confirm it was successful.
    Once verified, state 'Goal achieved'.
    """

    # 4. Run the autonomous loop
    # Limit to 5 steps for verification
    history = await agent.run(goal, max_steps=5)

    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Steps executed: {len(history)}")
    
    # Final check
    hello_file = os.path.join(test_dir, "hello.txt")
    if os.path.exists(hello_file):
        with open(hello_file, "r") as f:
            content = f.read()
            if "Æon is now autonomous!" in content:
                print("✅ PASSED: File created with correct content.")
            else:
                print(f"❌ FAILED: File content mismatch: '{content}'")
    else:
        print("❌ FAILED: File was not created.")

if __name__ == "__main__":
    asyncio.run(main())
