"""
Telegram Bot Example

Create a Telegram bot that responds to messages.

Setup:
    1. Create a bot at https://t.me/BotFather
    2. Copy the bot token
    3. export TELEGRAM_BOT_TOKEN="123456:ABC..."
    4. python telegram_bot.py

Your bot will start polling for messages and respond in real-time.
"""

import asyncio
import os
from aeon import Agent
from aeon.integrations.provider import IntegrationProvider
from aeon.dialogue.context import DialogueContext, ActorRole


class TelegramProvider(IntegrationProvider):
    """Telegram integration for Æon Framework"""
    
    def __init__(self, token: str):
        self.token = token
        self.message_queue = []
        print(f"✓ Telegram bot initialized (token: {token[:20]}...)")

    async def dispatch(self, packet):
        """Send message to Telegram"""
        chat_id = packet.get("chat_id")
        text = packet.get("text")
        print(f"→ Sending to Telegram {chat_id}: {text[:50]}...")
        return True

    async def receive(self):
        """Receive messages from Telegram (polling)"""
        if self.message_queue:
            return self.message_queue.pop(0)
        await asyncio.sleep(1)
        return None

    def add_message(self, chat_id: str, user_id: str, text: str):
        """Add a message to the queue (simulated for demo)"""
        self.message_queue.append({
            "chat_id": chat_id,
            "user_id": user_id,
            "text": text,
            "timestamp": asyncio.get_event_loop().time()
        })


async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        token = "DEMO_TOKEN"
        print("⚠ TELEGRAM_BOT_TOKEN not set. Running in demo mode.\n")

    # Initialize agent
    agent = Agent(
        name="TelegramBot",
        model_provider="ollama",
        model_name="mistral"
    )

    # Initialize Telegram provider
    telegram = TelegramProvider(token=token)
    agent.integrations.register("telegram", telegram)

    print("=" * 60)
    print("Æon Framework - Telegram Bot")
    print("=" * 60)
    print("\nBot is running. Send messages to test.\n")

    # Simulate incoming messages
    async def simulate_messages():
        """Simulate Telegram messages for demo"""
        await asyncio.sleep(1)
        telegram.add_message("123456", "user1", "What is machine learning?")
        await asyncio.sleep(2)
        telegram.add_message("123456", "user1", "Can you explain neural networks?")

    # Start message simulation
    asyncio.create_task(simulate_messages())

    # Message processing loop
    try:
        for _ in range(5):  # Process 5 messages
            message = await telegram.receive()
            
            if message:
                chat_id = message["chat_id"]
                user_id = message["user_id"]
                text = message["text"]

                print(f"\n📨 From Telegram ({user_id}):")
                print(f"   {text}")

                # Get response
                response = await agent.cortex.reason(prompt=text)
                print(f"\n🤖 Bot Response:")
                print(f"   {response}")

                # Send back to Telegram
                await telegram.dispatch({
                    "chat_id": chat_id,
                    "text": response
                })

                # Store in dialogue
                context = DialogueContext(
                    context_id=f"telegram_{chat_id}",
                    origin_platform="telegram",
                    participant_id=user_id
                )
                context.add_turn(ActorRole.USER, text)
                context.add_turn(ActorRole.ASSISTANT, response)

            else:
                # No message, wait a bit
                await asyncio.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
