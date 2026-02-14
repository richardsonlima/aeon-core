"""
Simple Chat Agent with OpenRouter

OpenRouter provides access to many models through one API.

Setup:
    1. Get API key from https://openrouter.ai
    2. export OPENROUTER_API_KEY="sk-or-..."
    3. python simple_chat_openrouter.py

Available models:
    - anthropic/claude-opus-4-6
    - openai/gpt-4o
    - google/gemini-2.0-flash
    - mistralai/mistral-large
    - meta-llama/llama-3-70b
"""

import asyncio
import os
from aeon import Agent


async def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")

    # You can switch between models easily
    model = "anthropic/claude-opus-4-6"  # Change to any supported model
    
    # Initialize agent with OpenRouter
    agent = Agent(
        name="OpenRouterChatBot",
        model_provider="openrouter",
        model_name=model,
        api_key=api_key
    )

    print("=" * 60)
    print(f"Æon Framework - Simple Chat with OpenRouter")
    print(f"Model: {model}")
    print("=" * 60)
    print("\nType 'quit' to exit")
    print("Type 'model <name>' to switch models\n")

    # Interactive chat loop
    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye!")
                break

            if user_input.lower().startswith("model "):
                model = user_input[6:].strip()
                agent.model_name = model
                print(f"\nSwitched to: {model}\n")
                continue

            if not user_input:
                continue

            # Get response from agent
            print("Thinking...", end="", flush=True)
            response = await agent.cortex.reason(prompt=user_input)
            print("\r           \r", end="")

            print(f"\nBot: {response}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
