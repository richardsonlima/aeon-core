# ÆON Framework v0.3.0 - Integration Layer Specification

## Overview

The Integration Layer bridges ÆON's cognitive reasoning (Cortex + Executive) with practical multi-platform communication. It provides the interfaces, protocols, and patterns for extending ÆON to new platforms and use cases.

---

## Core Integration Modules

### 1. Integrations (Multi-Platform Communication)

**Purpose**: Abstract transport layer for platform-agnostic communication.

**Key Components**:
- `IntegrationProvider`: Abstract base for transport handlers
- `ProviderRegistry`: Dynamic provider discovery and lifecycle management
- `Packet`: Unified data transport format for all platforms
- `TransportType`: Classification of transport modes (Async, Sync, Webhook, Polling)

**Supported Platforms**:
- WhatsApp (Baileys WebSocket)
- Telegram (Bot API)
- Slack (WebSocket)
- Discord (Gateway)
- Email (SMTP/IMAP)
- HTTP Webhooks
- Custom (implement IntegrationProvider)

**Example**:
```python
from aeon.integrations.provider import IntegrationProvider, Packet, ProviderConfig

class CustomProvider(IntegrationProvider):
    async def initialize(self):
        print("Connecting to platform...")
    
    async def dispatch(self, packet: Packet) -> bool:
        print(f"Sending: {packet.payload} → {packet.destination}")
        return True
    
    async def receive(self):
        # Optional: poll for messages
        return None
    
    async def terminate(self):
        print("Disconnecting...")

# Register & activate
provider = CustomProvider(ProviderConfig())
agent.integrations.register("custom", provider)
await agent.integrations.activate_provider("custom")
```

---

### 2. Extensions (Pluggable Capabilities)

**Purpose**: Modular capability system with runtime dependency resolution.

**Key Components**:
- `Capability`: Self-contained feature implementation
- `CapabilityMetadata`: Declarative capability descriptor
- `CapabilityLoader`: Runtime loading with dependency resolution
- `CapabilityRegistry`: Capability lifecycle management

**Features**:
- Dependency resolution with cycle detection
- Lazy loading (load only when needed)
- Version management
- Tag-based discovery
- Activation/deactivation lifecycle

**Example**:
```python
from aeon.extensions.capability import Capability, CapabilityMetadata

class WeatherCapability(Capability):
    metadata = CapabilityMetadata(
        name="weather",
        version="1.0.0",
        description="Provides weather information",
        dependencies=["api_client"],
        tags=["external", "utility"]
    )
    
    async def activate(self):
        print("Loading weather data sources...")
    
    async def invoke(self, **kwargs):
        location = kwargs.get("location", "NYC")
        return {"location": location, "temp": 72, "condition": "sunny"}

capability = WeatherCapability()
agent.extensions.register(capability)
await agent.extensions.activate("weather")
result = await agent.extensions.invoke("weather", location="London")
```

---

### 3. Dialogue (Conversation State)

**Purpose**: Event-sourced conversation management with retention policies.

**Key Components**:
- `DialogueContext`: Conversation state with turn history
- `Turn`: Single turn in dialogue exchange
- `DialogueArchive`: Persistent storage for dialogue contexts
- `ActorRole`: Classification of participants (User, Agent, System)

**Features**:
- Turn-based event history
- Event sourcing for full auditability
- Retention policies for storage management
- Archive capability for historical access
- Rich contextual annotations

**Example**:
```python
from aeon.dialogue.context import DialogueContext, Turn, ActorRole

context = DialogueContext(id="conv-123")

# Add turns
context.add_turn(Turn(
    actor=ActorRole.USER,
    utterance="What's the weather?",
    timestamp=datetime.now()
))

context.add_turn(Turn(
    actor=ActorRole.AGENT,
    utterance="It's sunny and 72°F",
    timestamp=datetime.now()
))

# Archive for later
archive = agent.dialogue.archive
archive.store(context)

# Retrieve
retrieved = archive.retrieve("conv-123")
```

---

### 4. Dispatcher (Event Routing)

**Purpose**: Type-safe event routing with priority-based inter-component communication.

**Key Components**:
- `Event`: Type-safe event representation
- `EventType`: Enum of all system events
- `EventHub`: Central routing and dispatch system
- `Subscriber`: Event handler registration

**Features**:
- Type-safe events (no string magic)
- Priority-based subscriber ordering
- Pattern-based event filtering
- Subscriber lifecycle management
- Built-in event tracing

**Example**:
```python
from aeon.dispatcher.event import Event, EventType
from aeon.dispatcher.hub import EventHub

hub = EventHub()

# Subscribe
async def on_message_received(event):
    print(f"Message from {event.data['sender']}: {event.data['text']}")

hub.subscribe(EventType.COMMUNICATION_RECEIVED, on_message_received)

# Emit
event = Event(
    type=EventType.COMMUNICATION_RECEIVED,
    data={"sender": "user@123", "text": "Hello!"}
)
await hub.emit(event)
```

---

### 5. Automation (Task Scheduling)

**Purpose**: Temporal task scheduling with flexible patterns.

**Key Components**:
- `TaskScheduler`: Orchestrates task execution
- `TemporalPattern`: Cron-like expressions for scheduling
- `ScheduledTask`: Task definition with pattern and handler
- `TaskRegistry`: Registry of scheduled tasks

**Features**:
- Cron-like temporal patterns
- Trigger-Action separation
- Handler registration separate from scheduling
- Flexible pattern support
- Multi-mode execution

**Example**:
```python
from aeon.automation.scheduler import TaskScheduler
from aeon.automation.temporal import TemporalPattern, ScheduledTask

scheduler = TaskScheduler()

# Define handler
async def cleanup_sessions():
    print("Cleaning up old sessions...")

scheduler.define_handler("cleanup", cleanup_sessions)

# Create temporal pattern (every hour)
pattern = TemporalPattern(minute="0")

# Schedule task
task = ScheduledTask(
    pattern=pattern,
    handler_id="cleanup"
)

scheduler.schedule(task)
```

---

## Advanced Integration Subsystems

### 6. Observability (Lifecycle Hooks)

**Purpose**: Monitor agent execution with lifecycle hooks and event tracking.

**Components**:
- `AgentLifecycleHook`: Base class for lifecycle listeners
- `TokenTrackingHook`: Token usage tracking
- `EventLogger`: Event logging for debugging
- `HookEventType`: Classifications of lifecycle events

**Usage**:
```python
from aeon.observability.hook import AgentLifecycleHook, HookEventType

class LoggingHook(AgentLifecycleHook):
    async def on_event(self, event_type: HookEventType, context):
        print(f"Event: {event_type} | Context: {context}")

hook = LoggingHook()
agent.observability.add_hook(hook)
```

---

### 7. Economics (Cost Tracking)

**Purpose**: Track and report execution costs.

**Components**:
- `CostTracker`: Tracks and reports execution costs
- `ExecutionCost`: Cost data structure
- `CostReport`: Aggregated cost report
- `ModelPricingRegistry`: Pricing data by model and provider

**Usage**:
```python
from aeon.economics.tracker import CostTracker

tracker = CostTracker()

# Track cost
cost = ExecutionCost(
    model="gpt-4",
    provider="openai",
    input_tokens=1000,
    output_tokens=500
)
tracker.record(cost)

# Generate report
report = tracker.generate_report()
print(f"Total cost: ${report.total_cost}")
```

---

### 8. CLI (Command Interface)

**Purpose**: Command-line interface for agent interaction.

**Components**:
- `CommandInterface`: Main CLI dispatcher
- `CLICommand`: Base class for CLI commands
- `CommandResult`: Return type for commands
- `Formatter`: Output formatting utilities

**Usage**:
```python
from aeon.cli.interface import CommandInterface, CLICommand

class GreetCommand(CLICommand):
    name = "greet"
    description = "Greet the user"
    
    async def execute(self, args):
        return CommandResult(
            success=True,
            output=f"Hello, {args.get('name', 'World')}!"
        )

cli = CommandInterface()
cli.register(GreetCommand())
await cli.run()
```

---

## ULTRA Enterprise Layer Integration

The ULTRA layer adds enterprise-grade systems that integrate with the base layer:

### Intelligent Routing (Router)
- Flexible message routing with strategies
- Filter-based routing rules
- Load balancing and failover

### Central Gateway (Gateway)
- Hub for all communications
- Session management
- Transport abstraction

### Enterprise Security (Security)
- Authentication and authorization
- Token lifecycle management
- Encryption at rest

### System Monitoring (Health)
- Real-time health checking
- Metrics collection
- Diagnostic reporting

### Performance Cache (Cache)
- Intelligent caching strategies
- TTL-based expiration
- Distributed replication

---

## Integration Patterns

### 1. Provider Pattern
```python
# Define a provider
class MyProvider(IntegrationProvider):
    pass

# Register
agent.integrations.register("my", MyProvider(config))

# Activate
await agent.integrations.activate_provider("my")

# Use
await agent.integrations.dispatch_packet("my", packet)
```

### 2. Capability Pattern
```python
# Define capability
class MyCapability(Capability):
    metadata = CapabilityMetadata(...)
    async def invoke(self, **kwargs):
        pass

# Register
agent.extensions.register(MyCapability())

# Activate
await agent.extensions.activate("my_capability")

# Use
result = await agent.extensions.invoke("my_capability", ...)
```

### 3. Event Pattern
```python
# Define handler
async def handler(event):
    pass

# Subscribe
hub.subscribe(EventType.SOME_EVENT, handler)

# Emit
await hub.emit(Event(type=EventType.SOME_EVENT, data=...))
```

---

## Best Practices

1. **Providers**: Implement health checks and error handling
2. **Capabilities**: Declare all dependencies in metadata
3. **Events**: Use enums, never strings for event types
4. **Dialogue**: Archive conversations for compliance
5. **Automation**: Use temporal patterns for clarity
6. **Integration**: Separate concerns across subsystems

---

## Type Safety & Validation

All integration components are fully typed:

```python
# Type hints throughout
async def dispatch_packet(self, packet: Packet) -> bool:
    pass

# Pydantic models for data
class Packet(BaseModel):
    origin: str
    destination: str
    payload: str
    metadata: Optional[Dict[str, Any]] = None
```

---

## Versioning & Compatibility

- Integration layer follows semantic versioning
- Breaking changes only in MAJOR versions
- New providers can be added in MINOR versions
- Bug fixes in PATCH versions

Current: **v0.3.0-ULTRA** (Feature complete, production-ready)
