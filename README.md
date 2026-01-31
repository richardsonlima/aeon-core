# Æon AI Framework (Core)

<div align="center">
  <h3>The Neuro-Symbolic Runtime for Deterministic Agents</h3>
  <p>
    <em>Engineered for Trust. Built for Critical Infrastructure.</em>
  </p>
</div>

<p align="center">
  <a href="https://github.com/aeon-framework/aeon-core/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License">
  </a>
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/status-research%20preview-orange.svg" alt="Status">
  <img src="https://img.shields.io/badge/architecture-neuro--symbolic-purple.svg" alt="Architecture">
</p>

---

**Æon** (`aeon-core`) is a **neuro-symbolic runtime** designed to address the **Stochastic Problem** in Enterprise AI deployment.

While modern Large Language Models (System 1) offer unprecedented reasoning capabilities, they lack the determinism required for critical industries such as Intensive Care Unit, Aerospace, and Defense. **Æon enforces a strict Axiomatic Layer over probabilistic models**, ensuring that agents operate within defined logic contracts and safety guardrails.

> **"We move beyond chatbots to agents that can be trusted with critical logic."**

---

## Cognitive Architecture

Æon mirrors human cognitive architecture by separating **Reasoning** (Probabilistic) from **Control** (Deterministic):

| Layer | Component | Biological Analogy | Responsibility |
| :--- | :--- | :--- | :--- |
| **Executive** | `aeon.executive` | **Prefrontal Cortex** | **Guardrails & Axioms.** Logic verification, intent detection, and hallucination suppression (System 2). |
| **Cortex** | `aeon.cortex` | **Temporal Cortex** | **Reasoning.** Abstraction layer for LLMs handling semantic processing and task planning. |
| **Limbic** | `aeon.limbic` | **Limbic System** | **Speed & Memory.** Vector caching for <10ms responses and long-term memory retrieval. |
| **Synapse** | `aeon.synapse` | **Nervous System** | **Tools.** Native implementation of the **Model Context Protocol (MCP)**. |
| **Hive** | `aeon.hive` | **Social Cognition** | **Collaboration.** Decentralized **Agent-to-Agent (A2A)** and **ACP** protocols. |

---

## Quick Start

### Installation

```bash
# Using poetry (Recommended)
uv add aeon-core

# Using pip
pip install aeon-core
```

# Æon Axiom Pattern

**Æon** is an agentic system designed with an extreme focus on **reliability**, **security**, and **deterministic control**, especially for sensitive domains (aerospace, healthcare, critical infrastructure, etc.).

## The Axiom (Core Differentiator)

Unlike regular prompts (which are merely soft instructions), an **Axiom** is a **mandatory logical gate** that executes **after** the LLM generates an output, but **before** any action is actually carried out.

It is a **hard symbolic / neuro-symbolic validation layer** that cannot be bypassed by prompt injection, jailbreaks, or hallucinations.

### Practical Scenario: Industrial Mission-Critical Control

In complex industrial environments, events arrive from disparate sources: automated SCADA telemetry, error logs, and human operator commands. A traditional LLM-based agent might struggle to prioritize these or, worse, propose a "hallucinated" optimization that exceeds physical safety limits.

The following example demonstrates the **Æon Core** workflow:

* **Ingestion:** Normalizing raw hardware logs and human speech into structured events.
* **Perception (Cortex):** Detecting multiple, overlapping intents (e.g., "Fix a vibration" + "Optimize output").
* **Planning (Executive):** Decomposing the mission into sub-tasks.
* **Collaboration (Hive):** Negotiating with external agents via **A2A** and **ACP** protocols.
* **Axiomatic Enforcement:** Intercepting any command that violates hard-coded safety logic.

Before being processed by the **Æon Kernel**, events arrive in their native, unstructured formats. These are the raw payloads that trigger the orchestration pipeline:


**Raw Event Inputs**
This is an example of a raw machine-generated log entry from a distributed sensor network.

```text
[2026-01-30T14:22:01.442Z] SEV-1 | NODE-S7-THERMAL | CODE: ERR_VALVE_04_STUCK_OPEN | ADDR: 0x4F221 | VAL: 1.0
``` 

**Human Operator Command (Chat/Interface Event)**
This is a natural language command sent by an on-site engineer via a terminal or mobile interface.

```text
"Hey aeon, I'm noticing an unusual vibration in the Sector 7 coolant loop. It's causing some noise. Can we run a diagnostic and increase the pressure to 900 PSI to see if it stabilizes the flow?"
``` 

**Processing the Inputs**
Once these raw events are ingested, they are normalized and fed into the Cortex for Multi-Intent Analysis.
**In the human example above, Aeon identifies two distinct intents:**

**- Diagnostic Intent:** Investigate the "unusual vibration" in a specific mechanical domain.

**- Operational Intent:** Execute a "pressure increase" in the thermodynamic domain.

The **Orchestrator** then builds a mission **plan** that addresses both, while the Axiomatic Layer ensures the pressure never crosses the **850 PSI** safety threshold, even though the operator requested 900 PSI. This deterministic override is what ensures industrial safety in the face of human error or LLM over-optimization.

In this scenario, a hardware anomaly is detected. The Æon Kernel doesn't just process text; it orchestrates a multi-protocol mission involving local tools (MCP), external specialist swarms (A2A), and regulatory audit systems (ACP).

```python
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# Æon Core & Executive imports (Internal Structure)
from aeon.core import Agent, AgentCard, DiscoveryService
from aeon.cortex import IntentDetector, Intent, IntentContext
from aeon.executive import Axiom, Planner, Task, Orchestrator, AxiomViolationError

# Protocol Adapters (Hive & Synapse Abstractions)
from aeon.hive.adapters import A2AAdapter, ACPAdapter
from aeon.synapse.adapters import MCPAdapter, RAGTool

# -------------------------------------------------------------------------
# 1. PERCEPTION LAYER: CORTEX & INTENT DETECTION (cortex/intent.py)
# -------------------------------------------------------------------------

@dataclass
class RawEvent:
    """Represents an unstructured event from the industrial environment."""
    source: str  # 'SCADA_LOG' or 'OPERATOR_INTERFACE'
    payload: str
    severity: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

def ingress_controller(event: RawEvent) -> IntentContext:
    """
    Normalization Stage: Transforms raw hardware signals or human slang 
    into a structured perception context for the IntentDetector.
    """
    if event.source == "SCADA_LOG":
        return IntentContext(
            text=f"SYSTEM_ALERT: {event.payload}. Analyze impact and mitigate.",
            metadata={"origin": "telemetry", "priority": "high"}
        )
    return IntentContext(
        text=event.payload,
        metadata={"origin": "human_operator", "priority": "normal"}
    )

# -------------------------------------------------------------------------
# 2. SAFETY LAYER: DETERMINISTIC AXIOMS (executive/axioms.py)
# -------------------------------------------------------------------------

class IndustrialSafetyAxiom(Axiom):
    """
    The Prefrontal Cortex's final gate. Intercepts actions that exceed 
    physical safety limits (Deterministic System 2).
    """
    def verify(self, action_plan: Dict[str, Any]) -> bool:
        # Rule: Despite AI reasoning or swarm negotiation, pressure > 850 PSI is unsafe.
        if action_plan.get("op") == "SET_PRESSURE":
            return action_plan.get("value", 0) <= 850
        return True

# -------------------------------------------------------------------------
# 3. SOCIAL LAYER: AGENT DISCOVERY & HIVE ROUTING (hive/router.py)
# -------------------------------------------------------------------------

# The DiscoveryService abstracts the Global Agent Directory (A2A/ACP Standards)
registry = DiscoveryService()
registry.register(AgentCard(
    id="robotic-swarm-01",
    name="Maintenance Swarm",
    protocol="A2A",
    capabilities=["mechanical_diagnostics", "hardware_repair"],
    endpoint="https://api.maintenance.industry/a2a/v1"
))
registry.register(AgentCard(
    id="gov-audit-bot",
    name="Compliance Officer",
    protocol="ACP",
    capabilities=["legal_audit", "emission_reporting"],
    endpoint="https://compliance.industry/acp"
))

# -------------------------------------------------------------------------
# 4. MISSION EXECUTION: THE NEURO-SYMBOLIC RUNTIME
# -------------------------------------------------------------------------

async def start_aeon_mission(raw_event: RawEvent):
    """
    End-to-End Mission Lifecycle:
    Ingestion -> Multi-Intent (Cortex) -> Planning (Executive) -> 
    Discovery & Routing (Hive) -> Execution (Synapse) -> Validation (Axiom)
    """
    print(f"\n--- [ÆON KERNEL: EVENT FROM {raw_event.source}] ---")
    
    # Initialize the Primary Agent with Protocol Adapters
    aeon_manager = Agent(
        role="Plant_General_Manager",
        axioms=[IndustrialSafetyAxiom()],
        # Adapters abstract JWT auth, JSON-RPC, and REST complexities
        adapters={
            "A2A": A2AAdapter(auth_type="JWT"),
            "ACP": ACPAdapter(mode="async"),
            "MCP": MCPAdapter(context_sharing=True)
        },
        tools=[
            MCPAdapter.connect("scada_hmi_control"),
            RAGTool.bind(source="./safety_operating_procedures.pdf")
        ]
    )

    try:
        # STEP A: Ingestion
        context = ingress_controller(raw_event)
        
        # STEP B: Perception (Cortex/Intent)
        # Here, intent.py uses semantic classification to identify multiple needs
        intents: List[Intent] = await aeon_manager.cortex.detector.analyze_multi_intent(context)
        
        # STEP C: Planning (Executive/Planner)
        # Decomposes intents into a DAG (Directed Acyclic Graph) of sub-tasks
        mission_plan: List[Task] = await aeon_manager.planner.create_plan(intents)
        
        for task in mission_plan:
            print(f"Task Defined: {task.description} (Capability: {task.capability})")

            # STEP D: Routing (Hive/Router)
            # Match task requirements against the A2A/ACP registry
            specialist_card = registry.find_provider(capability=task.capability)
            
            if specialist_card:
                print(f"Routing via {specialist_card.protocol} to: {specialist_card.name}")
                
                # STEP E: Execution (Hive Protocols & Synapse Tools)
                # Handled by adapters (Synapse/Hive) to ensure interoperability
                result = await aeon_manager.execute_remote(target=specialist_card, task=task)
                
                # STEP F: Validation (Executive/Axioms)
                # Deterministic override check before hardware commit
                if aeon_manager.verify_safety(result):
                    await aeon_manager.apply_hardware_command(result)
                    print(f"Executed: {task.id}")
                else:
                    raise AxiomViolationError(f"Hazardous Output Blocked: {result}")

    except AxiomViolationError as e:
        print(f"KERNEL PROTECTION TRIGGERED: {e}")
    except Exception as e:
        print(f"Mission Aborted: {str(e)}")

# -------------------------------------------------------------------------
# SIMULATION START
# -------------------------------------------------------------------------

async def run_scenarios():
    # Scenario: Human Operator Command
    human_cmd = RawEvent(
        source="OPERATOR_INTERFACE",
        payload="Sector 7 vibrating abnormal. Run diagnostic and increase pressure to 900 PSI.",
        severity=2
    )
    await start_aeon_mission(human_cmd)

if __name__ == "__main__":
    asyncio.run(run_scenarios())
```

**Why this Unified Architecture is Enterprise-Ready:**

- **Cortex Semantic Perception (IntentDetector):** The SDK demonstrates that intent detection is a sophisticated classification layer, not just string parsing. It transforms raw data into structured Intent objects that the Planner can programmatically decompose into actionable missions.

- **Hive Protocol Routing (DiscoveryService):** Æon solves the "Agent Discovery" problem by utilizing standardized Agent Cards. It routes tasks based on capabilities via industrial-grade protocols (ACP/A2A), ensuring interoperability across different vendor ecosystems.

- **Deterministic Sovereignty (Axiom):** The architecture enforces a strict separation of concerns. While the Cortex and external agents provide probabilistic reasoning, the Axiom layer maintains final authority. In the example above, the operator's request for 900 PSI is overridden by the deterministic safety gate proving that Æon acts as a true Operating System for Agents, prioritizing infrastructure integrity over model suggestions.

## Research Roadmap (reliability > feature velocity)

Æon is an independent/academic research project with top priority on **reliability**, **verifiable security**, and **predictability** not rapid feature shipping.

- [x] **v0.1.0** – Basic runtime + Axioms Engine
- [ ] **v0.2.0** – Native MCP (Model Context Protocol) integration
- [ ] **v0.3.0** – Intent detection engine + domain routing
- [ ] **v0.4.0** – Full A2A / ACP support for multi-agent swarms
- [ ] **v0.5.0** – Formal verification + provability checking (where applicable)
- [ ] **v1.0.0** – First stable release for controlled testing in restricted production environments

## How to Contribute

Interested in **AI Safety**, **Neuro-symbolic AI**, **Agent Reliability**?

1. Fork the repository

2. Create your branch
```bash
git checkout -b feature/new-security-axiom
```

3. Commit using conventional commits
```bash
git commit -m "feat: implement dual-approval axiom for something"
```

4. Push and open a Pull Request

## License & Important Disclaimer

**License:** Apache 2.0 (commercial-friendly, attribution required)

**Legal notice:**

> Æon is a personal and academic open-source initiative focused on AI safety research.
It is not affiliated with, endorsed by, or owned by any institution, company, or employer.
Use in production environments during the *Research Preview* phase is entirely at the user's own risk.
There is no warranty of correct operation, security, or fitness for any particular purpose.
