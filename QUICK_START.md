# Æon Framework v0.3.0 - Quick Reference Guide

## Installation

```bash
git clone https://github.com/richardsonlima/aeon-core.git
cd aeon-core
pip install -e .
```

## Core Concepts

### 1️⃣ Agent Initialization

```python
from aeon import Agent
from aeon.protocols import A2A, MCP

agent = Agent(
    name="MyBot",
    model="google/gemini-2.0-flash-001",
    protocols=[A2A(port=8000), MCP(servers=["tools.py"])]
)
```

---

## Layer 1: Integrations (Multi-Platform)

### Register a Provider

```python
from aeon.integrations.provider import IntegrationProvider, ProviderConfig, Packet

class MyProvider(IntegrationProvider):
    async def initialize(self):
        print("Connecting...")
    
    async def terminate(self):
        print("Disconnecting...")
    
    async def dispatch(self, packet: Packet) -> bool:
        print(f"Sending: {packet.payload} → {packet.destination}")
        return True
    
    async def receive(self):
        return None

# Register
provider = MyProvider(ProviderConfig())
agent.integrations.register("myplatform", provider)

# Activate
await agent.integrations.activate_provider("myplatform")

# Send packet
packet = Packet(origin="agent", destination="user123", payload="Hello!")
await agent.integrations.dispatch_packet("myplatform", packet)
```

---

## Layer 2: Extensions (Pluggable Capabilities)

### Create & Load a Capability

```python
from aeon.extensions.capability import Capability, CapabilityMetadata

class MyCapability(Capability):
    metadata = CapabilityMetadata(
        name="my_feature",
        version="1.0.0",
        description="Does something cool",
        dependencies=["other_feature"],  # Optional
        tags=["utility", "external"]
    )
    
    async def activate(self):
        print("Activating...")
    
    async def deactivate(self):
        print("Deactivating...")
    
    async def invoke(self, **kwargs):
        return f"Result: {kwargs.get('input')}"

# Register & activate
capability = MyCapability()
agent.extensions.register(capability)
await agent.extensions.activate("my_feature")

# Invoke
result = await agent.extensions.invoke("my_feature", input="test")
print(result)

# List active
active = agent.extensions.list_active()
```

---

## Layer 3: Dialogue (Conversation State)

### Manage Conversations

```python
from aeon.dialogue.context import DialogueContext, ActorRole

# Create conversation
context = DialogueContext(
    context_id="conv_001",
    origin_platform="telegram",
    participant_id="user_42"
)

# Add turns
context.add_turn(ActorRole.USER, "What's the weather?")
context.add_turn(ActorRole.AGENT, "Let me check...")
context.add_turn(ActorRole.SYSTEM, "Retrieved data")

# Store
agent.dialogue.store(context)

# Retrieve
retrieved = agent.dialogue.retrieve("conv_001")
print(f"History: {len(retrieved.turns)} turns")

# Query
user_convs = agent.dialogue.query_by_participant("user_42")
telegram_convs = agent.dialogue.query_by_platform("telegram")

# Cleanup expired
removed = agent.dialogue.cleanup_expired()
```

---

## Layer 4: Dispatcher (Event Routing)

### Emit & Handle Events

```python
from aeon.dispatcher.event import Event, EventType
from datetime import datetime

# Subscribe to event type
async def on_communication(event: Event):
    print(f"Got message: {event.payload['text']}")

agent.dispatcher.subscribe(EventType.COMMUNICATION_RECEIVED, on_communication)

# Subscribe to all events
def log_all(event):
    print(f"Event: {event.event_type.value}")

agent.dispatcher.subscribe_all(log_all)

# Emit event
event = Event(
    event_type=EventType.COMMUNICATION_RECEIVED,
    timestamp=datetime.now(),
    source="telegram_provider",
    payload={"text": "Hello!", "user": "user_42"},
    priority=5
)
await agent.dispatcher.emit(event)

# Start dispatcher (processes queued events)
asyncio.create_task(agent.dispatcher.start())
```

---

## Layer 5: Automation (Task Scheduling)

### Schedule & Execute Tasks

```python
from aeon.automation.temporal import TemporalPattern, ScheduledTask

# Define handler
async def send_daily_report():
    print("Sending daily report...")

# Register handler
agent.automation.define_handler("daily_report", send_daily_report)

# Create temporal pattern
pattern = TemporalPattern(
    minute="0",      # Minute 0
    hour="8",        # Hour 8 (8 AM)
    day_of_month="*", # Every day
    month="*",       # Every month
    day_of_week="*"  # Every day of week
)

# Schedule task
task = ScheduledTask(
    task_id="task_daily_report",
    label="Daily Report",
    temporal_pattern=pattern,
    handler_id="daily_report",
    enabled=True
)
agent.automation.schedule(task)

# Manual execution
await agent.automation.execute_task("task_daily_report")

# List tasks
tasks = agent.automation.list_tasks()
for task in tasks:
    print(f"{task.label}: {'enabled' if task.enabled else 'disabled'}")

# Enable/disable
agent.automation.disable_task("task_daily_report")
agent.automation.enable_task("task_daily_report")

# Start scheduler
await agent.automation.start()
```

---

## Complete Example Workflow

```python
import asyncio
from aeon import Agent
from aeon.protocols import A2A, MCP
from aeon.integrations.provider import IntegrationProvider, ProviderConfig, Packet
from aeon.extensions.capability import Capability, CapabilityMetadata
from aeon.dialogue.context import DialogueContext, ActorRole
from aeon.dispatcher.event import Event, EventType
from aeon.automation.temporal import TemporalPattern, ScheduledTask

async def main():
    # Initialize
    agent = Agent("ChatBot", "gpt-4", protocols=[A2A(), MCP()])
    
    # 1. Provider
    class TelegramProvider(IntegrationProvider):
        async def initialize(self): pass
        async def terminate(self): pass
        async def dispatch(self, packet): return True
        async def receive(self): return None
    
    agent.integrations.register("telegram", TelegramProvider(ProviderConfig()))
    await agent.integrations.activate_provider("telegram")
    
    # 2. Capability
    class WeatherCap(Capability):
        metadata = CapabilityMetadata(name="weather")
        async def activate(self): pass
        async def deactivate(self): pass
        async def invoke(self, **kw): return {"temp": 25, "city": kw.get("city")}
    
    agent.extensions.register(WeatherCap())
    await agent.extensions.activate("weather")
    
    # 3. Conversation
    ctx = DialogueContext("conv_1", "telegram", "user_42")
    ctx.add_turn(ActorRole.USER, "What's weather in SP?")
    weather = await agent.extensions.invoke("weather", city="São Paulo")
    ctx.add_turn(ActorRole.AGENT, f"In SP: {weather['temp']}°C")
    agent.dialogue.store(ctx)
    
    # 4. Event
    event = Event(
        event_type=EventType.PROCESSING_COMPLETE,
        source="agent",
        payload={"result": weather},
        priority=7
    )
    await agent.dispatcher.emit(event)
    
    # 5. Task
    async def health():
        print("✓ System OK")
    
    agent.automation.define_handler("health", health)
    task = ScheduledTask(
        task_id="hc1",
        label="Health",
        temporal_pattern=TemporalPattern(hour="*/1"),
        handler_id="health"
    )
    agent.automation.schedule(task)
    await agent.automation.execute_task("hc1")
    
    # Dispatch message
    packet = Packet("agent", "user_42", f"Weather: {weather['temp']}°C")
    await agent.integrations.dispatch_packet("telegram", packet)

asyncio.run(main())
```

---

## Common Patterns

### Pattern 1: Event-Driven Workflow

```python
# Listen for incoming messages
async def handle_message(event: Event):
    user = event.payload['user']
    text = event.payload['text']
    
    # Create dialogue
    ctx = DialogueContext(f"conv_{user}", "telegram", user)
    ctx.add_turn(ActorRole.USER, text)
    
    # Process with capability
    result = await agent.extensions.invoke("llm", prompt=text)
    ctx.add_turn(ActorRole.AGENT, result)
    
    # Store and send
    agent.dialogue.store(ctx)
    packet = Packet("agent", user, result)
    await agent.integrations.dispatch_packet("telegram", packet)

agent.dispatcher.subscribe(EventType.COMMUNICATION_RECEIVED, handle_message)
```

### Pattern 2: Capability Chain

```python
# Multiple capabilities
agent.extensions.register(GPTCapability())
agent.extensions.register(TranslateCapability())
agent.extensions.register(SummarizeCapability())

await agent.extensions.activate("gpt")
await agent.extensions.activate("translate")
await agent.extensions.activate("summarize")

# Chain execution
text = "Hello"
translated = await agent.extensions.invoke("translate", text=text, lang="pt")
summarized = await agent.extensions.invoke("summarize", text=translated)
```

### Pattern 3: Scheduled Reports

```python
async def daily_summary():
    convs = agent.dialogue.query_by_platform("telegram")
    print(f"Today: {len(convs)} conversations")

agent.automation.define_handler("summary", daily_summary)
task = ScheduledTask(
    task_id="daily_summary",
    label="Daily Summary",
    temporal_pattern=TemporalPattern(hour="23", minute="0"),  # 11 PM
    handler_id="summary"
)
agent.automation.schedule(task)
```

---

## Running the Demo

```bash
python examples/advanced_integration_demo.py
```

---

## Files to Read

- **ARCHITECTURE.md** - Complete reference
- **DESIGN_INDEPENDENCE.md** - Design guarantees
- **INTEGRATION_SUMMARY.md** - What was built
- **examples/advanced_integration_demo.py** - Working code
