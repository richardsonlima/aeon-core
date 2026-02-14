"""
Simple Chat Agent with Ollama (Local)

This is the fastest way to get started. Run Ollama locally and chat with a model.

Setup:
    1. brew install ollama
    2. ollama serve (in another terminal)
    3. ollama pull mistral
    4. python simple_chat_ollama.py

That's it! No API keys needed, runs completely offline.
"""

import asyncio
from aeon import Agent


async def main():
    # Initialize agent with local Ollama
    agent = Agent(
        name="LocalChatBot",
        model_provider="ollama",
        model_name="mistral",
        base_url="http://localhost:11434"
    )

    print("=" * 60)
    print("Æon Framework - Simple Chat with Ollama")
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
            response = await agent.cortex.reason(prompt=user_input)
            print(f"\nBot: {response}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
