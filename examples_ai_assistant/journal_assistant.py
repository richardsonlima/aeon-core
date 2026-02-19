"""
Personal Journal Assistant

Create an AI-powered journal that:
- Accepts daily entries
- Summarizes emotions and themes
- Provides insights and reflections
- Maintains private journal file

Setup:
    python journal_assistant.py

The journal is stored in journal_entries.txt (local, encrypted recommended for production)
"""

import asyncio
import os
import datetime
from aeon import Agent, Capability, CapabilityMetadata
from aeon.dialogue import DialogueContext, Turn


class JournalCapability(Capability):
    """Journal management capability"""
    
    def __init__(self, journal_file: str = "journal_entries.txt"):
        self.journal_file = journal_file
        self.metadata = CapabilityMetadata(
            name="journal",
            description="Save and retrieve journal entries",
            dependencies=[]
        )

    async def activate(self):
        """Activate the capability"""
        pass

    async def deactivate(self):
        """Deactivate the capability"""
        pass

    async def invoke(self, **kwargs):
        """Invoke capability method"""
        method = kwargs.get("method")
        if method == "save":
            return await self.save_entry(kwargs.get("text", ""))
        elif method == "get_recent":
            return await self.get_recent_entries(kwargs.get("days", 7))
        elif method == "count":
            return await self.count_entries()
        return "Unknown method"

    async def save_entry(self, text: str) -> str:
        """Save a journal entry"""
        date = datetime.date.today().isoformat()
        time = datetime.datetime.now().strftime("%H:%M")
        
        entry = f"\\n[{date} {time}]\\n{text}\\n"
        
        with open(self.journal_file, "a") as f:
            f.write(entry)
        
        return f"✅ Entry saved for {date} at {time}"

    async def get_recent_entries(self, days: int = 7) -> str:
        """Get recent journal entries"""
        if not os.path.exists(self.journal_file):
            return "No entries yet. Start by creating one!"
        
        with open(self.journal_file, "r") as f:
            content = f.read()
        
        # Return last 2000 characters (approximately last 7 days)
        return content[-2000:] if content else "No entries found."

    async def count_entries(self) -> int:
        """Count total entries"""
        if not os.path.exists(self.journal_file):
            return 0
        
        with open(self.journal_file, "r") as f:
            content = f.read()
        
        return content.count("\\n[")


async def main():
    # Initialize agent
    agent = Agent(
        name="JournalAssistant",
        model="ollama/phi3.5",
        protocols=[]
    )

    # Create and register journal capability
    journal = JournalCapability()
    agent.extensions.register(journal)

    print("=" * 60)
    print("Æon Framework - Personal Journal Assistant")
    print("=" * 60)
    print("\\nCommands:")
    print("  write   - Write a new entry")
    print("  read    - Read recent entries")
    print("  reflect - AI reflection on entries")
    print("  quit    - Exit\\n")

    # Create dialogue context
    context = DialogueContext(
        context_id="journal_session",
        origin_platform="cli",
        participant_id="user"
    )

    try:
        while True:
            command = input("Command: ").strip().lower()

            if command == "quit":
                print("\\n✨ Your journal has been saved. Goodbye!")
                break

            elif command == "write":
                print("\\nToday's entry (press Enter twice to finish):")
                lines = []
                while True:
                    try:
                        line = input()
                        if line == "":
                            if lines and lines[-1] == "":
                                break
                            lines.append(line)
                        else:
                            lines.append(line)
                    except EOFError:
                        break
                
                entry_text = "\\n".join(lines[:-1] if lines[-1] == "" else lines)
                
                if entry_text.strip():
                    # Save entry
                    result = await journal.save_entry(entry_text)
                    print(f"\\n{result}\\n")
                    
                    # Get AI response
                    prompt = f"This person wrote in their journal: '{entry_text}'. Provide a brief, supportive reflection (2-3 sentences)."
                    response = agent.cortex.plan_action(
                        system_prompt=agent.system_prompt,
                        user_input=prompt,
                        tools=[]
                    )
                    print(f"🤖 Reflection: {response}\\n")
                    
                    # Store in dialogue
                    context.add_turn(Turn(actor="user", content=entry_text))
                    context.add_turn(Turn(actor="assistant", content=str(response)))

            elif command == "read":
                entries = await journal.get_recent_entries(days=7)
                print(f"\\n📖 Recent Entries:\\n{entries}\\n")

            elif command == "reflect":
                count = await journal.count_entries()
                entries = await journal.get_recent_entries(days=7)
                
                prompt = f"""The person has {count} total journal entries. Here are recent ones:
                
{entries}

Provide a brief analysis of:
1. Overall emotional tone
2. Main themes or concerns
3. Positive developments or growth
4. One piece of supportive advice"""

                print("\\nGenerating insights...\\n")
                reflection = agent.cortex.plan_action(
                    system_prompt=agent.system_prompt,
                    user_input=prompt,
                    tools=[]
                )
                print(f"📊 Journal Insights:\\n{reflection}\\n")
                
                context.add_turn(Turn(actor="user", content="Reflect on my recent journal entries"))
                context.add_turn(Turn(actor="assistant", content=str(reflection)))

            else:
                print("Unknown command. Try: write, read, reflect, quit\\n")

    except KeyboardInterrupt:
        print("\\n\\n✨ Journal saved. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
