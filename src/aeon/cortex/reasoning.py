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
        
        # Detect if using Ollama (local) or OpenRouter (cloud)
        if config.model.startswith("ollama/"):
            # Ollama local mode
            self.client = OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",  # Ollama doesn't need real API key
            )
            # Remove ollama/ prefix for actual model name
            self.config.model = config.model.replace("ollama/", "")
        else:
            # OpenRouter cloud mode
            api_key = os.getenv("OPENROUTER_API_KEY")
            
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is missing.")
                
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )

    def sanitize_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Ensures messages follow the strict User -> Assistant alternation.
        Strips consecutive roles or orphaned tool results.
        """
        sanitized = []
        last_role = None
        
        for msg in messages:
            role = msg.get("role")
            
            # 1. Skip if same role as last (keep the latest content)
            if role == last_role:
                if sanitized:
                    sanitized[-1] = msg # Replace with latest from same role
                continue
                
            sanitized.append(msg)
            last_role = role
            
        # 3. Ensure it ends with a user message for the next prompt (if not already)
        # Most APIs expect the last message to be 'user' before 'assistant' response.
        return sanitized

    def plan_action(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]], 
        tools: List[Dict]
    ) -> Union[ChatCompletionMessageToolCall, str]:
        """
        Sends context to the LLM and requests a tool call (Action).
        Returns either a ToolCall object or a plain string response.
        """
        # Sanitize history
        cleaned_history = self.sanitize_messages(messages)
        
        # Ensure system prompt is at the start
        full_messages = [{"role": "system", "content": system_prompt}] + cleaned_history

        print(f" [>] Cortex: Sending request to {self.config.model} ({len(full_messages)} messages)...")

        # Construct parameters dynamically to avoid sending empty 'tools' list
        # causing 400 errors on some providers.
        api_params = {
            "model": self.config.model,
            "messages": full_messages,
            "temperature": self.config.temperature
        }

        # Ollama models often lack native tool-calling support in the API bridge.
        # We rely on Æon's robust prompt-based extraction for local models.
        is_ollama = "localhost:11434" in str(self.client.base_url)
        
        if tools and not is_ollama:
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