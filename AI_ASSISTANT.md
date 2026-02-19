# Æon Framework (Core)

<div align="center">
  <h3>Build Your Own Personal AI Assistant</h3>
  <p>
    <em>"Safety-Native. Protocol-First. Extensible by Design."</em>
  </p>
  <p><strong>The Neuro-Symbolic Runtime for Distributed Agents</strong></p>
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

## 🎯 What is Æon Framework?

**Æon v0.3.0** is a comprehensive framework that solves the **Extensibility Problem** in agent systems.  
It enables you to build **your own personal AI assistant** with:

- **Multi-Platform Support**: Telegram, Slack, Discord, WhatsApp, Email, HTTP, and custom providers
- **Safety-First Design**: Axiom-based control with deterministic safety validation
- **Production-Ready**: 16 integrated subsystems across 4 layers (Core, Integration, Advanced, ULTRA)
- **LLM Flexibility**: Support for OpenAI, OpenRouter, Amazon Bedrock, Ollama, and more

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

## 🚀 Getting Started: 5 Minutes to Your First AI Assistant

### 1. Install Æon

```bash
pip install aeon-core
```

### 2. Choose Your LLM Provider

Pick one of the providers below and complete setup:

#### 🟠 **Option A: OpenRouter** (Recommended for Start)

OpenRouter provides a unified API with access to many models (Claude, GPT, Gemini, etc.) through a single endpoint.

**Setup:**
```bash
# Get your API key from https://openrouter.ai
export OPENROUTER_API_KEY="sk-or-xxx..."

# Create config file
cat > config.py << 'EOF'
AGENT_CONFIG = {
    "name": "MyAssistant",
    "model": {
        "provider": "openrouter",
        "model_name": "anthropic/claude-opus-4-6",
        "api_key": "${OPENROUTER_API_KEY}"
    }
}
EOF
```

**In Your Python Code:**
```python
from aeon import Agent

agent = Agent(
    name="MyAssistant",
    model_provider="openrouter",
    model_name="anthropic/claude-opus-4-6",
    api_key="sk-or-xxx..."
)
```

---

#### 🔵 **Option B: OpenAI**

Direct access to GPT models with usage-based billing.

**Setup:**
```bash
# Get your API key from https://platform.openai.com/api-keys
export OPENAI_API_KEY="sk-..."

cat > config.py << 'EOF'
AGENT_CONFIG = {
    "name": "MyAssistant",
    "model": {
        "provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "${OPENAI_API_KEY}"
    }
}
EOF
```

**In Your Python Code:**
```python
from aeon import Agent

agent = Agent(
    name="MyAssistant",
    model_provider="openai",
    model_name="gpt-4o",
    api_key="sk-..."
)
```

---

#### 🔴 **Option C: Amazon Bedrock**

Enterprise-grade LLMs through AWS infrastructure with automatic credential handling.

**Setup Prerequisites:**
```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-east-1"

# Verify Bedrock models are enabled in your AWS account
aws bedrock list-foundation-models --region us-east-1
```

**In Your Python Code:**
```python
from aeon import Agent

agent = Agent(
    name="MyAssistant",
    model_provider="amazon-bedrock",
    model_name="us.anthropic.claude-opus-4-6-v1:0",
    aws_region="us-east-1"
    # No api_key needed - uses AWS SDK chain
)
```

**Advanced: EC2 Instance Setup**
```bash
# Attach IAM role with permissions:
# - bedrock:InvokeModel
# - bedrock:InvokeModelWithResponseStream
# - bedrock:ListFoundationModels

# On EC2 instance:
export AWS_PROFILE=default
export AWS_REGION=us-east-1

# Enable automatic model discovery
aeon config set models.bedrockDiscovery.enabled true
```

---

#### 🟢 **Option D: Local Ollama** (Free! Runs on Your Mac/Linux)

Run LLMs locally without any cloud service. Perfect for development and privacy-focused deployments.

**Setup:**
```bash
# 1. Install Ollama from https://ollama.ai
# On Mac/Linux, simply: brew install ollama

# 2. Start Ollama service (runs on localhost:11434)
ollama serve

# 3. In another terminal, download a model
ollama pull phi3.5        # ~1.9GB - Fast and capable (Recommended for M1)
# or
ollama pull neural-chat    # Optimized for chat
# or
ollama pull llama2          # Meta's Llama 2
```

**In Your Python Code:**
```python
from aeon import Agent

agent = Agent(
    name="MyAssistant",
    model_provider="ollama",
    model_name="phi3.5",
    base_url="http://localhost:11434"  # Default Ollama address
)
```

**Comparison of Ollama Models:**

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| qwen2.5-coder | 1.9GB | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Coding & Reason (M1 optimized) |
| neural-chat | 4.1GB | ⚡⚡⚡ | ⭐⭐⭐ | Chat-optimized |
| llama2 | 3.8GB | ⚡⚡⚡ | ⭐⭐⭐ | General purpose |
| phi | 1.6GB | ⚡⚡⚡⚡ | ⭐⭐⭐ | Lightweight |

---

### 3. Create Your First Agent

```python
from aeon import Agent
from aeon.protocols import A2A, MCP

# Initialize with your chosen provider
agent = Agent(
    name="MyAssistant",
    model_provider="openrouter",  # Change to: openai, amazon-bedrock, or ollama
    model_name="anthropic/claude-opus-4-6",
    api_key="sk-or-xxx..."  # Or use env vars
)

# Your agent is ready!
if __name__ == "__main__":
    agent.start()
    print("✅ Agent is running and ready for messages")
```

---

## 🎯 Next: Add Integrations to Your Assistant

Once your core agent works, add communication integrations:

### Add Telegram Support

```python
from aeon import Agent
from aeon.integrations.provider import IntegrationProvider

# Initialize agent
agent = Agent(
    name="MyAssistant",
    model_provider="openrouter",
    model_name="anthropic/claude-opus-4-6"
)

# Register Telegram integration
class TelegramProvider(IntegrationProvider):
    async def dispatch(self, packet):
        # Send to Telegram
        return True
    
    async def receive(self):
        # Poll for new Telegram messages
        return None

telegram = TelegramProvider(config={"token": "YOUR_TELEGRAM_BOT_TOKEN"})
agent.integrations.register("telegram", telegram)
```

---

## 🔍 LLM Provider Comparison

Choose the right provider for your use case:

| Provider | Best For | Cost | Setup Time | Privacy | Models Available |
|----------|----------|------|------------|---------|------------------|
| **Ollama** | Local development, privacy-critical | Free | 5 min | ✅ On-device | Mistral, Llama2, Phi, Neural-Chat |
| **OpenRouter** | Starting out, trying many models | Pay-as-you-go | 3 min | ⚠️ Cloud | Claude, GPT, Gemini, Mistral, Llama2 |
| **OpenAI** | Production ChatGPT/GPT-4 integration | Pay-as-you-go | 3 min | ⚠️ Cloud | GPT-4o, GPT-4 Turbo, GPT-3.5 |
| **Amazon Bedrock** | Enterprise AWS infrastructure | Pay-as-you-go | 10 min | ⚠️ AWS | Claude, Mistral, Llama2, Cohere, Jurassic |

---

## 💡 Real-World Example: Personal Journal Assistant

Here's a complete example that creates an assistant that helps you maintain a daily journal:

```python
from aeon import Agent
from aeon.dialogue.context import DialogueContext, ActorRole
from aeon.extensions.capability import Capability
import datetime

# 1. Initialize the agent with your LLM choice
agent = Agent(
    name="JournalAssistant",
    model_provider="ollama",  # Using local Ollama for privacy
    model_name="phi3.5"
)

# 2. Create a Journal Capability
class JournalCapability(Capability):
    def __init__(self, journal_file="journal.txt"):
        self.journal_file = journal_file
    
    async def save_entry(self, text: str) -> str:
        """Save today's journal entry"""
        date = datetime.date.today()
        with open(self.journal_file, "a") as f:
            f.write(f"\n=== {date} ===\n{text}\n")
        return f"✅ Journal entry saved for {date}"
    
    async def read_recent(self, days: int = 7) -> str:
        """Read recent entries"""
        with open(self.journal_file, "r") as f:
            return f.read()[-1000:]  # Last 1000 chars

# 3. Register the capability
journal = JournalCapability()
agent.extensions.register(journal)

# 4. Create a conversation
context = DialogueContext(
    context_id="daily_journal",
    origin_platform="cli",
    participant_id="user_1"
)

# 5. Have a conversation with the agent
async def run_journal_session():
    user_input = "Today I learned about AI frameworks. I'm excited about Æon!"
    context.add_turn(ActorRole.USER, user_input)
    
    # Agent processes and generates response
    response = await agent.cortex.reason(
        prompt=user_input,
        context=context
    )
    
    # Save the entry
    await journal.save_entry(user_input)
    
    print(f"Agent: {response}")
    print("✅ Entry saved!")

# Run it
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_journal_session())
```

**Output:**
```
Agent: That's wonderful! Learning about new AI frameworks is always exciting. 
Æon sounds particularly interesting with its focus on safety and extensibility. 
I've recorded your entry for today.
✅ Entry saved!
```

---

## 🛡️ Safety Features in Your Assistant

Æon makes it easy to add safety rules to your assistant:

```python
from aeon import Agent

agent = Agent(
    name="SafeAssistant",
    model_provider="ollama",
    model_name="phi3.5"
)

# Define safety rules (axioms)
@agent.axiom(on_violation="BLOCK")
def no_harmful_content(response: str) -> bool:
    """Prevent harmful content in responses"""
    harmful_keywords = ["illegal", "dangerous", "harmful"]
    return not any(keyword in response.lower() for keyword in harmful_keywords)

@agent.axiom(on_violation="LIMIT")
def respect_rate_limits(request_count: int) -> bool:
    """Limit requests to 100 per hour"""
    return request_count < 100

# Your assistant now enforces these rules automatically
```

---

## 📱 Add Multiple Communication Channels

Once your core agent works with one provider, extend it to multiple platforms:

```python
from aeon import Agent
from aeon.integrations.provider import IntegrationProvider

agent = Agent(
    name="MyAssistant",
    model_provider="openai",
    model_name="gpt-4o"
)

# Support Telegram
class TelegramProvider(IntegrationProvider):
    async def dispatch(self, packet):
        # Send to Telegram API
        pass

# Support Discord
class DiscordProvider(IntegrationProvider):
    async def dispatch(self, packet):
        # Send to Discord API
        pass

# Support Slack
class SlackProvider(IntegrationProvider):
    async def dispatch(self, packet):
        # Send to Slack API
        pass

# Register all
agent.integrations.register("telegram", TelegramProvider())
agent.integrations.register("discord", DiscordProvider())
agent.integrations.register("slack", SlackProvider())

# Now your assistant works on all three platforms!
```

---

## 🌟 Advanced Features: Load Extension Capabilities

```python
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

## 🎓 Learning Resources & Common Questions

### I just installed Æon. What should I do first?

1. **Pick an LLM provider** - Start with Ollama (free, local) or OpenRouter (easy cloud setup)
2. **Create a simple agent** - Use the code example above
3. **Test it works** - Make sure you can send messages and get responses
4. **Add an integration** - Connect to Telegram, Discord, or another platform
5. **Add a capability** - Create a simple function your agent can call

### How do I choose between cloud vs local LLM?

| Choice | When | Examples |
|--------|------|----------|
| **Cloud (OpenAI, OpenRouter, Bedrock)** | You want cutting-edge models, don't mind API costs, want simplicity | Production bots, advanced use cases |
| **Local (Ollama)** | You value privacy, want free, OK with slower responses | Development, testing, personal projects |

**Pro tip:** Start with Ollama for development, switch to cloud for production.

### How do I debug my agent?

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use Æon's built-in observability
from aeon.observability import LifecycleHook

@agent.observe(LifecycleHook.MESSAGE_RECEIVED)
async def log_message(context):
    print(f"📨 Message: {context.message}")

@agent.observe(LifecycleHook.RESPONSE_GENERATED)
async def log_response(context):
    print(f"📤 Response: {context.response}")
```

### Can I use Æon with function calling / tools?

Yes! Use the Synapse subsystem:

```python
from aeon.synapse.mcp import MCPClient

agent = Agent(name="ToolAgent", model_provider="openai")

# Register MCP tools
mcp = MCPClient(servers=["weather-service", "calculator-service"])
agent.synapse.register("tools", mcp)

# Now your agent can call these tools automatically
```

### My agent is running slow. What should I do?

1. **Enable caching** - Use the Cache subsystem (ULTRA layer)
```python
from aeon.cache import LRUCache

agent.cache.configure(
    strategy="lru",
    max_size=1000,
    ttl=3600  # 1 hour
)
```

2. **Use a lighter model** - Mistral is faster than Claude
3. **Add rate limiting** - Prevent overwhelmed endpoints
4. **Monitor costs** - Use the Economics subsystem

---

## 🚨 Troubleshooting

### Error: "Model not found"
**Solution:** Verify the model exists on your provider.
```bash
# For Ollama
ollama list

# For OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | grep "data"
```

### Error: "API key invalid"
**Solution:** Check your credentials.
```bash
# OpenAI
echo $OPENAI_API_KEY  # Should start with sk-

# OpenRouter
echo $OPENROUTER_API_KEY  # Should start with sk-or-

# Ollama (no key needed)
curl http://localhost:11434/api/tags  # Should return model list
```

### Agent not responding
**Solution:** Check connectivity and permissions.
```bash
# Test Ollama
curl http://localhost:11434/api/generate \
  -d '{"model":"phi3.5","prompt":"test"}'

# Test OpenAI
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"test"}]}'
```

---

## 📚 Full Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system design and integration guide
- **[QUICK_START.md](QUICK_START.md)** - Step-by-step getting started
- **[INTEGRATION.md](INTEGRATION.md)** - Multi-platform communication details
- **[ULTRA.md](ULTRA.md)** - Advanced ULTRA layer features
- **[examples/](examples/)** - Working code demonstrations
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

## 🧪 Examples: Building Different Kinds of Agents

### Example 1: Simple Chat Agent (Fastest Start)

The simplest agent - chat with an AI locally:

```python
from aeon import Agent

agent = Agent(
    name="ChatBot",
    model_provider="ollama",
    model_name="phi3.5"
)

async def main():
    response = await agent.cortex.reason(
        prompt="What is machine learning?"
    )
    print(f"Agent: {response}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Try it:**
```bash
pip install aeon-core
brew install ollama
ollama pull phi3.5
python chat_agent.py
```

---

### Example 2: Industrial Controller Agent (Safety-Focused)

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
    model_provider="openai",
    model_name="gpt-4o",
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

### Example 3: Multi-Channel Customer Support Agent

Connect to multiple messaging platforms simultaneously:

```python
from aeon import Agent
from aeon.integrations.provider import IntegrationProvider

agent = Agent(
    name="SupportBot",
    model_provider="openrouter",
    model_name="anthropic/claude-opus-4-6"
)

# Telegram, Discord, Slack integrations
class TelegramProvider(IntegrationProvider):
    async def dispatch(self, packet): pass
    async def receive(self): pass

class DiscordProvider(IntegrationProvider):
    async def dispatch(self, packet): pass
    async def receive(self): pass

class SlackProvider(IntegrationProvider):
    async def dispatch(self, packet): pass
    async def receive(self): pass

# Register all channels
agent.integrations.register("telegram", TelegramProvider())
agent.integrations.register("discord", DiscordProvider())
agent.integrations.register("slack", SlackProvider())

# Your agent now supports 3 platforms with same logic!
```

---

## 🖥️ Terminal Output (Visual Feedback)

```plaintext
🚀 Æon Core v0.3.0-ULTRA initialized
├── 🧠 Cortex: Ready (model=mistral)
├── 🛡️ Executive: Safety Active (2 axioms)
├── 📡 A2A Server: Online at http://localhost:8000/messages
├── 🔌 MCP Client: Connected (4 tools)
├── 📨 Integrations: Telegram, Discord, Slack (READY)
└── 💾 Cache: LRU enabled (1000 items, 1h TTL)
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

---

## 📃 Citation

```bibtex
@misc{Aeon Framework,
  author = {LIMA, Richardson Edson de},
  title = {Aeon Framework - The Neuro-Symbolic Runtime for Deterministic AI Agents. "Standards-First. Safety-Native."},
  year = {2026},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/richardsonlima/aeon-core.git}}
}
```