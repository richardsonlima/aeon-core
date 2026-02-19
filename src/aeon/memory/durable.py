
import os
from typing import Dict, List

class DurableStore:
    """
    Durable Memory system inspired by OpenClaw.
    Stores and retrieves facts from Markdown files.
    """
    def __init__(self, storage_dir: str = ".aeon"):
        self.storage_dir = storage_dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        self.user_file = os.path.join(storage_dir, "user.md")
        self.facts_file = os.path.join(storage_dir, "facts.md")
        
        # Ensure files exist
        for f in [self.user_file, self.facts_file]:
            if not os.path.exists(f):
                with open(f, 'w') as fh:
                    fh.write(f"# {os.path.basename(f)}\n\n")

    def get_context(self) -> str:
        """Returns all durable facts as a prompt-ready string"""
        context = "\n## Durable Memory (User Facts & Preferences)\n"
        try:
            for f in [self.user_file, self.facts_file]:
                if os.path.exists(f):
                    with open(f, 'r') as fh:
                        content = fh.read().strip()
                        if len(content) > 50: # Ignore empty/header-only files
                            context += f"\n### From {os.path.basename(f)}:\n{content}\n"
        except Exception as e:
            print(f" [!] Error reading durable memory: {e}")
            
        return context

    def append_fact(self, fact: str):
        """Append a new fact to facts.md"""
        with open(self.facts_file, 'a') as f:
            f.write(f"- {fact}\n")
