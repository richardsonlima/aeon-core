import os
import json
import time
from typing import Dict, Any, List, Optional

class SwarmCheckpoint:
    """
    Executive Layer (L2) Component for Persistent Orchestration.
    Solves LangGraph's complexity by capturing periodic 'Reality Snapshots'.
    """
    
    def __init__(self, vault_path: str = "src/aeon/core/vault"):
        self.checkpoint_dir = os.path.join(vault_path, "checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def save_snapshot(self, swarm_id: str, state: Dict[str, Any]):
        """Saves the current state of a multi-agent swarm."""
        filename = f"checkpoint_{swarm_id}_{int(time.time())}.json"
        path = os.path.join(self.checkpoint_dir, filename)
        
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
            
        print(f" [✓] Vault: Swarm Checkpoint saved for '{swarm_id}'")
        return path

    def load_latest(self, swarm_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent state for a given swarm."""
        files = [f for f in os.listdir(self.checkpoint_dir) if f.startswith(f"checkpoint_{swarm_id}")]
        if not files:
            return None
            
        latest_file = sorted(files)[-1]
        path = os.path.join(self.checkpoint_dir, latest_file)
        
        with open(path, "r") as f:
            return json.load(f)
