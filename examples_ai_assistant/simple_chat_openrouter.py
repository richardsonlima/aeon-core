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
    - google/gemini-2.0-flash-001
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
    model = "google/gemini-2.0-flash-001"  # Change to any supported model
    
    # Initialize agent with OpenRouter
    agent = Agent(
        name="OpenRouterChatBot",
        model=model,  # OpenRouter format: provider/model-name
        protocols=[]
    )

    print("=" * 60)
    print(f"Æon Framework - Simple Chat with OpenRouter")
    print(f"Model: {model}")
    print("=" * 60)
    print("\nType 'quit' to exit\n")

    # Interactive chat loop
    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            # Get response from agent
            print("Thinking...", end="", flush=True)
            response = agent.cortex.plan_action(
                system_prompt=agent.system_prompt,
                user_input=user_input,
                tools=[]
            )
            print("\r           \r", end="")

            print(f"\nBot: {response}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
