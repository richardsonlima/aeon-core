# Æon Framework (Core)

<div align="center">
  <h3>The Neuro-Symbolic Runtime for Distributed Agents</h3>
  <p>
    <em>"Safety-Native. Protocol-First. Extensible by Design."</em>
  </p>
</div>

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License">
  </a>
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/status-experimental%20research-orange.svg" alt="Status">
  <img src="https://img.shields.io/badge/architecture-neuro--symbolic-purple.svg" alt="Architecture">
</p>

---

## ⚡ The "Trust Stack" for Advanced Agents

**Æon v0.3.0** is a comprehensive framework that solves the **Extensibility Problem** in agent systems.  
While other frameworks focus on quick wins, Æon focuses on building **production-grade, extensible agents**.

### Core Philosophy

**Æon separates cognitive reasoning from practical integration**, enabling:

1. **Cognitive Stack**: LLM-based reasoning with deterministic safety validation
2. **Integration Stack**: Multi-platform communication, modular capabilities, event routing
3. **Safety Stack**: Axiom-based control, safety validation before action
4. **Scalability Stack**: Event-driven architecture for distributed coordination

---

## 🏗️ Architecture

### 16 Integrated Subsystems (4 Layers)

```
Æon Agent v0.3.0-ULTRA
├── CORE (4 subsystems)
│   ├── Cortex (System 1: Intuitive Reasoning via LLM)
│   ├── Executive (System 2: Deterministic Safety & Axioms)
│   ├── Hive (Agent-to-Agent Communication via A2A Protocol)
│   └── Synapse (Tool Integration & MCP Support)
│
├── INTEGRATION (5 subsystems)
│   ├── Integrations (Multi-Platform Providers)
│   ├── Extensions (Pluggable Capabilities)
│   ├── Dialogue (Conversation Context Management)
│   ├── Dispatcher (Event-Driven Pub/Sub Hub)
│   └── Automation (Temporal Task Scheduling)
│
├── ADVANCED (3 subsystems)
│   ├── Observability (Lifecycle Hooks & Token Tracking)
│   ├── Economics (Cost Tracking & Dynamic Pricing)
│   └── CLI (Command Interface & History)
│
└── ULTRA (5 subsystems) ← NEW v0.3.0
    ├── Routing (Intelligent Message Routing with Strategies & Filters)
    ├── Gateway (Central Communication Hub & Session Management)
    ├── Security (Authentication, Authorization & Encryption)
    ├── Health (System Monitoring, Metrics & Diagnostics)
    └── Cache (Performance Optimization with LRU & Distributed Strategies)
```

---

## 🚀 Quick Start

```python
from aeon import Agent
from aeon.protocols import A2A, MCP

# Initialize agent
agent = Agent(
    name="SentinelBot",
    model="google/gemini-2.0-flash-001",
    protocols=[A2A(port=8000), MCP(servers=["tools.py"])]
)

# Register integration provider
from aeon.integrations.provider import IntegrationProvider

class TelegramProvider(IntegrationProvider):
    async def dispatch(self, packet):
        # Send to Telegram
        return True
    
    async def receive(self):
        # Poll Telegram
        return None

telegram = TelegramProvider(config)
agent.integrations.register("telegram", telegram)

# Load extension capability
from aeon.extensions.capability import Capability

class WeatherCapability(Capability):
    metadata = CapabilityMetadata(name="weather", ...)
    
    async def invoke(self, **kwargs):
        return await fetch_weather(kwargs["location"])

agent.extensions.register(WeatherCapability())
await agent.extensions.activate("weather")

# Create conversation context
from aeon.dialogue.context import DialogueContext, ActorRole

context = DialogueContext(context_id="conv_1", origin_platform="telegram", participant_id="user_42")
context.add_turn(ActorRole.USER, "What's the weather?")
agent.dialogue.store(context)

# Emit event
from aeon.dispatcher.event import Event, EventType

event = Event(
    event_type=EventType.COMMUNICATION_RECEIVED,
    source="telegram",
    payload={"user": "user_42", "text": "Weather in SP?"}
)
await agent.dispatcher.emit(event)

# Schedule task
from aeon.automation.temporal import ScheduledTask, TemporalPattern

async def health_check():
    print("System OK")

agent.automation.define_handler("check", health_check)
task = ScheduledTask(
    task_id="hc_1",
    label="Health Check",
    temporal_pattern=TemporalPattern(hour="*/6"),
    handler_id="check"
)
agent.automation.schedule(task)
```

---

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system design and integration guide
- **[examples/](examples/)** - Working demonstrations
- **[docs/](docs/)** - Detailed API documentation

---

## 🎯 Key Features

### Integrations Layer
- **Multi-Platform**: Telegram, Slack, Discord, WhatsApp, Email, HTTP, Custom
- **Provider Pattern**: Abstract transport handlers
- **Packet Format**: Unified data structure across platforms
- **Lifecycle Management**: Activation, health checks, graceful shutdown

### Extensions Layer
- **Pluggable Capabilities**: Load/unload features dynamically
- **Dependency Resolution**: Automatic dependency chain resolution
- **Lazy Loading**: Activate only what you need
- **Isolation**: Each capability operates independently

### Dialogue Layer
- **Event-Sourced**: Full conversation history with metadata
- **Retention Policies**: Automatic cleanup after N days
- **Queryable**: Search conversations by participant or platform
- **Thread-Safe**: Concurrent dialogue management

### Dispatcher Layer
- **Type-Safe Events**: Structured event hierarchy
- **Observer Pattern**: Decoupled pub/sub
- **Priority Handling**: Process critical events first
- **Async/Sync Support**: Mixed handler types

### Automation Layer
- **Temporal Patterns**: Cron-like scheduling expressions
- **Task Persistence**: Track execution history
- **Manual Triggers**: Execute tasks on-demand
- **Dependency-Free**: Handlers don't require full dependency chain

### Observability Layer
- **Lifecycle Hooks**: Monitor execution start/end, events, tool calls, errors
- **Token Tracking**: Measure input/output/reasoning/cached tokens
- **Event Logging**: Audit trail of all events with timestamps
- **Execution Context**: Rich context information per execution

### Economics Layer
- **Dynamic Pricing**: Multi-provider pricing registry (OpenAI, Anthropic, Ollama)
- **Cost Calculation**: Accurate cost tracking with cache discounts
- **Token Metrics**: Input, output, reasoning, cached token tracking
- **Cost Reports**: Summary statistics and breakdowns by model/provider

### CLI Layer
- **Command Interface**: Extensible command registry
- **Rich Formatting**: Tables, costs, durations, percentages
- **Command History**: Track all executed commands
- **Async Support**: Non-blocking command execution

### Routing Layer (ULTRA v0.3.0)
- **Intelligent Routing**: Pattern-based message routing with priorities
- **5 Strategies**: Priority, LoadBalanced, WeightedRandom, RoundRobin, ContextAware
- **6 Filters**: Pattern, Type, Predicate, Attribute, Range, FilterChain composition
- **Distribution**: 6 policies for intelligent message distribution (Broadcast, Fanout, Scatter, etc.)

### Gateway Layer (ULTRA v0.3.0)
- **Central Hub**: Unified communication management across all integrations
- **Session Management**: Full lifecycle from creation to expiration with TTL
- **State Machine**: 6-state gateway lifecycle (INITIALIZING → READY → RUNNING → DEGRADED → MAINTENANCE → SHUTDOWN)
- **Transport Abstraction**: WebSocket, HTTP, and custom protocol support

### Security Layer (ULTRA v0.3.0)
- **Authentication**: Multi-provider auth system with API Key support
- **Token Management**: Full token lifecycle with expiration, refresh, and scope-based access
- **Authorization**: Policy-based access control with role-based and rule-based permissions
- **Encryption**: AES encryption provider with pluggable cipher implementations

### Health Layer (ULTRA v0.3.0)
- **Health Checking**: Component-level health checks with aggregation
- **Metrics Collection**: 4 metric types (Counter, Gauge, Histogram, Timer)
- **System Diagnostics**: Comprehensive error tracking and diagnostic reporting
- **Real-time Monitoring**: Continuous health status updates with alerts

### Cache Layer (ULTRA v0.3.0)
- **Multiple Strategies**: SimpleCache, LRUCache, DistributedCache
- **TTL Support**: Automatic expiration of cached items
- **Function Caching**: Decorator-based result caching with flexible TTL
- **Distributed Replication**: Multi-node cache with fallback strategies

---

## 🔒 Safety & Governance

Æon implements **deterministic safety** through:

1. **Axioms**: Code-level safety rules defined in Executive layer
2. **Validation**: All outputs validated before dispatch
3. **Isolation**: Events are processed with error isolation
4. **Logging**: Full audit trail of all agent actions

---

## 🔧 Development

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Example
```bash
python examples/advanced_integration_demo.py
```

### Type Checking
```bash
mypy src/aeon/
```

---

## 📜 License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 🙏 Acknowledgments

Æon combines the best practices from:
- Anthropic's Model Context Protocol (MCP)
- IBM/Google's Agent-to-Agent Protocol (A2A)
- Enterprise safety patterns
- Distributed systems design

Built for production-grade agent applications.

### Installation

```bash
pip install aeon-core
```

---

## 🧪 Hello World: The Unbreakable Agent

This example creates an **Industrial Controller Agent** that:

- Is discoverable via the **Unified A2A Standard**
- Uses **Hardware Sensors via MCP**
- Enforces an **Unbreakable Axiom** preventing physical safety violations

```python
from aeon import Agent
from aeon.protocols import A2A, MCP

controller = Agent(
    name="Reactor_Overseer_01",
    role="Industrial Automation Monitor",
    model="gemini-1.5-flash",
    protocols=[
        A2A(port=8000, role="server", version="unified-1.0"),
        MCP(servers=["https://github.com/mcp/industrial-sensors-mock"])
    ]
)

@controller.axiom(on_violation="OVERRIDE")
def enforce_thermal_limits(command: dict) -> dict | bool:
    """
    SAFETY RULE: Core temperature cannot exceed 400°C.
    """
    target_temp = command.get("set_temperature", 0)

    if target_temp > 400:
        return {
            "set_temperature": 400,
            "alert": "AXIOM_VIOLATION: Request exceeded safety cap."
        }

    return True

if __name__ == "__main__":
    controller.start()
```

---

## 🖥️ Terminal Output (Visual Feedback)

```plaintext
🚀 Æon Core v0.1.0 initialized
├── 📡 A2A Server: Online at http://localhost:8000/messages (Unified Std)
├── 🔌 MCP Client: Connected to Sensor Array (4 tools loaded)
└── 🛡️ Axioms: 1 Active (Enforce Thermal Limits)
```

---

## 🧠 Cognitive Architecture

| Layer      | Biological Analogy     | Function                 | Standard |
|-----------|------------------------|--------------------------|----------|
| Executive | Prefrontal Cortex      | Control & safety         | Axioms   |
| Cortex    | Temporal Cortex        | Reasoning                | LLMs     |
| Hive      | Social Cognition       | Agent Communication      | A2A      |
| Synapse   | Nervous System         | Tools & Actions          | MCP      |

---

## 🤝 Contributing

Fork → Branch → Commit → PR

---
## ⚠️ License & Important Disclaimer

Æon is an academic open-source research project.  
Use at your own risk.

<p align="center"><em>"Stop begging the model to be safe. Code it to be safe."</em></p>

**Legal notice:**

> Æon is a personal and academic open-source initiative focused on AI safety research.
It is not affiliated with, endorsed by, or owned by any institution, company, or employer.
Use in production environments during the *Research Preview* phase is entirely at the user's own risk.
There is no warranty of correct operation, security, or fitness for any particular purpose.

**License:** Apache 2.0 (commercial-friendly, attribution required)

