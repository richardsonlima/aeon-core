# Aeon Framework v0.3.0-alpha - Advanced Integration Architecture

## Overview

Aeon Framework v0.3.0 introduces a comprehensive integration layer that combines neuro-symbolic reasoning with practical multi-platform capabilities. Unlike traditional agent frameworks, Aeon separates concerns into distinct subsystems with clear interfaces and protocols.

## Architecture Layers

### Core Cognitive Stack
- **Cortex**: LLM-based reasoning engine (System 1 - Fast/Intuitive)
- **Executive**: Safety axioms and deterministic validation (System 2 - Slow/Deliberate)
- **Hive**: Agent-to-Agent communication (A2A Protocol)
- **Synapse**: Tool integration and MCP connectivity

### Practical Integration Stack
- **Integrations**: Multi-platform communication providers
- **Extensions**: Modular capability system with dependency resolution
- **Dialogue**: Conversation state management with event sourcing
- **Dispatcher**: Event-driven inter-component communication
- **Automation**: Temporal task scheduling with pattern-based triggers

---

## Integration Layer

### Integrations Module (replaces traditional Channels)

**Purpose**: Abstract transport layer for platform-agnostic communication.

**Key Concepts**:
- **IntegrationProvider**: Abstract transport handler
- **ProviderRegistry**: Dynamic provider discovery and routing
- **Packet**: Unified data transport format
- **TransportType**: Supports Async, Sync, Webhook, Polling

**Example - Telegram Integration**:

```python
from aeon.integrations.provider import IntegrationProvider, Packet

class TelegramProvider(IntegrationProvider):
    async def dispatch(self, packet: Packet) -> bool:
        # Send packet to Telegram
        return True
    
    async def receive(self) -> Optional[Packet]:
        # Poll for incoming messages
        return None

# Register provider
telegram = TelegramProvider(config)
agent.integrations.register("telegram", telegram)

# Send via provider
await agent.integrations.dispatch_packet("telegram", packet)
```

**Supported Platforms**:
- WhatsApp (Baileys WebSocket)
- Telegram (Bot API)
- Slack (WebSocket)
- Discord (Gateway)
- Email (SMTP)
- HTTP Webhooks
- Custom (implement IntegrationProvider)

---

## Extensions Layer

### Extensions Module (replaces traditional Skills)

**Purpose**: Pluggable capability system with dependency injection.

**Key Concepts**:
- **Capability**: Self-contained feature implementation
- **CapabilityMetadata**: Declarative capability description
- **CapabilityLoader**: Runtime loading with dependency resolution
- **Activation**: Lazy loading on-demand

**Example - Custom Capability**:

```python
from aeon.extensions.capability import Capability, CapabilityMetadata

class WeatherCapability(Capability):
    metadata = CapabilityMetadata(
        name="weather",
        version="1.0.0",
        description="Provides weather information",
        dependencies=["location_service"],  # Requires location_service
        tags=["information", "external-api"]
    )
    
    async def activate(self) -> None:
        # Initialize resources
        pass
    
    async def invoke(self, **kwargs) -> dict:
        location = kwargs.get("location")
        return await fetch_weather(location)

# Load capability
agent.extensions.register(WeatherCapability())
await agent.extensions.activate("weather")

# Invoke
result = await agent.extensions.invoke("weather", location="São Paulo")
```

**Built-in Capabilities** (examples to implement):
- GitHub API Integration
- Weather Data Fetching
- System Administration (Tmux, SSH)
- Code Execution Sandbox
- Document Processing
- Image Generation
- Web Search

---

## Dialogue Layer

### Dialogue Module (replaces traditional Session Management)

**Purpose**: Event-sourced conversation context with persistence.

**Key Concepts**:
- **DialogueContext**: Encapsulates single conversation
- **Turn**: Individual speaker contribution with metadata
- **ActorRole**: User/Agent/System classification
- **DialogueArchive**: Persistent storage with retention policies

**Example - Conversation Management**:

```python
from aeon.dialogue.context import DialogueContext, ActorRole

# Create context
context = DialogueContext(
    context_id="conv_user_42",
    origin_platform="telegram",
    participant_id="user_42"
)

# Add turns
context.add_turn(ActorRole.USER, "What's the weather?")
context.add_turn(ActorRole.AGENT, "Let me check...")

# Store in archive
agent.dialogue.store(context)

# Retrieve history
history = context.get_history(limit=10)

# Query
contexts = agent.dialogue.query_by_participant("user_42")
```

**Features**:
- Full conversation history with timestamps
- Contextual metadata per turn
- Turn-level annotations
- Retention policy enforcement
- Queryable archive
- Automatic cleanup

---

## Dispatcher Layer

### Dispatcher Module (replaces traditional Message Bus)

**Purpose**: Type-safe event routing with priority handling.

**Key Concepts**:
- **Event**: Type-safe event representation
- **EventType**: Classification enum
- **EventHub**: Central dispatch engine
- **Observer Pattern**: Decoupled pub/sub

**Example - Event Handling**:

```python
from aeon.dispatcher.event import Event, EventType

# Subscribe to event type
async def handle_communication(event: Event):
    print(f"Received from {event.source}: {event.payload}")

agent.dispatcher.subscribe(EventType.COMMUNICATION_RECEIVED, handle_communication)

# Subscribe to all events
agent.dispatcher.subscribe_all(lambda e: print(f"Event: {e.event_type}"))

# Emit event
event = Event(
    event_type=EventType.COMMUNICATION_RECEIVED,
    source="telegram_provider",
    payload={"user": "user_42", "text": "Hello!"},
    priority=5
)
await agent.dispatcher.emit(event)
```

**Event Types**:
- `LIFECYCLE_BOOT` / `LIFECYCLE_SHUTDOWN`
- `COMMUNICATION_RECEIVED` / `COMMUNICATION_SENT`
- `PROCESSING_START` / `PROCESSING_COMPLETE`
- `ERROR_OCCURRED`
- `CAPABILITY_LOADED` / `CAPABILITY_FAILED`

**Features**:
- Type-safe event hierarchy
- Priority-based processing
- Async/sync handler support
- Wildcard subscriptions
- Error isolation

---

## Automation Layer

### Automation Module (replaces traditional Cron)

**Purpose**: Temporal task orchestration with flexible scheduling.

**Key Concepts**:
- **ScheduledTask**: Task definition with temporal trigger
- **TemporalPattern**: Cron-like scheduling expression
- **TaskScheduler**: Execution engine
- **Separation of Concerns**: Scheduling logic isolated from execution

**Example - Task Scheduling**:

```python
from aeon.automation.temporal import TemporalPattern, ScheduledTask

# Define handler
async def health_check():
    print("Running health check...")

agent.automation.define_handler("health_check", health_check)

# Create temporal pattern
pattern = TemporalPattern(
    minute="0",
    hour="*/6",  # Every 6 hours
    day_of_month="*",
    month="*",
    day_of_week="*"
)

# Schedule task
task = ScheduledTask(
    task_id="health_001",
    label="System Health Check",
    temporal_pattern=pattern,
    handler_id="health_check",
    enabled=True
)

agent.automation.schedule(task)

# Manual execution
await agent.automation.execute_task("health_001")
```

**Temporal Patterns**:
- `*/N` - Every N units
- `N-M` - Range
- `L` - Last (day/weekday)
- `W` - Nearest weekday
- Specific values: `0,1,2`

**Features**:
- Execution history tracking
- Enable/disable without unscheduling
- Manual triggering
- Dependency-free execution
- Event emission on completion

---

## Integration Flow Example

```
User Input (Telegram)
    ↓
[TelegramProvider.receive()]
    ↓
[Event: COMMUNICATION_RECEIVED]
    ↓
[Dispatcher.emit(event)]
    ↓
[Cortex: LLM reasoning]
    ↓
[Extensions: Invoke "weather" capability]
    ↓
[DialogueContext: Add turn]
    ↓
[Event: PROCESSING_COMPLETE]
    ↓
[TelegramProvider.dispatch(packet)]
    ↓
User Response (Telegram)
```

---

## Design Principles

1. **Separation of Concerns**: Each layer has a single, well-defined responsibility
2. **Protocol-Oriented**: Interfaces are abstract protocols, not concrete implementations
3. **Decoupling**: Components communicate via events, not direct references
4. **Extensibility**: New providers, capabilities, and handlers can be added without modifying core
5. **Safety First**: All outputs validated through Executive axioms before exposure
6. **Zero Overhead**: Unused subsystems incur no runtime cost

---

## Migration from Nanobot

| Nanobot | Aeon v0.3.0 | Purpose |
|---------|-----------|---------|
| Channels | Integrations + ProviderRegistry | Multi-platform communication |
| Skills | Extensions + CapabilityLoader | Modular capabilities |
| Sessions | Dialogue + DialogueArchive | Conversation management |
| Bus | Dispatcher + EventHub | Event routing |
| Cron | Automation + TaskScheduler | Task scheduling |

---

## Next Steps

- [ ] Implement Telegram provider adapter
- [ ] Implement Slack provider adapter
- [ ] Build memory/RAG capability
- [ ] Add plugin marketplace
- [ ] Create monitoring dashboard
- [ ] Implement distributed scheduling

---

## Running Examples

```bash
# Complete integration demo
python examples/advanced_integration_demo.py

# Reactor controller with safety
python examples/reactor_controller.py
```
