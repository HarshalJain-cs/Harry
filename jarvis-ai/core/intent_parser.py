"""
JARVIS Intent Parser - Natural language command understanding.

Uses local LLM to extract intents, entities, and confidence from commands.
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ai.llm import LLMClient


class IntentType(Enum):
    """Common intent types."""
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    WEB_SEARCH = "web_search"
    OPEN_URL = "open_url"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    CLIPBOARD = "clipboard"
    FILE_OP = "file_operation"
    SYSTEM = "system"
    QUESTION = "question"
    COMMAND = "command"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Parsed intent from natural language command."""
    intent: str
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_command: str = ""
    reasoning: str = ""


class IntentParser:
    """
    Parse natural language commands into structured intents.
    
    Uses a local LLM (Phi-3, Mistral, etc.) for intent extraction.
    """
    
    SYSTEM_PROMPT = """You are an intent parser for a desktop AI assistant called JARVIS.
Your job is to extract the intent and entities from user commands.

Output ONLY valid JSON with these fields:
- intent: The action type (open_app, close_app, web_search, open_url, type_text, press_key, clipboard, file_operation, system, question, command)
- entities: Key parameters as a dictionary
- confidence: Your confidence from 0.0 to 1.0
- reasoning: Brief explanation of your interpretation

Examples:
User: "Open Chrome"
{"intent": "open_app", "entities": {"app": "chrome"}, "confidence": 0.95, "reasoning": "Clear request to open Chrome browser"}

User: "Search for Python tutorials on YouTube"  
{"intent": "web_search", "entities": {"query": "Python tutorials", "site": "youtube"}, "confidence": 0.90, "reasoning": "Web search request with site preference"}

User: "Type hello world"
{"intent": "type_text", "entities": {"text": "hello world"}, "confidence": 0.92, "reasoning": "Request to type specific text"}

User: "What's the weather like?"
{"intent": "question", "entities": {"topic": "weather"}, "confidence": 0.85, "reasoning": "Question requiring information lookup"}

User: "Close this window"
{"intent": "close_app", "entities": {"target": "active_window"}, "confidence": 0.88, "reasoning": "Request to close current window"}

Respond ONLY with the JSON object, no other text."""

    # Common app name mappings
    APP_ALIASES = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "browser": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "microsoft edge": "msedge",
        "notepad": "notepad",
        "code": "code",
        "vscode": "code",
        "visual studio code": "code",
        "terminal": "cmd",
        "command prompt": "cmd",
        "powershell": "powershell",
        "explorer": "explorer",
        "file explorer": "explorer",
        "spotify": "spotify",
        "discord": "discord",
        "slack": "slack",
        "teams": "teams",
        "outlook": "outlook",
        "word": "winword",
        "excel": "excel",
        "powerpoint": "powerpnt",
        "calculator": "calc",
        "settings": "ms-settings:",
    }
    
    def __init__(self, model: str = "phi3:mini"):
        """
        Initialize intent parser.
        
        Args:
            model: LLM model to use for parsing
        """
        self.llm = LLMClient(model=model)
    
    def parse(self, command: str) -> ParsedIntent:
        """
        Parse a natural language command.
        
        Args:
            command: User's voice or text command
            
        Returns:
            ParsedIntent with extracted intent, entities, and confidence
        """
        if not command.strip():
            return ParsedIntent(
                intent="unknown",
                confidence=0.0,
                raw_command=command,
                reasoning="Empty command",
            )
        
        # Try quick pattern matching first for common commands
        quick_result = self._quick_parse(command)
        if quick_result and quick_result.confidence >= 0.9:
            return quick_result
        
        # Use LLM for complex parsing
        try:
            response = self.llm.generate_json(
                prompt=f"Parse this command: {command}",
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.3,  # Low temp for more deterministic parsing
            )
            
            if "error" in response:
                return ParsedIntent(
                    intent="unknown",
                    confidence=0.0,
                    raw_command=command,
                    reasoning=f"Parse error: {response.get('error')}",
                )
            
            # Normalize app names if present
            entities = response.get("entities", {})
            if "app" in entities:
                entities["app"] = self._normalize_app_name(entities["app"])
            
            return ParsedIntent(
                intent=response.get("intent", "unknown"),
                entities=entities,
                confidence=float(response.get("confidence", 0.5)),
                raw_command=command,
                reasoning=response.get("reasoning", ""),
            )
        
        except Exception as e:
            return ParsedIntent(
                intent="unknown",
                confidence=0.0,
                raw_command=command,
                reasoning=f"Error: {str(e)}",
            )
    
    def _quick_parse(self, command: str) -> Optional[ParsedIntent]:
        """Quick pattern-based parsing for common commands."""
        cmd_lower = command.lower().strip()
        
        # Open app patterns
        if cmd_lower.startswith("open "):
            app = cmd_lower[5:].strip()
            normalized = self._normalize_app_name(app)
            return ParsedIntent(
                intent="open_app",
                entities={"app": normalized},
                confidence=0.95,
                raw_command=command,
                reasoning="Pattern match: 'open <app>'",
            )
        
        # Close app patterns
        if cmd_lower.startswith("close "):
            target = cmd_lower[6:].strip()
            return ParsedIntent(
                intent="close_app",
                entities={"target": target},
                confidence=0.90,
                raw_command=command,
                reasoning="Pattern match: 'close <target>'",
            )
        
        # Web search patterns
        search_prefixes = ["search for ", "google ", "look up ", "find "]
        for prefix in search_prefixes:
            if cmd_lower.startswith(prefix):
                query = cmd_lower[len(prefix):].strip()
                return ParsedIntent(
                    intent="web_search",
                    entities={"query": query},
                    confidence=0.92,
                    raw_command=command,
                    reasoning=f"Pattern match: '{prefix}<query>'",
                )
        
        # Type text patterns
        if cmd_lower.startswith("type "):
            text = command[5:].strip()  # Keep original case
            return ParsedIntent(
                intent="type_text",
                entities={"text": text},
                confidence=0.93,
                raw_command=command,
                reasoning="Pattern match: 'type <text>'",
            )
        
        return None
    
    def _normalize_app_name(self, app_name: str) -> str:
        """Normalize app name to executable name."""
        app_lower = app_name.lower().strip()
        return self.APP_ALIASES.get(app_lower, app_name)
    
    def get_tool_for_intent(self, intent: str) -> Optional[str]:
        """Map intent type to tool name."""
        mapping = {
            "open_app": "open_app",
            "close_app": "close_app",
            "web_search": "web_search",
            "open_url": "open_url",
            "type_text": "type_text",
            "press_key": "press_key",
            "clipboard": "clipboard",
            "file_operation": "file_op",
            "system": "system_command",
            "question": "answer_question",
            "command": "execute_command",
        }
        return mapping.get(intent)


if __name__ == "__main__":
    # Test intent parser
    print("Testing Intent Parser...")
    
    parser = IntentParser()
    
    test_commands = [
        "Open Chrome",
        "Search for Python tutorials",
        "Close this window",
        "Type hello world",
        "What time is it?",
        "Open Visual Studio Code",
    ]
    
    for cmd in test_commands:
        print(f"\nCommand: '{cmd}'")
        result = parser.parse(cmd)
        print(f"  Intent: {result.intent}")
        print(f"  Entities: {result.entities}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")
