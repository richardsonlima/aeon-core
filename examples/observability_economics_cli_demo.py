#!/usr/bin/env python
"""
Complete example demonstrating Observability, Economics, and CLI modules in Æon Framework v0.3.0.

This example shows:
1. Lifecycle hooks with token tracking
2. Cost calculation and reporting
3. CLI commands for agent control
4. Integration with all framework layers
"""

import asyncio
from datetime import datetime
from uuid import uuid4

# Core framework
from aeon.core.agent import Agent
from aeon.hive.protocol import A2AConfig
from aeon.synapse.adapter import MCPConfig

# Observability
from aeon.observability.hook import ExecutionContext, EventType
from aeon.observability.tracker import TokenTrackingHook, EventLogger

# Economics
from aeon.economics.tracker import CostTracker
from aeon.economics.pricing import ModelPricingRegistry, ProviderType

# CLI
from aeon.cli.interface import CommandInterface, CLICommand, CommandResult, CommandStatus
from aeon.cli.formatter import format_cost, format_tokens, format_table


# ============================================================================
# EXAMPLE 1: Lifecycle Hooks with Token Tracking
# ============================================================================

async def example_observability():
    """Demonstrate lifecycle hooks and token tracking."""
    print("\n" + "="*80)
    print("EXAMPLE 1: OBSERVABILITY - Lifecycle Hooks & Token Tracking")
    print("="*80 + "\n")
    
    # Create execution context
    execution_id = str(uuid4())[:8]
    context = ExecutionContext(
        execution_id=execution_id,
        agent_name="ClaudeAgent-v3",
        event_type=EventType.EXECUTION_START,
    )
    
    # Simulate execution metrics
    context.interaction_count = 5
    context.tool_calls = 3
    context.reasoning_steps = 8
    context.validation_checks = 2
    context.safety_checks = 1
    
    context.input_tokens = 2_500
    context.output_tokens = 1_200
    context.reasoning_tokens = 500
    context.cached_tokens = 100
    
    print(f"Execution Context: {execution_id}")
    print(f"Agent: {context.agent_name}")
    print(f"Input Tokens: {format_tokens(context.input_tokens)}")
    print(f"Output Tokens: {format_tokens(context.output_tokens)}")
    print(f"Reasoning Tokens: {format_tokens(context.reasoning_tokens)}")
    print(f"Cached Tokens: {format_tokens(context.cached_tokens)} (50% discount)")
    print(f"\nInteractions: {context.interaction_count}")
    print(f"Tool Calls: {context.tool_calls}")
    print(f"Reasoning Steps: {context.reasoning_steps}")
    print(f"Validation Checks: {context.validation_checks}")
    print(f"Safety Checks: {context.safety_checks}")
    
    # Initialize tracking hook
    tracker = TokenTrackingHook()
    
    # Emit events
    await tracker.on_execution_start(context)
    print(f"\n[*] Execution started - hook notified")
    
    context.tool_calls = 5  # Updated tool calls
    await tracker.on_tool_call(context, "read_file", {"path": "/tmp/example.txt"})
    print(f"[*] Tool call tracked")
    
    context.status = "completed"
    context.duration_ms = 2500.0
    await tracker.on_execution_end(context)
    print(f"[*] Execution completed")
    
    # Get summary
    summary = tracker.get_execution_summary()
    print(f"\n[Summary] Executions: {summary['execution_count']}")
    print(f"[Summary] Total tokens: {format_tokens(summary['total_usage']['total_tokens'])}")


# ============================================================================
# EXAMPLE 2: Cost Calculation & Reporting
# ============================================================================

async def example_economics():
    """Demonstrate cost tracking and pricing."""
    print("\n" + "="*80)
    print("EXAMPLE 2: ECONOMICS - Cost Tracking & Reporting")
    print("="*80 + "\n")
    
    # Initialize cost tracker with pricing registry
    registry = ModelPricingRegistry()
    tracker = CostTracker(registry)
    
    # Record multiple executions with different models
    executions = [
        ("gpt-5", 1000, 500, 0, 100),        # Reasoning
        ("gpt-5-mini", 2000, 800, 200, 50),  # With cache
        ("claude-3-opus", 3000, 1200, 0, 0), # Expensive model
        ("gpt-oss-20b", 500, 300, 0, 0),     # Local (free)
    ]
    
    for i, (model, input_toks, output_toks, cached_toks, reasoning_toks) in enumerate(executions):
        exec_id = f"exec-{i+1}"
        cost = tracker.record_execution(
            execution_id=exec_id,
            model_id=model,
            input_tokens=input_toks,
            output_tokens=output_toks,
            cached_tokens=cached_toks,
            reasoning_tokens=reasoning_toks,
            duration_ms=1000.0 + i * 500,
            success=True,
        )
        print(f"[{exec_id}] {model}: {format_cost(cost.total_cost)}")
    
    # Generate report
    report = tracker.get_report()
    print(f"\n[Report] Total Executions: {report.total_executions}")
    print(f"[Report] Total Cost: {format_cost(report.total_cost)}")
    print(f"[Report] Total Tokens: {format_tokens(report.total_tokens)}")
    print(f"[Report] Avg Cost/Exec: {format_cost(report.avg_cost_per_execution)}")
    print(f"[Report] Cache Savings: {format_cost(report.savings_from_cache)}")
    
    # Cost breakdown by model
    print(f"\n[Cost Breakdown]")
    for model, cost in report.cost_by_model.items():
        print(f"  {model}: {format_cost(cost)}")
    
    # Cost breakdown by provider
    print(f"\n[Provider Breakdown]")
    for provider, cost in report.cost_by_provider.items():
        print(f"  {provider}: {format_cost(cost)}")
    
    # List available models
    print(f"\n[Available Models]")
    models = registry.list_models()
    model_table = [
        {
            "Model": m,
            "Provider": registry.get_model_pricing(m).provider.value,
            "Input": f"${registry.get_model_pricing(m).input_price_per_1m:.4f}/1M",
            "Output": f"${registry.get_model_pricing(m).output_price_per_1m:.4f}/1M",
        }
        for m in models[:5]  # Show first 5
    ]
    table = format_table(model_table, style="simple")
    print(table)


# ============================================================================
# EXAMPLE 3: CLI Commands
# ============================================================================

class StatusCommand(CLICommand):
    """Command to show agent status."""
    
    def __init__(self):
        super().__init__(
            name="status",
            description="Show agent status and metrics"
        )
    
    async def execute(self, **kwargs) -> CommandResult:
        """Execute status command."""
        status_info = {
            "agent_name": "ÆonAgent-v0.3.0",
            "status": "READY",
            "uptime_seconds": 3600,
            "total_executions": 42,
            "total_cost": "$1.23",
            "layers": "8 (Core + 5 Integration + 3 Advanced)",
        }
        return CommandResult(
            status=CommandStatus.COMPLETED,
            output=status_info,
            message="Status retrieved",
        )


class CostCommand(CLICommand):
    """Command to show cost statistics."""
    
    def __init__(self, cost_tracker: CostTracker):
        super().__init__(
            name="costs",
            description="Show cost statistics"
        )
        self.tracker = cost_tracker
    
    async def execute(self, **kwargs) -> CommandResult:
        """Execute cost command."""
        report = self.tracker.get_report()
        return CommandResult(
            status=CommandStatus.COMPLETED,
            output=report.to_dict(),
            message="Cost report generated",
        )


async def example_cli():
    """Demonstrate CLI commands."""
    print("\n" + "="*80)
    print("EXAMPLE 3: CLI - Command Interface")
    print("="*80 + "\n")
    
    # Create CLI interface
    cli = CommandInterface()
    
    # Register commands
    cli.register_command(StatusCommand())
    
    # Create cost tracker for demo
    registry = ModelPricingRegistry()
    tracker = CostTracker(registry)
    tracker.record_execution("cmd-1", "gpt-5-mini", 1000, 500)
    cli.register_command(CostCommand(tracker))
    
    # List available commands
    commands = cli.list_commands()
    print(f"Available Commands: {', '.join(commands)}\n")
    
    # Execute status command
    print("[>] Executing: status")
    result = await cli.execute_command("status")
    if result.is_success():
        for key, value in result.output.items():
            print(f"    {key}: {value}")
    
    # Execute costs command
    print("\n[>] Executing: costs")
    result = await cli.execute_command("costs")
    if result.is_success():
        cost_info = result.output
        print(f"    Total Executions: {cost_info['total_executions']}")
        print(f"    Total Cost: {format_cost(cost_info['total_cost'])}")


# ============================================================================
# EXAMPLE 4: Integration with Agent
# ============================================================================

async def example_agent_integration():
    """Demonstrate integration with Agent class."""
    print("\n" + "="*80)
    print("EXAMPLE 4: INTEGRATION - All Layers Together")
    print("="*80 + "\n")
    
    # Create agent
    agent = Agent(
        name="ÆonMaster-v0.3.0",
        model="gpt-5",
        protocols=[],  # Empty for demo
    )
    
    print(f"Agent: {agent.name}")
    print(f"System Prompt Lines: {len(agent.system_prompt.split(chr(10)))}")
    
    # Check subsystems
    subsystems = {
        "Cortex (Reasoning)": agent.cortex is not None,
        "Executive (Safety)": agent.executive is not None,
        "Integrations": hasattr(agent, 'integrations') and agent.integrations is not None,
        "Extensions": hasattr(agent, 'extensions') and agent.extensions is not None,
        "Dialogue": hasattr(agent, 'dialogue') and agent.dialogue is not None,
        "Dispatcher": hasattr(agent, 'dispatcher') and agent.dispatcher is not None,
        "Automation": hasattr(agent, 'automation') and agent.automation is not None,
        "Observability": hasattr(agent, 'observability') and agent.observability is not None,
        "Economics": hasattr(agent, 'economics') and agent.economics is not None,
        "CLI": hasattr(agent, 'cli') and agent.cli is not None,
    }
    
    print(f"\n[✓] Subsystems Initialized:")
    for subsystem, initialized in subsystems.items():
        status = "✓ ACTIVE" if initialized else "✗ INACTIVE"
        print(f"  {status}: {subsystem}")
    
    # Register hooks
    tracking_hook = TokenTrackingHook()
    event_logger = EventLogger(verbose=False)
    
    agent.observability.register(tracking_hook)
    agent.observability.register(event_logger)
    
    print(f"\n[✓] Hooks registered: {len(agent.observability.hooks)}")
    
    # Record a sample execution
    print(f"\n[✓] Recording sample execution...")
    cost = agent.economics.record_execution(
        execution_id="agent-demo-1",
        model_id="gpt-5-mini",
        input_tokens=2500,
        output_tokens=1200,
        cached_tokens=100,
        reasoning_tokens=300,
        duration_ms=2500.0,
        success=True,
    )
    
    print(f"    Execution Cost: {format_cost(cost.total_cost)}")
    print(f"    Total Tokens: {format_tokens(cost.input_tokens + cost.output_tokens)}")
    
    # Get report
    report = agent.economics.get_report()
    print(f"\n[✓] Economics Report:")
    print(f"    Total Executions: {report.total_executions}")
    print(f"    Total Cost: {format_cost(report.total_cost)}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all examples."""
    print("\n" + "#"*80)
    print("# ÆON FRAMEWORK v0.3.0 - OBSERVABILITY, ECONOMICS & CLI DEMONSTRATION")
    print("#"*80)
    
    await example_observability()
    await example_economics()
    await example_cli()
    await example_agent_integration()
    
    print("\n" + "#"*80)
    print("# DEMONSTRATION COMPLETE")
    print("#"*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
