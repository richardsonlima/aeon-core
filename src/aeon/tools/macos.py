import asyncio
import subprocess
from typing import Any, Dict, List, Optional
from aeon.tools.base import BaseTool

class MacOSTool(BaseTool):
    """
    Native macOS system integration tool.
    Allows the agent to interact with Apple Notes, Reminders, Safari, and System Notifications.
    """
    
    def __init__(self):
        super().__init__(
            name="macos_system",
            description="Control NATIVE macOS system apps (Notes, Reminders, Safari, and Notifications). MUST be used for all local OS automation tasks like creating reminders or notes."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "add_note", 
                        "add_reminder", 
                        "safari_open", 
                        "safari_get_text", 
                        "system_notify"
                    ],
                    "description": "The macOS action to perform"
                },
                "title": {
                    "type": "string",
                    "description": "Title for note, reminder, or notification"
                },
                "content": {
                    "type": "string",
                    "description": "Body content for note or notification message"
                },
                "list_name": {
                    "type": "string",
                    "description": "Target list name for reminders (defaults to 'Reminders')"
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date for reminder (optional, naturally phrased like 'tomorrow at 10am')"
                },
                "url": {
                    "type": "string",
                    "description": "URL to open in Safari"
                }
            },
            "required": ["action"]
        }

    def _run_applescript(self, script: str) -> str:
        """Execute an AppleScript and return the output"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"AppleScript Error: {e.stderr.strip()}")

    async def execute(self, **kwargs) -> Any:
        action = kwargs.get("action", "").lower()
        
        # Action Normalizer (Hyper-Robustness for small models)
        if "reminder" in action: action = "add_reminder"
        elif "note" in action: action = "add_note"
        elif "safari" in action or "open" in action: 
            if "url" in kwargs: action = "safari_open"
        elif "notify" in action or "notification" in action: action = "system_notify"

        try:
            if action == "add_note":
                title = kwargs.get("title", "New Note")
                content = kwargs.get("content", "")
                script = f'''
                tell application "Notes"
                    tell account "Default"
                        make new note with properties {{name:"{title}", body:"{content}"}}
                    end tell
                end tell
                '''
                self._run_applescript(script)
                return f"Successfully created Apple Note: {title}"

            elif action == "add_reminder":
                title = kwargs.get("title")
                list_name = kwargs.get("list_name")
                due_date = kwargs.get("due_date")
                
                if not title:
                    return "Error: Reminder title is required"
                
                # Combine properties into a single record
                props = [f'name:"{title}"']
                if due_date:
                    props.append(f'due date:date "{due_date}"')
                
                props_string = ", ".join(props)
                
                # Resilient Script: Try specific list, fallback to default if not found
                script = f'''
                tell application "Reminders"
                    set targetList to default list
                    {f'try\nset targetList to list "{list_name}"\nend try' if list_name else ""}
                    tell targetList
                        make new reminder with properties {{{props_string}}}
                    end tell
                end tell
                '''
                self._run_applescript(script)
                actual_list = list_name if list_name else "Default"
                return f"Successfully added reminder '{title}' (List: {actual_list})"

            elif action == "safari_open":
                url = kwargs.get("url")
                if not url:
                    return "Error: URL is required"
                
                script = f'''
                tell application "Safari"
                    open location "{url}"
                    activate
                end tell
                '''
                self._run_applescript(script)
                return f"Opened {url} in Safari"

            elif action == "safari_get_text":
                script = '''
                tell application "Safari"
                    if (count of windows) > 0 then
                        get text of front document
                    else
                        return "No Safari windows open"
                    end if
                end tell
                '''
                content = self._run_applescript(script)
                return content[:5000] + ("..." if len(content) > 5000 else "")

            elif action == "system_notify":
                title = kwargs.get("title", "Aeon Assistant")
                message = kwargs.get("content", "Task complete")
                script = f'display notification "{message}" with title "{title}"'
                self._run_applescript(script)
                return f"Sent system notification: {title}"

            return f"Unknown action: {action}"

        except Exception as e:
            return f"macOS Tool Error: {str(e)}"
