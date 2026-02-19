"""
Multi-Platform Bot

Run the same agent on multiple platforms simultaneously.
Supported platforms: Telegram, Discord, Slack, Email, HTTP

This example shows how one agent can:
- Handle messages from 3+ platforms
- Maintain separate conversation contexts per platform
- Apply different rules per channel
"""

import asyncio
from aeon import Agent, IntegrationProvider
from aeon.dialogue import DialogueContext, Turn


class UniversalIntegration(IntegrationProvider):
    """Generic multi-platform integration"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.message_queue = []
        print(f"✓ {platform.title()} integration initialized")

    async def dispatch(self, packet):
        """Send message to platform"""
        recipient = packet.get("recipient", "unknown")
        text = packet.get("text", "")
        print(f"  → [{self.platform}] {recipient}: {text[:40]}...")
        return True

    async def receive(self):
        """Receive messages from platform"""
        if self.message_queue:
            return self.message_queue.pop(0)
        await asyncio.sleep(0.5)
        return None

    def add_message(self, user_id: str, text: str):
        """Add incoming message"""
        self.message_queue.append({
            "user_id": user_id,
            "text": text
        })


async def main():
    print("=" * 60)
    print("Æon Framework - Multi-Platform Bot")
    print("=" * 60)

    # Initialize agent
    agent = Agent(
        name="UniversalBot",
        model="ollama/phi3.5",
        protocols=[]
    )

    # Register integrations for 3 platforms
    print("\\nRegistering Platforms:")
    platforms = {}
    for platform in ["telegram", "discord", "slack"]:
        provider = UniversalIntegration(platform)
        agent.integrations.register(platform, provider)
        platforms[platform] = provider

    # Dialogue contexts per platform
    contexts = {
        platform: DialogueContext(
            context_id=f"{platform}_session",
            origin_platform=platform,
            participant_id="demo_user"
        )
        for platform in platforms.keys()
    }

    print("\\n" + "=" * 60)
    print("Demo: Messages from Multiple Platforms")
    print("=" * 60)

    # Simulate incoming messages from different platforms
    messages = [
        ("telegram", "user1", "Hello! How are you?"),
        ("discord", "user2", "What can you do?"),
        ("slack", "user3", "Tell me a joke"),
        ("telegram", "user1", "What's the weather?"),
        ("discord", "user2", "Can you code in Python?"),
    ]

    # Add messages to queues
    for platform, user_id, text in messages:
        platforms[platform].add_message(user_id, text)

    # Process messages
    print()
    for i in range(len(messages)):
        # Poll each platform
        for platform_name, provider in platforms.items():
            message = await provider.receive()
            
            if message:
                user_id = message["user_id"]
                text = message["text"]
                platform_display = platform_name.title()

                print(f"\\n[{platform_display}] {user_id}:")
                print(f"  Message: {text}")

                # Get response
                response = agent.cortex.plan_action(
                    system_prompt=agent.system_prompt,
                    user_input=text,
                    tools=[]
                )

                # Add platform-specific prefix (e.g., emoji)
                emojis = {
                    "telegram": "📱",
                    "discord": "🎮",
                    "slack": "💼"
                }
                emoji = emojis.get(platform_name, "")

                response_str = str(response)
                print(f"  {emoji} Bot: {response_str[:80]}...")

                # Send to platform
                await provider.dispatch({
                    "recipient": user_id,
                    "text": response_str
                })

                # Store in platform-specific context
                contexts[platform_name].add_turn(Turn(actor="user", content=text))
                contexts[platform_name].add_turn(Turn(actor="assistant", content=response_str))

    # Summary
    print("\\n" + "=" * 60)
    print("Platform Statistics")
    print("=" * 60)

    for platform_name, context in contexts.items():
        turns = len(context.dialogue)
        emoji = {"telegram": "📱", "discord": "🎮", "slack": "💼"}.get(platform_name, "")
        print(f"{emoji} {platform_name.title()}: {turns} messages")

    print("\\n✓ Multi-platform bot demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
