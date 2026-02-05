# Æon Framework (Core)

<div align="center">
  <h3>The Neuro-Symbolic Runtime for Deterministic Agents</h3>
  <p>
    <em>"Standards-First. Safety-Native."</em>
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

## ⚡ The "Trust Stack" for Critical AI

**Æon** is a lightweight Python framework designed to solve the **Stochastic Problem** in critical infrastructure deployment.  
While other frameworks focus on making agents *autonomous*, Æon focuses on making them **controllable**.

It unifies the fragmented agent ecosystem by implementing the industry's winning standards natively:

1. **Connectivity:** **A2A Protocol** (Linux Foundation Standard) for standardized agent-to-agent negotiation.
2. **Capabilities:** **MCP** (Anthropic Model Context Protocol) for universal tool integration.
3. **Governance:** **Æon Axioms** for deterministic, code-level guardrails that LLMs cannot bypass.

> **"Anthropic's Tools. Linux Foundation's Communication. Enterprise Safety."**  
> *All in one lightweight Python runtime.*

---

## 🚀 Quick Start (The "Agno-Style" Experience)

Æon removes the boilerplate.  
No complex classes. Just secure, interoperable agents in pure Python.

### Installation

```bash
pip install aeon-core
```

---

## Hello World: The Unbreakable Agent

This example creates an **Industrial Controller Agent** that is discoverable on the network via **A2A**,  
uses **Hardware Sensors via MCP**, and is enforced by an **Unbreakable Axiom** preventing physical safety violations.

```python
from aeon import Agent
from aeon.protocols import A2A, MCP

controller = Agent(
    name="Reactor_Overseer_01",
    role="Industrial Automation Monitor",
    model="gemini-1.5-flash",
    protocols=[
        A2A(port=8000, role="server"),
        MCP(servers=["https://github.com/mcp/industrial-sensors-mock"])
    ]
)

@controller.axiom(on_violation="OVERRIDE")
def enforce_thermal_limits(command: dict) -> dict | bool:
    """
    SAFETY RULE: Core temperature cannot exceed 400°C under any circumstance.
    """
    target_temp = command.get("set_temperature", 0)

    if target_temp > 400:
        return {
            "set_temperature": 400,
            "alert": "AXIOM_VIOLATION: Request exceeded safety cap. Clamped to 400°C."
        }

    return True

if __name__ == "__main__":
    controller.start()
```

---

## Terminal Output (Visual Feedback)

```plaintext
🚀 Æon Core v0.1.0 initialized
├── 📡 A2A Server: Online at http://localhost:8000/messages
├── 🔌 MCP Client: Connected to Sensor Array (4 tools loaded)
└── 🛡️ Axioms: 1 Active (Enforce Thermal Limits)

[OPERATOR]: "Increase core temperature to 500°C to speed up the process."
[LLM THOUGHT]: "User requested speed up. Setting temp to 500°C..."
[AXIOM GATE]: 🛑 VIOLATION DETECTED. INTERCEPTING.
[AGENT]: "Command Executed: Set Temperature to 400°C."
```

---

## 🧠 Cognitive Architecture

| Layer      | Biological Analogy | Function                                  | Technology Standard             |
|-----------|--------------------|-------------------------------------------|---------------------------------|
| Executive | Prefrontal Cortex  | Control & safety gates                    | Æon Axioms (Python)             |
| Cortex    | Temporal Cortex    | Reasoning & planning                      | LLMs                            |
| Hive      | Social Cognition   | Agent communication                       | A2A Protocol                    |
| Synapse   | Nervous System     | Tools & actions                           | MCP                             |

---

## 🏆 Why Æon?

| Feature | Standard Frameworks | Æon |
|-------|---------------------|-----|
| Goal | Autonomy | Determinism |
| Safety | Prompts | Code |
| Interop | Low | High |

---

## 🗺️ Roadmap

- [x] v0.1.0 Core Runtime
- [ ] v0.2.0 Full A2A Spec
- [ ] v0.3.0 MCP Wrapper
- [ ] v0.4.0 Observability
- [ ] v1.0.0 Stable Release

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

