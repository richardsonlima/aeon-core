"""
Aeon Example: Advanced Agent with Integrations, Extensions & Automation (v0.3.0-alpha).
Demonstrates complete integration of all Aeon subsystems.
"""

import sys
import os
import asyncio

# Ensure src path is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from aeon import Agent
from aeon.protocols import A2A, MCP
from aeon.integrations.provider import IntegrationProvider, ProviderConfig, Packet, TransportType
from aeon.extensions.capability import Capability, CapabilityMetadata
from aeon.dialogue.context import DialogueContext, ActorRole
from aeon.dispatcher.event import Event, EventType
from aeon.automation.temporal import TemporalPattern, ScheduledTask


# Example: Custom Integration Provider (e.g., for Telegram)
class TelegramProvider(IntegrationProvider):
    """Mock Telegram provider for demonstration."""
    
    async def initialize(self) -> None:
        print("🔌 [Telegram Provider] Initializing connection...")
        self._initialized = True
    
    async def terminate(self) -> None:
        print("🔌 [Telegram Provider] Closing connection...")
        self._initialized = False
    
    async def dispatch(self, packet: Packet) -> bool:
        print(f"📤 [Telegram] → {packet.destination}: {packet.payload[:50]}...")
        return True
    
    async def receive(self) -> None:
        return None


# Example: Custom Capability (e.g., Weather Information)
class WeatherCapability(Capability):
    """Mock weather capability for demonstration."""
    
    metadata = CapabilityMetadata(
        name="weather",
        version="1.0.0",
        description="Retrieves weather information for locations",
        tags=["information", "external-api"]
    )
    
    async def activate(self) -> None:
        print("⚙️ [Weather Capability] Activated")
    
    async def deactivate(self) -> None:
        print("⚙️ [Weather Capability] Deactivated")
    
    async def invoke(self, **kwargs) -> dict:
        location = kwargs.get("location", "Unknown")
        print(f"🌤️  Fetching weather for {location}...")
        return {"location": location, "condition": "Sunny", "temp": 25}


async def main():
    """Demonstrate complete Aeon Framework integration."""
    
    print("=" * 70)
    print("🧠 AEON FRAMEWORK v0.3.0-alpha - Complete Integration Demo")
    print("=" * 70)
    print()
    
    # 1. Initialize Agent
    print("1️⃣  INITIALIZING AGENT")
    print("-" * 70)
    agent = Agent(
        name="SentinelBot",
        model="google/gemini-2.0-flash-001",
        protocols=[
            A2A(port=8000),
            MCP(servers=["industrial_sensor.py"]),
        ]
    )
    print(f"✓ Agent '{agent.name}' initialized\n")
    
    # 2. Register Integration Providers
    print("2️⃣  REGISTERING INTEGRATION PROVIDERS")
    print("-" * 70)
    telegram = TelegramProvider(ProviderConfig(
        transport_type=TransportType.ASYNC,
        enabled=True
    ))
    agent.integrations.register("telegram", telegram)
    print(f"✓ Telegram provider registered")
    print(f"  Available providers: {agent.integrations.list_providers()}\n")
    
    # 3. Load Capabilities via Extension System
    print("3️⃣  LOADING EXTENSION CAPABILITIES")
    print("-" * 70)
    weather_cap = WeatherCapability()
    agent.extensions.register(weather_cap)
    print(f"✓ Weather capability registered")
    print(f"  Available: {list(agent.extensions.list_capabilities().keys())}\n")
    
    # 4. Activate Extension
    print("4️⃣  ACTIVATING EXTENSIONS")
    print("-" * 70)
    await agent.extensions.activate("weather")
    print(f"✓ Active extensions: {agent.extensions.list_active()}\n")
    
    # 5. Create Dialogue Context
    print("5️⃣  CREATING DIALOGUE CONTEXT")
    print("-" * 70)
    context = DialogueContext(
        context_id="conv_user_42_telegram",
        origin_platform="telegram",
        participant_id="user_42"
    )
    context.add_turn(ActorRole.USER, "What's the weather in São Paulo?")
    context.add_turn(ActorRole.AGENT, "Let me check that for you...")
    agent.dialogue.store(context)
    print(f"✓ Dialogue context created: {context.context_id}")
    print(f"  Turns: {len(context.turns)}")
    print(f"  Last: {context.get_last_turn().utterance if context.get_last_turn() else 'None'}\n")
    
    # 6. Emit Event via Dispatcher
    print("6️⃣  EMITTING EVENTS VIA DISPATCHER")
    print("-" * 70)
    event = Event(
        event_type=EventType.COMMUNICATION_RECEIVED,
        timestamp=asyncio.get_event_loop().time(),
        source="telegram_provider",
        payload={"user": "user_42", "message": "What's the weather?"},
        priority=5
    )
    await agent.dispatcher.emit(event)
    print(f"✓ Event emitted: {event.event_type.value}\n")
    
    # 7. Invoke Capability
    print("7️⃣  INVOKING CAPABILITY")
    print("-" * 70)
    weather_result = await agent.extensions.invoke("weather", location="São Paulo")
    print(f"✓ Capability invoked: {weather_result}\n")
    
    # 8. Schedule Task
    print("8️⃣  SCHEDULING AUTOMATION TASK")
    print("-" * 70)
    async def health_check():
        print("   ⏰ Performing system health check...")
    
    agent.automation.define_handler("health_check", health_check)
    task = ScheduledTask(
        task_id="health_001",
        label="System Health Check",
        temporal_pattern=TemporalPattern(hour="*/6"),  # Every 6 hours
        handler_id="health_check",
        enabled=True
    )
    agent.automation.schedule(task)
    print(f"✓ Task scheduled: {task.label}")
    print(f"  Pattern: Every 6 hours\n")
    
    # 9. Activate Provider
    print("9️⃣  ACTIVATING INTEGRATION PROVIDER")
    print("-" * 70)
    await agent.integrations.activate_provider("telegram")
    print(f"✓ Telegram provider activated\n")
    
    # 10. Send Packet through Provider
    print("🔟 DISPATCHING PACKET THROUGH PROVIDER")
    print("-" * 70)
    packet = Packet(
        origin="agent",
        destination="user_42",
        payload="São Paulo weather: Sunny, 25°C"
    )
    success = await agent.integrations.dispatch_packet("telegram", packet)
    print(f"✓ Packet dispatch: {'SUCCESS' if success else 'FAILED'}\n")
    
    # 11. Display System Status
    print("1️⃣1️⃣  SYSTEM STATUS REPORT")
    print("-" * 70)
    print(f"Agent: {agent.name}")
    print(f"Core Subsystems:")
    print(f"  - Cortex (LLM): {agent.cortex.config.model}")
    print(f"  - Executive (Safety): Axiom registry ready")
    print(f"  - Hive (A2A): {'Connected' if agent.hive else 'Not initialized'}")
    print(f"  - Synapse (MCP): {'Ready' if agent.synapse else 'Not initialized'}")
    print(f"\nIntegration Layer:")
    print(f"  - Providers: {agent.integrations.list_providers()}")
    print(f"  - Active: {[p for p in agent.integrations.list_providers() if agent.integrations.is_active(p)]}")
    print(f"\nExtension Layer:")
    print(f"  - Capabilities: {list(agent.extensions.list_capabilities().keys())}")
    print(f"  - Active: {agent.extensions.list_active()}")
    print(f"\nDialogue Layer:")
    print(f"  - Contexts: {len(agent.dialogue.list_contexts())}")
    print(f"  - Retention: 30 days")
    print(f"\nAutomation Layer:")
    print(f"  - Scheduled tasks: {len(agent.automation.list_tasks())}")
    print(f"  - Running: {agent.automation._running}")
    print()
    
    print("=" * 70)
    print("✨ Aeon Framework fully operational with Nanobot-level capabilities!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
