"""
Simple Chat Agent with OpenAI

Use OpenAI's GPT-4o for production-grade chat.

Setup:
    1. export OPENAI_API_KEY="sk-..."
    2. pip install aeon-core
    3. python simple_chat_openai.py

Cost: ~$0.005 per 1K input tokens, $0.015 per 1K output tokens
"""

import asyncio
import os
from aeon import Agent


async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Initialize agent with OpenAI
    agent = Agent(
        name="OpenAIChatBot",
        model_provider="openai",
        model_name="gpt-4o",
        api_key=api_key
    )

    print("=" * 60)
    print("Æon Framework - Simple Chat with OpenAI")
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
            response = await agent.cortex.reason(prompt=user_input)
            print("\r           \r", end="")  # Clear "Thinking..."

            print(f"\nBot: {response}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
