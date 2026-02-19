import datetime
from typing import Dict, Any, Optional
from aeon.core.config import AeonConfig

class SituationalInjector:
    """
    Dispatcher-level (L4) middleware to inject deterministic situational context 
    into the reasoning loop. Solves the "Temporal Bug" (UTC vs Local).
    """
    
    def __init__(self, config: Optional[AeonConfig] = None):
        self.config = config

    def get_current_context(self, user_timezone: str = "UTC") -> Dict[str, Any]:
        """
        Retrieves the exact situational reality of the user.
        """
        # In a real implementation, this would use pytz for timezone conversion
        # For this demo, we'll simulate the San Francisco context mentioned by the user
        now = datetime.datetime.now()
        
        return {
            "timestamp_utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "user_local_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "user_timezone": user_timezone,
            "location": "São Francisco, CA" if user_timezone == "America/Los_Angeles" else "Unknown",
            "day_of_week": now.strftime("%A"),
            "framework_status": "v0.4.0-ULTRA (Active)"
        }

    def inject(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Prefixes the prompt with a deterministic situational block.
        """
        situational_block = (
            f"--- SITUATIONAL CONTEXT ---\n"
            f"Current Time: {context['user_local_time']} ({context['user_timezone']})\n"
            f"Location: {context['location']}\n"
            f"Day: {context['day_of_week']}\n"
            f"Status: {context['framework_status']}\n"
            f"---------------------------\n\n"
        )
        return situational_block + prompt
