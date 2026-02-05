"""
Cortex Layer: Reasoning Engine.
Connects to System 1 (LLMs) via OpenRouter using the OpenAI Client Standard.
"""
import os
from typing import List, Dict, Any, Optional, Union
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageToolCall
from pydantic import BaseModel

class CortexConfig(BaseModel):
    # Defaulting to Gemini 2.0 Flash (Excellent reasoning/cost ratio)
    model: str = "google/gemini-2.0-flash-001" 
    temperature: float = 0.0

class Cortex:
    """
    The reasoning engine interfacing with System 1 (LLMs).
    Responsible for interpreting user intent and selecting tools.
    """
    def __init__(self, config: CortexConfig):
        self.config = config
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is missing.")
            
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    def plan_action(
        self, 
        system_prompt: str, 
        user_input: str, 
        tools: List[Dict]
    ) -> Union[ChatCompletionMessageToolCall, str]:
        """
        Sends context to the LLM and requests a tool call (Action).
        Returns either a ToolCall object or a plain string response.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        print(f" [>] Cortex: Sending request to {self.config.model}...")

        # Construct parameters dynamically to avoid sending empty 'tools' list
        # causing 400 errors on some providers.
        api_params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature
        }

        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**api_params)
            
            message = response.choices[0].message
            
            # Check if the model wants to call a tool
            if message.tool_calls:
                # For v0.1.0, we handle the first tool call.
                # v0.2.0 will introduce parallel tool execution.
                return message.tool_calls[0]
            
            # If no tool called, return the thought/text
            return message.content or "No response content."

        except Exception as e:
            return f"Cortex Error: {str(e)}"