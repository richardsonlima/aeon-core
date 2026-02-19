# Æon Framework (Core)

<div align="center">

[![Version](https://img.shields.io/badge/version-v0.4.0--ULTRA-blue.svg)](https://github.com/richardsonlima/aeon-core)
[![Python Versions](https://img.shields.io/badge/python-3.10+-blue.svg)](https://github.com/richardsonlima/aeon-core)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-research--preview-orange.svg)](https://github.com/richardsonlima/aeon-core)
[![Architecture](https://img.shields.io/badge/architecture-neuro--symbolic-purple.svg)](https://github.com/richardsonlima/aeon-core)
[![UV Compatible](https://img.shields.io/badge/UV-Compatible-5C63FF.svg)](https://github.com/astral-sh/uv)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

  <p>
      <a href="README.md">English</a> | <a href="README_pt.md">Português</a>
  </p>
  
**The Deterministic Runtime for Safety-Critical AI Agents with Autonomous Native Capabilities**

</div>

## 🌟 Overview

Æon is a comprehensive, production-ready framework for building **Neuro-Symbolic AI agents**. Unlike stochastic-only systems, Æon combines the intuitive reasoning of LLMs (**System 1**) with the deterministic safety and control of code-level axioms (**System 2**).

It establishes a standard "Trust Stack" that enables agents to be **Safety-Native**, **Protocol-First**, and **Extensible by Design**. With deep integration of the **Agent-to-Agent (A2A)** and **Model Context Protocol (MCP)**, Æon allows you to build interoperable agent ecosystems that can collaborate safely in high-stakes environments.

## 📋 What's New in v0.4.0 (ULTRA)

- **🔌 Autonomous Native Engine**: Built-in support for browser automation (Playwright), persistent event-sourced memory (SQLite), and granular Trust Levels.
- **🏗️ Developer First CLI**: Transform from scripts to projects with the new `aeon` command. Scaffold, run, and serve agents in seconds.
- **🚀 Declarative Runtime**: Define agents via `aeon.yaml` and launch a full **Gateway Server** for production deployments.
- **🛡️ Enhanced Safety executive**: Improved SIL-4 compliant axioms with TMR (Triple Modular Redundancy) reasoning for mission-critical reliability.
- **🔄 Deep Persistence**: Event-sourced memory system that survives reboots and provides a complete audit trail of agent thoughts and actions.
- **⏰ Temporal Capabilities**: Native scheduling for cron jobs and delayed tasks, enabling agents to act autonomously over time.

## 📋 What's New in v0.3.0 (ULTRA Phase)

- **Routing Layer**: Intelligent pattern-based message routing with 5 distinct strategies (Priority, Weighted, etc.).
- **Gateway Layer**: Centralized communication hub with session management and TTL support.
- **Security Layer**: Policy-based access control, AES encryption, and multi-provider authentication.
- **Health Layer**: Real-time system monitoring, metrics collection (Counter, Gauge, etc.), and diagnostics.

## ✨ Why Choose Æon?

- **Deterministic Safety**: Stop begging the model to be safe. Enforce safety at the runtime level with **Axioms**.
- **Neuro-Symbolic Core**: The perfect balance between LLM intuition and hard-coded rules.
- **Protocol-First**: Native support for **A2A** (Agent-to-Agent) and **MCP** (Model Context Protocol).
- **Enterprise Ready**: Built with observability, economics (cost tracking), and health monitoring from the ground up.
- **Local-First & Private**: Run entirely on your hardware with Ollama or connect to premium cloud providers.
- **Stark visual Feedback**: Terminal-native UI components for monitoring agent execution in real-time.

## 📦 Installation

### Using UV (Recommended)

[UV](https://github.com/astral-sh/uv) is the fastest way to manage Æon dependencies:

```bash
# Clone the repository
git clone https://github.com/richardsonlima/aeon-core.git
cd aeon-core

# Create environment and install
uv sync
```

### Using pip

```bash
pip install aeon-core
```

## 🚀 Quick Start Examples

### 1. Developer Workflow (CLI)

From zero to agent in three commands:

```bash
# Initialize a new project
aeon init my-safety-agent

# Configure your model in aeon.yaml
# (Default: google/gemini-2.0-flash-001)

# Run a task interactively
aeon run "Check reactor thermal status"

# Start the production gateway
aeon serve --port 8000
```

### 2. Create a Safety-Native Agent (Code)

```python
from aeon import Agent
from aeon.protocols import A2A, MCP

# Initialize the agent with the Trust Stack
agent = Agent(
    name="Sentinel",
    model="google/gemini-2.0-flash-001",
    protocols=[A2A(port=8000), MCP(servers=["industrial_tools.py"])]
)

# Define an Unbreakable Axiom (System 2)
@agent.axiom(on_violation="OVERRIDE")
def safety_limit(command: dict) -> bool | dict:
    """SAFETY RULE: Power output cannot exceed 100%."""
    if command.get("power", 0) > 100:
        return {"power": 100, "warning": "AXIOM_LIMIT_REACHED"}
    return True

if __name__ == "__main__":
    agent.start()
```

### 3. Autonomous Browser Workflow

```python
from aeon import Agent
from aeon.core.config import TrustLevel

agent = Agent(name="Researcher", trust_level=TrustLevel.FULL)

async def main():
    # Agent can autonomously browse and remember
    response = await agent.run("Find the latest paper on SIL-4 safety and save the summary.")
    print(f"Agent Action: {response.last_thought}")

# Run via CLI: aeon run ...
```

## 🔌 Enhanced MCP (Model Context Protocol) v2.0

Æon now features a completely redesigned MCP implementation that provides robust, production-ready integration with external tools:

- **Synapse Layer**: Unified tool discovery and invocation.
- **Standard Support**: Full compliance with the latest MCP specification.
- **Multi-Server**: Connect to multiple MCP servers simultaneously (Stdio, SSE).
- **Type Safety**: Automatic parameter validation for tool calls.

## 📖 Architecture: The 16 Subsystems

Æon is organized into 4 distinct layers, each providing critical functionality for advanced agents:

### 1. CORE (System 1 & 2)
- **Cortex**: Neuro-reasoning via LLMs.
- **Executive**: Deterministic control via Axioms.
- **Hive**: Standardized communication (A2A).
- **Synapse**: Tool integration (MCP).

### 2. INTEGRATION
- **Integrations**: Multi-platform connectivity (Telegram, Discord, Slack).
- **Extensions**: Dynamic capability loading.
- **Dialogue**: Persistent, event-sourced conversation history.
- **Dispatcher**: Event-driven pub/sub architecture.
- **Automation**: Temporal task scheduling (Cron/Interval).

### 3. ADVANCED
- **Observability**: Life-cycle hooks and audit trails.
- **Economics**: Real-time token tracking and cost calculation.
- **CLI**: Premium developer interface.

### 4. ULTRA (Enterprise)
- **Routing**: High-performance message distribution.
- **Gateway**: Centralized session and transport management.
- **Security**: Authentication, authorization, and encryption.
- **Health**: System diagnostics and metrics.

## 🧪 Hello World: Industrial Overseer

```python
from aeon import Agent
from aeon.protocols import A2A, MCP

controller = Agent(
    name="Reactor_Overseer_01",
    role="Industrial Automation Monitor",
    model="gemini-1.5-flash",
    protocols=[
        A2A(port=8000),
        MCP(servers=["mcp-server-industrial"])
    ]
)

@controller.axiom(on_violation="REJECT")
def enforce_safety(command: dict):
    # Any command attempting to disable cooling is rejected
    if command.get("action") == "DISABLE_COOLING":
        return False
    return True

if __name__ == "__main__":
    controller.start()
```

## 🖥 Terminal Output (Visual Feedback)

```plaintext
🚀 Æon Core v0.4.0-ULTRA initialized
├── 📡 A2A Server: Online at http://0.0.0.0:8000 (Unified Standard)
├── 🔌 MCP Client: Connected (4 tools loaded: read_sensor, adjust_valve...)
├── 🛡️ Axioms: 2 Active (enforce_safety, thermal_limit)
└── 🧠 Brain: Gemini-2.0-Flash (Ready)
```

## 🤝 Community & Support

- **[GitHub Issues](https://github.com/richardsonlima/aeon-core/issues)**: Report bugs or request features.
- **[Aeon Landing Page](https://www.richardsonlima.com.br/aeon/)**: Visit our landing page for deep dives.
- **[Contributing Guide](CONTRIBUTING.md)**: Learn how to join the mission.

## 📝 Citing this Project

If you use Æon in your research, please cite it as:

```bibtex
@software{richardsonlima-aeon-framework,
  author = {LIMA, Richardson Edson de},
  title = {Aeon Framework: The Neuro-Symbolic Runtime for Deterministic AI Agents},
  url = {https://github.com/richardsonlima/aeon-core},
  version = {0.4.0-ULTRA},
  year = {2026},
}
```

## 👨💻 Author

**Richardson Lima (Rick) **

- GitHub: [richardsonlima](https://github.com/richardsonlima)
- LinkedIn: [richardsonlima](https://www.linkedin.com/in/richardsonlima)

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

Made with ❤️ for AI Safety by Richardson Lima.