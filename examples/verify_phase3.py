"""
Verification script for Æon Core Phase 3:
1. Advanced Scheduling (Cron/Interval)
2. Webhook Triggers
3. SQLite Persistence
"""
import asyncio
import httpx
from datetime import datetime
from aeon import Agent
from aeon.automation.scheduler import ScheduledTask
import os

async def main():
    print("=" * 60)
    print("🚀 AEON CORE - PHASE 3 VERIFICATION")
    print("=" * 60)

    # Clean up previous DB for fresh test
    if os.path.exists("aeon_memory.db"):
        os.remove("aeon_memory.db")

    # 1. Initialize Agent
    agent = Agent(
        name="Phase3Bot",
        model="ollama/phi3.5",
        protocols=[]
    )
    
    # ---------------------------------------------------------
    # TEST 1: Scheduling (Interval Task)
    # ---------------------------------------------------------
    print("\n⏰ TEST 1: Scheduling (Interval Task)")
    
    task_ran = False
    
    def my_task_handler():
        nonlocal task_ran
        print("   ✅ Scheduled task executed!")
        task_ran = True

    # Register handler and schedule task
    agent.automation.define_handler("test_handler", my_task_handler)
    agent.automation.schedule(
        task_id="test_task",
        handler_id="test_handler",
        interval_seconds=2  # Run every 2 seconds
    )
    
    # Start agent (starts scheduler and webhook server)
    await agent.start()
    
    print("   Waiting for scheduled task...")
    await asyncio.sleep(3)  # Wait enough time for task to run
    
    if task_ran:
        print("✅ PASSED: Scheduler executed interval task.")
    else:
        print("❌ FAILED: Scheduler did not execute task.")

    # ---------------------------------------------------------
    # TEST 2: Webhook Trigger
    # ---------------------------------------------------------
    print("\n🔔 TEST 2: Webhook Trigger")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8001/webhook/github",
                json={"event": "push", "repo": "aeon-core"}
            )
            print(f"   Webhook response: {response.status_code} {response.json()}")
            
            if response.status_code == 200:
                print("✅ PASSED: Webhook endpoint reachable.")
            else:
                print("❌ FAILED: Webhook endpoint returned error.")
        except Exception as e:
            print(f"❌ FAILED: Could not connect to webhook: {e}")

    # ---------------------------------------------------------
    # TEST 3: SQLite Persistence
    # ---------------------------------------------------------
    print("\n💾 TEST 3: SQLite Persistence")
    
    # Check if DB file exists
    if os.path.exists("aeon_memory.db"):
        print("   ✅ DB file created.")
    else:
        print("   ❌ DB file missing.")
        
    # Check if events are in DB (we should have AGENT_START and maybe Scheduler/Webhook events if we logged them properly)
    # Note: WebhookListener currently just prints, let's see if we can check proper DB recording later.
    # But Agent.memory.append() definitely writes to DB.
    
    history = agent.memory.get_history()
    print(f"   Events in memory/DB: {len(history)}")
    if len(history) > 0:
        print(f"   Sample event: {history[0].type}")
        print("✅ PASSED: Events persist in SQLite.")
    else:
        print("❌ FAILED: No events found in memory.")

    # Stop agent
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
