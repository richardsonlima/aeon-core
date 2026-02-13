"""Cost tracking and reporting for agent executions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from .pricing import ModelPricingRegistry, ModelPricing, ProviderType


@dataclass
class ExecutionCost:
    """Cost information for a single execution."""
    
    execution_id: str
    model_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    
    # Costs (in USD)
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    
    # Metadata
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "model_id": self.model_id,
            "timestamp": self.timestamp.isoformat(),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "total_cost": self.total_cost,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class CostReport:
    """Summary report of costs across executions."""
    
    total_executions: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    
    # Breakdown by model
    cost_by_model: Dict[str, float] = field(default_factory=dict)
    cost_by_provider: Dict[str, float] = field(default_factory=dict)
    
    # Token breakdown
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    total_reasoning_tokens: int = 0
    
    # Cost details
    total_input_cost: float = 0.0
    total_output_cost: float = 0.0
    savings_from_cache: float = 0.0
    
    # Statistics
    avg_cost_per_execution: float = 0.0
    min_execution_cost: float = 0.0
    max_execution_cost: float = 0.0
    
    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_executions": self.total_executions,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "cost_by_model": self.cost_by_model,
            "cost_by_provider": self.cost_by_provider,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cached_tokens": self.total_cached_tokens,
            "total_reasoning_tokens": self.total_reasoning_tokens,
            "total_input_cost": self.total_input_cost,
            "total_output_cost": self.total_output_cost,
            "savings_from_cache": self.savings_from_cache,
            "avg_cost_per_execution": self.avg_cost_per_execution,
            "min_execution_cost": self.min_execution_cost,
            "max_execution_cost": self.max_execution_cost,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


class CostTracker:
    """Tracks and reports execution costs."""
    
    def __init__(self, pricing_registry: Optional[ModelPricingRegistry] = None):
        """Initialize cost tracker.
        
        Args:
            pricing_registry: Optional custom pricing registry
        """
        self.pricing = pricing_registry or ModelPricingRegistry()
        self.executions: List[ExecutionCost] = []
    
    def record_execution(
        self,
        execution_id: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> ExecutionCost:
        """Record an execution and calculate costs.
        
        Args:
            execution_id: Unique execution identifier
            model_id: Model used
            input_tokens: Input token count
            output_tokens: Output token count
            cached_tokens: Cached token count
            reasoning_tokens: Reasoning token count
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
            error: Error message if failed
            
        Returns:
            ExecutionCost record
        """
        # Get model pricing
        model_pricing = self.pricing.get_model_pricing(model_id)
        if not model_pricing:
            raise ValueError(f"Unknown model: {model_id}")
        
        # Calculate costs
        input_cost = model_pricing.calculate_input_cost(input_tokens, cached_tokens)
        output_cost = model_pricing.calculate_output_cost(output_tokens, reasoning_tokens)
        total_cost = input_cost + output_cost
        
        # Create execution cost record
        cost = ExecutionCost(
            execution_id=execution_id,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            reasoning_tokens=reasoning_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )
        
        self.executions.append(cost)
        return cost
    
    def get_report(self) -> CostReport:
        """Generate cost report.
        
        Returns:
            CostReport with summary statistics
        """
        if not self.executions:
            return CostReport()
        
        report = CostReport(
            total_executions=len(self.executions),
            start_time=self.executions[0].timestamp,
            end_time=self.executions[-1].timestamp,
        )
        
        costs_by_execution = []
        
        for execution in self.executions:
            # Accumulate totals
            report.total_tokens += (
                execution.input_tokens
                + execution.output_tokens
                + execution.reasoning_tokens
            )
            report.total_cost += execution.total_cost
            report.total_input_tokens += execution.input_tokens
            report.total_output_tokens += execution.output_tokens
            report.total_cached_tokens += execution.cached_tokens
            report.total_reasoning_tokens += execution.reasoning_tokens
            report.total_input_cost += execution.input_cost
            report.total_output_cost += execution.output_cost
            
            # Track by model and provider
            if execution.model_id not in report.cost_by_model:
                report.cost_by_model[execution.model_id] = 0.0
            report.cost_by_model[execution.model_id] += execution.total_cost
            
            # Track by provider
            model_pricing = self.pricing.get_model_pricing(execution.model_id)
            if model_pricing:
                provider_name = model_pricing.provider.value
                if provider_name not in report.cost_by_provider:
                    report.cost_by_provider[provider_name] = 0.0
                report.cost_by_provider[provider_name] += execution.total_cost
            
            costs_by_execution.append(execution.total_cost)
        
        # Calculate savings from cache
        for execution in self.executions:
            model_pricing = self.pricing.get_model_pricing(execution.model_id)
            if model_pricing and execution.cached_tokens > 0:
                # Calculate what we would have paid without cache
                regular_cost = (execution.cached_tokens * model_pricing.input_price_per_1m) / 1_000_000
                # Calculate what we actually paid with cache
                cached_cost = execution.cached_tokens * (
                    model_pricing.cached_input_price_per_1m or (model_pricing.input_price_per_1m * 0.5)
                ) / 1_000_000
                report.savings_from_cache += regular_cost - cached_cost
        
        # Calculate statistics
        if costs_by_execution:
            report.avg_cost_per_execution = report.total_cost / len(costs_by_execution)
            report.min_execution_cost = min(costs_by_execution)
            report.max_execution_cost = max(costs_by_execution)
        
        return report
    
    def clear(self) -> None:
        """Clear all recorded executions."""
        self.executions.clear()
    
    def get_executions(self) -> List[ExecutionCost]:
        """Get all recorded executions.
        
        Returns:
            List of ExecutionCost records
        """
        return self.executions
