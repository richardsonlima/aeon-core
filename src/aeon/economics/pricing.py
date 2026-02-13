"""Model pricing registry for different LLM providers."""

from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field


class ProviderType(str, Enum):
    """LLM provider types."""
    
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"  # Local models
    CUSTOM = "custom"


@dataclass
class ModelPricing:
    """Pricing information for a single model."""
    
    model_id: str
    provider: ProviderType
    
    # Pricing per 1M tokens (in USD)
    input_price_per_1m: float  # Input tokens
    output_price_per_1m: float  # Output tokens
    
    # Optional: special token types
    reasoning_price_per_1m: Optional[float] = None  # For reasoning tokens (GPT-5)
    cached_input_price_per_1m: Optional[float] = None  # For cached inputs
    
    # Metadata
    context_window: int = 128000  # Max context in tokens
    max_output: int = 128000  # Max output in tokens
    supports_vision: bool = False
    supports_reasoning: bool = False
    
    def calculate_input_cost(self, tokens: int, cached_tokens: int = 0) -> float:
        """Calculate input cost in USD.
        
        Args:
            tokens: Number of input tokens
            cached_tokens: Number of cached tokens (optional discount)
            
        Returns:
            Cost in USD
        """
        regular_tokens = tokens - cached_tokens
        cost = (regular_tokens * self.input_price_per_1m) / 1_000_000
        
        if cached_tokens > 0 and self.cached_input_price_per_1m:
            cost += (cached_tokens * self.cached_input_price_per_1m) / 1_000_000
        
        return cost
    
    def calculate_output_cost(self, tokens: int, reasoning_tokens: int = 0) -> float:
        """Calculate output cost in USD.
        
        Args:
            tokens: Number of output tokens
            reasoning_tokens: Number of reasoning tokens (optional)
            
        Returns:
            Cost in USD
        """
        regular_tokens = tokens - reasoning_tokens
        cost = (regular_tokens * self.output_price_per_1m) / 1_000_000
        
        if reasoning_tokens > 0 and self.reasoning_price_per_1m:
            cost += (reasoning_tokens * self.reasoning_price_per_1m) / 1_000_000
        elif reasoning_tokens > 0:
            # If no special pricing, use output pricing
            cost += (reasoning_tokens * self.output_price_per_1m) / 1_000_000
        
        return cost
    
    def calculate_total_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
    ) -> float:
        """Calculate total cost in USD.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached tokens
            reasoning_tokens: Number of reasoning tokens
            
        Returns:
            Total cost in USD
        """
        input_cost = self.calculate_input_cost(input_tokens, cached_tokens)
        output_cost = self.calculate_output_cost(output_tokens, reasoning_tokens)
        return input_cost + output_cost


class ModelPricingRegistry:
    """Registry of model pricing across providers."""
    
    # Default pricing data (August 2025 rates)
    DEFAULT_PRICING: Dict[ProviderType, Dict[str, ModelPricing]] = {
        ProviderType.OPENAI: {
            "gpt-5": ModelPricing(
                model_id="gpt-5",
                provider=ProviderType.OPENAI,
                input_price_per_1m=1.25,
                output_price_per_1m=10.00,
                reasoning_price_per_1m=10.00,
                cached_input_price_per_1m=0.625,
                supports_reasoning=True,
            ),
            "gpt-5-mini": ModelPricing(
                model_id="gpt-5-mini",
                provider=ProviderType.OPENAI,
                input_price_per_1m=0.25,
                output_price_per_1m=2.00,
                reasoning_price_per_1m=2.00,
                cached_input_price_per_1m=0.125,
                supports_reasoning=True,
            ),
            "gpt-5-nano": ModelPricing(
                model_id="gpt-5-nano",
                provider=ProviderType.OPENAI,
                input_price_per_1m=0.05,
                output_price_per_1m=0.40,
                reasoning_price_per_1m=0.40,
                cached_input_price_per_1m=0.025,
                supports_reasoning=True,
            ),
            "gpt-4o": ModelPricing(
                model_id="gpt-4o",
                provider=ProviderType.OPENAI,
                input_price_per_1m=5.00,
                output_price_per_1m=15.00,
                cached_input_price_per_1m=2.50,
            ),
        },
        ProviderType.ANTHROPIC: {
            "claude-3-opus": ModelPricing(
                model_id="claude-3-opus",
                provider=ProviderType.ANTHROPIC,
                input_price_per_1m=15.00,
                output_price_per_1m=75.00,
                cached_input_price_per_1m=7.50,
                context_window=200000,
            ),
            "claude-3-sonnet": ModelPricing(
                model_id="claude-3-sonnet",
                provider=ProviderType.ANTHROPIC,
                input_price_per_1m=3.00,
                output_price_per_1m=15.00,
                cached_input_price_per_1m=1.50,
                context_window=200000,
            ),
            "claude-3-haiku": ModelPricing(
                model_id="claude-3-haiku",
                provider=ProviderType.ANTHROPIC,
                input_price_per_1m=0.80,
                output_price_per_1m=4.00,
                cached_input_price_per_1m=0.40,
            ),
        },
        ProviderType.OLLAMA: {
            "gpt-oss-20b": ModelPricing(
                model_id="gpt-oss-20b",
                provider=ProviderType.OLLAMA,
                input_price_per_1m=0.00,
                output_price_per_1m=0.00,
            ),
            "gpt-oss-120b": ModelPricing(
                model_id="gpt-oss-120b",
                provider=ProviderType.OLLAMA,
                input_price_per_1m=0.00,
                output_price_per_1m=0.00,
            ),
            "llama2": ModelPricing(
                model_id="llama2",
                provider=ProviderType.OLLAMA,
                input_price_per_1m=0.00,
                output_price_per_1m=0.00,
            ),
        },
    }
    
    def __init__(self):
        """Initialize pricing registry with defaults."""
        self.pricing: Dict[str, ModelPricing] = {}
        
        # Load defaults
        for provider_models in self.DEFAULT_PRICING.values():
            for model_id, pricing in provider_models.items():
                self.pricing[model_id] = pricing
    
    def register_model(self, pricing: ModelPricing) -> None:
        """Register or update model pricing.
        
        Args:
            pricing: Model pricing information
        """
        self.pricing[pricing.model_id] = pricing
    
    def get_model_pricing(self, model_id: str) -> Optional[ModelPricing]:
        """Get pricing for a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            ModelPricing or None if not found
        """
        return self.pricing.get(model_id)
    
    def get_models_by_provider(self, provider: ProviderType) -> Dict[str, ModelPricing]:
        """Get all models for a provider.
        
        Args:
            provider: Provider type
            
        Returns:
            Dictionary of models and their pricing
        """
        return {
            model_id: pricing
            for model_id, pricing in self.pricing.items()
            if pricing.provider == provider
        }
    
    def list_models(self, provider: Optional[ProviderType] = None) -> list[str]:
        """List available models.
        
        Args:
            provider: Optional filter by provider
            
        Returns:
            List of model IDs
        """
        if provider:
            return [
                model_id
                for model_id, pricing in self.pricing.items()
                if pricing.provider == provider
            ]
        return list(self.pricing.keys())
    
    def estimate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
    ) -> Optional[Tuple[float, Dict]]:
        """Estimate cost for a model usage.
        
        Args:
            model_id: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached tokens
            reasoning_tokens: Number of reasoning tokens
            
        Returns:
            Tuple of (total_cost, breakdown_dict) or None if model not found
        """
        pricing = self.get_model_pricing(model_id)
        if not pricing:
            return None
        
        input_cost = pricing.calculate_input_cost(input_tokens, cached_tokens)
        output_cost = pricing.calculate_output_cost(output_tokens, reasoning_tokens)
        total_cost = input_cost + output_cost
        
        breakdown = {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "reasoning_tokens": reasoning_tokens,
        }
        
        return total_cost, breakdown
