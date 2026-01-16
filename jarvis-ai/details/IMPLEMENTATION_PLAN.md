# JARVIS Implementation Plan
## Complete Bug Fixes + Advanced Features + Wakey Integration

**Generated:** January 2026
**Status:** Ready for Implementation

---

## Part 1: Critical Bug Fixes (Priority: HIGH)

### 1.1 Fix Import Collision in tools/__init__.py

**Problem:** `from .system import register_system_tools` imports from `tools/system/` directory instead of `tools/system.py` file.

**Solution:** Rename `tools/system.py` to `tools/system_tools.py` and update imports.

```python
# File: tools/__init__.py (UPDATED)
"""JARVIS Tools - Executable actions and utilities."""
from .registry import Tool, ToolRegistry, tool
from .system_tools import register_system_tools  # Changed from .system
from .web import register_web_tools

__all__ = [
    "Tool",
    "ToolRegistry",
    "tool",
    "register_system_tools",
    "register_web_tools",
]
```

**Files to modify:**
- Rename: `tools/system.py` -> `tools/system_tools.py`
- Update: `tools/__init__.py`
- Update any other imports referencing `tools.system`

---

### 1.2 Fix Method Name Mismatches in server.py

**Problem:** Server calls wrong method names.

**Changes needed in `ui/server.py`:**

```python
# Line ~151: Change
result = await asyncio.to_thread(
    self.agent.process_text,  # WRONG
    request.command,
)
# To:
result = await asyncio.to_thread(
    self.agent.process_text_command,  # CORRECT
    request.command,
)

# Line ~203: Change
history = memory.get_command_history(limit)  # WRONG
# To:
history = memory.get_recent_commands(limit)  # CORRECT

# Line ~229: Same fix
result = await asyncio.to_thread(
    self.agent.process_text_command,  # CORRECT
    command,
)
```

---

### 1.3 Fix ChromaDB Deprecated API in memory.py

**Problem:** Uses old ChromaDB initialization syntax.

**Change in `core/memory.py`:**

```python
# Lines 134-146: Replace old init
def _init_chroma(self):
    """Initialize ChromaDB for semantic search."""
    try:
        # NEW API (ChromaDB 0.4+)
        self.chroma_client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=chromadb.Settings(
                anonymized_telemetry=False,
            )
        )

        self.memories_collection = self.chroma_client.get_or_create_collection(
            name="jarvis_memories",
            metadata={"description": "JARVIS semantic memories"}
        )
    except Exception as e:
        print(f"ChromaDB initialization failed: {e}")
        self.chroma_client = None
```

Also update `close()` method:
```python
def close(self):
    """Close database connections."""
    self.conn.close()
    # ChromaDB PersistentClient auto-persists, no manual persist needed
```

---

## Part 2: Dependency Installation

### 2.1 Core Dependencies Install Script

Create `scripts/install.py`:

```python
#!/usr/bin/env python3
"""JARVIS Dependency Installer"""
import subprocess
import sys

CORE_DEPS = [
    "numpy>=1.24.0",
    "psutil>=5.9.0",
    "pyautogui>=0.9.54",
    "pynput>=1.7.6",
    "pyperclip>=1.8.2",
    "mss>=9.0.0",
    "pillow>=10.0.0",
    "requests>=2.28.0",
    "pydantic>=2.0.0",
    "rich>=13.0.0",
    "python-dotenv>=1.0.0",
    "apscheduler>=3.10.0",
]

AI_DEPS = [
    "ollama>=0.1.0",
    "openai-whisper>=20230314",
    "sounddevice>=0.4.6",
    "soundfile>=0.12.1",
    "pyaudio>=0.2.12",
]

MEMORY_DEPS = [
    "chromadb>=0.4.0",
    "sentence-transformers>=2.0.0",
    "sqlalchemy>=2.0.0",
]

SERVER_DEPS = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
]

def install(packages, name):
    print(f"\n{'='*50}")
    print(f"Installing {name}...")
    print('='*50)
    for pkg in packages:
        print(f"  -> {pkg}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

if __name__ == "__main__":
    install(CORE_DEPS, "Core Dependencies")
    install(AI_DEPS, "AI Dependencies")
    install(MEMORY_DEPS, "Memory Dependencies")
    install(SERVER_DEPS, "Server Dependencies")
    print("\n[OK] All dependencies installed!")
```

---

## Part 3: Advanced Features to Add

### 3.1 Screen Context Awareness

**Purpose:** Let JARVIS understand what's on screen for smarter actions.

**New file:** `tools/vision/screen_context.py`

```python
"""Screen context awareness for smarter JARVIS responses."""
import mss
from PIL import Image
import io

class ScreenContext:
    """Capture and analyze screen content."""

    def __init__(self):
        self.sct = mss.mss()
        self.ocr = None  # Lazy load

    def capture_active_window(self) -> Image.Image:
        """Capture screenshot of active window."""
        # Get active window bounds
        monitor = self.sct.monitors[1]  # Primary monitor
        screenshot = self.sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    def get_screen_text(self, region=None) -> str:
        """Extract text from screen using OCR."""
        if self.ocr is None:
            try:
                from paddleocr import PaddleOCR
                self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            except ImportError:
                return ""

        img = self.capture_active_window()
        result = self.ocr.ocr(img)

        if result and result[0]:
            return " ".join([line[1][0] for line in result[0]])
        return ""

    def get_active_app_context(self) -> dict:
        """Get context about the active application."""
        import psutil
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        try:
            proc = psutil.Process(pid)
            return {
                "app_name": proc.name(),
                "window_title": win32gui.GetWindowText(hwnd),
                "pid": pid,
            }
        except:
            return {}
```

---

### 3.2 Natural Conversation Memory

**Purpose:** Remember conversation context for follow-up commands.

**New file:** `core/conversation.py`

```python
"""Conversation context for natural follow-ups."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

@dataclass
class ConversationTurn:
    """A single turn in conversation."""
    user_input: str
    intent: str
    entities: Dict[str, Any]
    response: str
    timestamp: datetime = field(default_factory=datetime.now)

class ConversationContext:
    """Track conversation for natural follow-ups."""

    def __init__(self, max_turns: int = 10, context_timeout: int = 300):
        self.turns: List[ConversationTurn] = []
        self.max_turns = max_turns
        self.context_timeout = context_timeout  # seconds
        self.current_topic: Optional[str] = None
        self.referenced_entities: Dict[str, Any] = {}

    def add_turn(self, turn: ConversationTurn):
        """Add a conversation turn."""
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

        # Update referenced entities
        self.referenced_entities.update(turn.entities)
        self.current_topic = turn.intent

    def resolve_reference(self, text: str) -> str:
        """Resolve pronouns and references like 'it', 'that', 'there'."""
        # If text contains reference words
        references = {
            "it": self._get_last_object(),
            "that": self._get_last_object(),
            "there": self.referenced_entities.get("location"),
            "him": self.referenced_entities.get("person"),
            "her": self.referenced_entities.get("person"),
        }

        for ref, value in references.items():
            if ref in text.lower() and value:
                text = text.lower().replace(ref, str(value))

        return text

    def _get_last_object(self) -> Optional[str]:
        """Get the last mentioned object/app/file."""
        for key in ["app", "file", "url", "query"]:
            if key in self.referenced_entities:
                return self.referenced_entities[key]
        return None

    def is_context_valid(self) -> bool:
        """Check if context is still valid (not timed out)."""
        if not self.turns:
            return False
        last_turn = self.turns[-1]
        age = datetime.now() - last_turn.timestamp
        return age < timedelta(seconds=self.context_timeout)

    def get_context_summary(self) -> str:
        """Get summary for LLM context."""
        if not self.turns:
            return ""

        recent = self.turns[-3:]  # Last 3 turns
        lines = ["Recent conversation:"]
        for turn in recent:
            lines.append(f"User: {turn.user_input}")
            lines.append(f"JARVIS: {turn.response[:100]}...")
        return "\n".join(lines)
```

---

### 3.3 Smart Suggestions System

**Purpose:** Proactively suggest actions based on context.

**New file:** `core/suggestions.py`

```python
"""Smart suggestions based on user patterns and context."""
from typing import List, Dict, Optional
from datetime import datetime, time
from dataclasses import dataclass

@dataclass
class Suggestion:
    """A proactive suggestion."""
    action: str
    description: str
    confidence: float
    reason: str
    params: Dict = None

class SuggestionEngine:
    """Generate smart suggestions based on patterns."""

    def __init__(self, memory_system):
        self.memory = memory_system
        self.time_patterns: Dict[str, List[str]] = {}
        self.app_sequences: Dict[str, List[str]] = {}

    def get_suggestions(self, context: Dict = None) -> List[Suggestion]:
        """Get contextual suggestions."""
        suggestions = []

        # Time-based suggestions
        time_suggestions = self._time_based_suggestions()
        suggestions.extend(time_suggestions)

        # Sequence-based suggestions
        if context and "last_app" in context:
            seq_suggestions = self._sequence_suggestions(context["last_app"])
            suggestions.extend(seq_suggestions)

        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:3]  # Top 3

    def _time_based_suggestions(self) -> List[Suggestion]:
        """Suggestions based on time of day patterns."""
        now = datetime.now()
        hour = now.hour

        suggestions = []

        # Morning routine (6-9 AM)
        if 6 <= hour < 9:
            suggestions.append(Suggestion(
                action="open_app",
                description="Open your morning apps",
                confidence=0.7,
                reason="You usually start with these apps in the morning",
                params={"app": "outlook"}  # Customize based on history
            ))

        # Work hours (9-5)
        elif 9 <= hour < 17:
            stats = self.memory.get_command_stats() if self.memory else {}
            top_intents = stats.get("top_intents", {})
            if top_intents:
                most_common = list(top_intents.keys())[0]
                suggestions.append(Suggestion(
                    action=most_common,
                    description=f"Your most common action: {most_common}",
                    confidence=0.6,
                    reason="Based on your usage patterns"
                ))

        return suggestions

    def _sequence_suggestions(self, last_app: str) -> List[Suggestion]:
        """Suggestions based on app usage sequences."""
        # Common sequences
        sequences = {
            "chrome": ["vscode", "terminal"],
            "outlook": ["teams", "calendar"],
            "vscode": ["terminal", "chrome"],
        }

        suggestions = []
        if last_app.lower() in sequences:
            for next_app in sequences[last_app.lower()]:
                suggestions.append(Suggestion(
                    action="open_app",
                    description=f"Open {next_app}?",
                    confidence=0.5,
                    reason=f"You often use {next_app} after {last_app}",
                    params={"app": next_app}
                ))

        return suggestions

    def learn_pattern(self, action: str, timestamp: datetime):
        """Learn from user actions to improve suggestions."""
        hour = timestamp.hour
        hour_key = f"hour_{hour}"

        if hour_key not in self.time_patterns:
            self.time_patterns[hour_key] = []

        self.time_patterns[hour_key].append(action)
```

---

### 3.4 Voice Customization & Multiple Assistants

**New file:** `ai/personalities.py`

```python
"""Multiple personality/assistant configurations."""
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

class PersonalityStyle(Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    CONCISE = "concise"
    DETAILED = "detailed"

@dataclass
class AssistantPersonality:
    """Configuration for an assistant personality."""
    name: str
    wake_word: str
    voice: str
    style: PersonalityStyle
    system_prompt_prefix: str
    greeting: str

class PersonalityManager:
    """Manage multiple assistant personalities."""

    DEFAULT_PERSONALITIES = {
        "jarvis": AssistantPersonality(
            name="JARVIS",
            wake_word="jarvis",
            voice="en_US-ryan-medium",  # Male professional
            style=PersonalityStyle.PROFESSIONAL,
            system_prompt_prefix="You are JARVIS, a professional AI assistant. Be helpful, precise, and efficient.",
            greeting="Good day, sir. How may I assist you?"
        ),
        "friday": AssistantPersonality(
            name="FRIDAY",
            wake_word="friday",
            voice="en_US-amy-medium",  # Female
            style=PersonalityStyle.CASUAL,
            system_prompt_prefix="You are FRIDAY, a friendly AI assistant. Be helpful and conversational.",
            greeting="Hey there! What can I do for you?"
        ),
        "hal": AssistantPersonality(
            name="HAL",
            wake_word="hal",
            voice="en_US-lessac-medium",
            style=PersonalityStyle.CONCISE,
            system_prompt_prefix="You are HAL, a precise AI. Give minimal, accurate responses.",
            greeting="I'm ready."
        ),
    }

    def __init__(self):
        self.personalities = self.DEFAULT_PERSONALITIES.copy()
        self.active: str = "jarvis"

    def get_active(self) -> AssistantPersonality:
        """Get the active personality."""
        return self.personalities[self.active]

    def switch(self, name: str) -> bool:
        """Switch to a different personality."""
        if name.lower() in self.personalities:
            self.active = name.lower()
            return True
        return False

    def add_custom(self, config: AssistantPersonality):
        """Add a custom personality."""
        self.personalities[config.name.lower()] = config
```

---

## Part 4: Wakey App Integration

### 4.1 Integration Architecture

Since both JARVIS and Wakey are desktop apps, the best approach is:

```
+----------------+                    +----------------+
|    JARVIS      |<-- Local API ----->|     Wakey      |
| (Python/CLI)   |   (localhost)      |  (Electron)    |
+----------------+                    +----------------+
        |                                    |
        v                                    v
+----------------+                    +----------------+
| SQLite/Chroma  |                    |   Wakey DB     |
|   (Memory)     |                    | (Tasks/Notes)  |
+----------------+                    +----------------+
        \                                   /
         \                                 /
          +-------------------------------+
          |     Shared Sync Service       |
          |   (Optional Cloud Backup)     |
          +-------------------------------+
```

### 4.2 Wakey Integration Module

**New file:** `integrations/wakey.py`

```python
"""JARVIS-Wakey Integration - Sync with Wakey productivity app."""
import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import aiohttp

@dataclass
class WakeyTask:
    """Task from Wakey."""
    id: str
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: int
    completed: bool
    tags: List[str]

@dataclass
class WakeyNote:
    """Note from Wakey."""
    id: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    folder: Optional[str]

@dataclass
class WakeyEvent:
    """Calendar event from Wakey."""
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    description: Optional[str]

class WakeyClient:
    """
    Client for communicating with Wakey Electron app.

    Wakey should expose a local HTTP API on localhost.
    """

    DEFAULT_PORT = 9876  # Wakey's local API port

    def __init__(self, port: int = None):
        self.port = port or self.DEFAULT_PORT
        self.base_url = f"http://localhost:{self.port}/api"
        self.connected = False
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Test connection to Wakey."""
        try:
            self._session = aiohttp.ClientSession()
            async with self._session.get(f"{self.base_url}/ping") as resp:
                if resp.status == 200:
                    self.connected = True
                    return True
        except:
            pass
        return False

    async def disconnect(self):
        """Close connection."""
        if self._session:
            await self._session.close()
        self.connected = False

    # ===== Tasks API =====

    async def get_tasks(self, filter_completed: bool = True) -> List[WakeyTask]:
        """Get all tasks from Wakey."""
        if not self.connected:
            await self.connect()

        try:
            params = {"completed": "false"} if filter_completed else {}
            async with self._session.get(f"{self.base_url}/tasks", params=params) as resp:
                data = await resp.json()
                return [self._parse_task(t) for t in data.get("tasks", [])]
        except:
            return []

    async def create_task(self, title: str, description: str = None,
                          due_date: datetime = None, priority: int = 1) -> Optional[WakeyTask]:
        """Create a new task in Wakey."""
        if not self.connected:
            await self.connect()

        payload = {
            "title": title,
            "description": description,
            "due_date": due_date.isoformat() if due_date else None,
            "priority": priority,
        }

        try:
            async with self._session.post(f"{self.base_url}/tasks", json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return self._parse_task(data)
        except:
            pass
        return None

    async def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed."""
        try:
            async with self._session.patch(
                f"{self.base_url}/tasks/{task_id}",
                json={"completed": True}
            ) as resp:
                return resp.status == 200
        except:
            return False

    # ===== Notes API =====

    async def get_notes(self, folder: str = None) -> List[WakeyNote]:
        """Get notes from Wakey."""
        if not self.connected:
            await self.connect()

        try:
            params = {"folder": folder} if folder else {}
            async with self._session.get(f"{self.base_url}/notes", params=params) as resp:
                data = await resp.json()
                return [self._parse_note(n) for n in data.get("notes", [])]
        except:
            return []

    async def create_note(self, title: str, content: str, folder: str = None) -> Optional[WakeyNote]:
        """Create a note in Wakey."""
        if not self.connected:
            await self.connect()

        payload = {"title": title, "content": content, "folder": folder}

        try:
            async with self._session.post(f"{self.base_url}/notes", json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return self._parse_note(data)
        except:
            pass
        return None

    async def search_notes(self, query: str) -> List[WakeyNote]:
        """Search notes by content."""
        try:
            async with self._session.get(
                f"{self.base_url}/notes/search",
                params={"q": query}
            ) as resp:
                data = await resp.json()
                return [self._parse_note(n) for n in data.get("notes", [])]
        except:
            return []

    # ===== Calendar API =====

    async def get_events(self, start: datetime = None, end: datetime = None) -> List[WakeyEvent]:
        """Get calendar events from Wakey."""
        if not self.connected:
            await self.connect()

        try:
            params = {}
            if start:
                params["start"] = start.isoformat()
            if end:
                params["end"] = end.isoformat()

            async with self._session.get(f"{self.base_url}/events", params=params) as resp:
                data = await resp.json()
                return [self._parse_event(e) for e in data.get("events", [])]
        except:
            return []

    async def create_event(self, title: str, start_time: datetime,
                           end_time: datetime, location: str = None) -> Optional[WakeyEvent]:
        """Create a calendar event in Wakey."""
        if not self.connected:
            await self.connect()

        payload = {
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "location": location,
        }

        try:
            async with self._session.post(f"{self.base_url}/events", json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return self._parse_event(data)
        except:
            pass
        return None

    # ===== Reminders API =====

    async def get_reminders(self) -> List[Dict]:
        """Get active reminders."""
        try:
            async with self._session.get(f"{self.base_url}/reminders") as resp:
                data = await resp.json()
                return data.get("reminders", [])
        except:
            return []

    async def create_reminder(self, message: str, remind_at: datetime) -> bool:
        """Create a reminder in Wakey."""
        try:
            async with self._session.post(
                f"{self.base_url}/reminders",
                json={"message": message, "remind_at": remind_at.isoformat()}
            ) as resp:
                return resp.status == 201
        except:
            return False

    # ===== Parsers =====

    def _parse_task(self, data: Dict) -> WakeyTask:
        return WakeyTask(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            priority=data.get("priority", 1),
            completed=data.get("completed", False),
            tags=data.get("tags", []),
        )

    def _parse_note(self, data: Dict) -> WakeyNote:
        return WakeyNote(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            folder=data.get("folder"),
        )

    def _parse_event(self, data: Dict) -> WakeyEvent:
        return WakeyEvent(
            id=data["id"],
            title=data["title"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            location=data.get("location"),
            description=data.get("description"),
        )


# Sync singleton
_wakey_client: Optional[WakeyClient] = None

def get_wakey_client() -> WakeyClient:
    """Get or create Wakey client."""
    global _wakey_client
    if _wakey_client is None:
        _wakey_client = WakeyClient()
    return _wakey_client
```

---

### 4.3 Wakey JARVIS Tools

**New file:** `tools/wakey_tools.py`

```python
"""JARVIS tools for Wakey integration."""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from tools.registry import tool, ToolResult, RiskLevel
from integrations.wakey import get_wakey_client, WakeyClient

def run_async(coro):
    """Run async code from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

# ===== Task Tools =====

@tool(
    name="wakey_list_tasks",
    description="List your tasks from Wakey",
    category="productivity",
    examples=["show my tasks", "what do I need to do", "list todos"],
)
def wakey_list_tasks(include_completed: bool = False) -> ToolResult:
    """Get tasks from Wakey."""
    try:
        client = get_wakey_client()
        tasks = run_async(client.get_tasks(filter_completed=not include_completed))

        if not tasks:
            return ToolResult(success=True, output="No pending tasks!")

        output = []
        for task in tasks[:10]:  # Top 10
            status = "[x]" if task.completed else "[ ]"
            due = f" (due: {task.due_date.strftime('%b %d')})" if task.due_date else ""
            output.append(f"{status} {task.title}{due}")

        return ToolResult(success=True, output="\n".join(output))
    except Exception as e:
        return ToolResult(success=False, error=f"Could not get tasks: {e}")


@tool(
    name="wakey_add_task",
    description="Add a new task to Wakey",
    category="productivity",
    examples=["add task buy groceries", "remind me to call mom", "create todo"],
)
def wakey_add_task(
    title: str,
    due_date: Optional[str] = None,
    priority: int = 1
) -> ToolResult:
    """Create a task in Wakey."""
    try:
        client = get_wakey_client()

        # Parse due date
        due = None
        if due_date:
            # Support natural language like "tomorrow", "next week"
            due_lower = due_date.lower()
            if "tomorrow" in due_lower:
                due = datetime.now() + timedelta(days=1)
            elif "next week" in due_lower:
                due = datetime.now() + timedelta(weeks=1)
            else:
                try:
                    due = datetime.fromisoformat(due_date)
                except:
                    pass

        task = run_async(client.create_task(title, due_date=due, priority=priority))

        if task:
            return ToolResult(success=True, output=f"Created task: {task.title}")
        return ToolResult(success=False, error="Failed to create task")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="wakey_complete_task",
    description="Mark a task as completed in Wakey",
    category="productivity",
    examples=["complete task 1", "mark task done", "finish task"],
)
def wakey_complete_task(task_id: str) -> ToolResult:
    """Complete a task."""
    try:
        client = get_wakey_client()
        success = run_async(client.complete_task(task_id))

        if success:
            return ToolResult(success=True, output="Task marked as completed!")
        return ToolResult(success=False, error="Could not complete task")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ===== Notes Tools =====

@tool(
    name="wakey_search_notes",
    description="Search your notes in Wakey",
    category="productivity",
    examples=["search notes for meeting", "find note about project"],
)
def wakey_search_notes(query: str) -> ToolResult:
    """Search notes in Wakey."""
    try:
        client = get_wakey_client()
        notes = run_async(client.search_notes(query))

        if not notes:
            return ToolResult(success=True, output=f"No notes found for '{query}'")

        output = [f"Found {len(notes)} notes:"]
        for note in notes[:5]:
            preview = note.content[:100] + "..." if len(note.content) > 100 else note.content
            output.append(f"- {note.title}: {preview}")

        return ToolResult(success=True, output="\n".join(output))
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="wakey_create_note",
    description="Create a new note in Wakey",
    category="productivity",
    examples=["create note meeting summary", "save note"],
)
def wakey_create_note(title: str, content: str, folder: str = None) -> ToolResult:
    """Create a note in Wakey."""
    try:
        client = get_wakey_client()
        note = run_async(client.create_note(title, content, folder))

        if note:
            return ToolResult(success=True, output=f"Created note: {note.title}")
        return ToolResult(success=False, error="Failed to create note")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ===== Calendar Tools =====

@tool(
    name="wakey_get_schedule",
    description="Get your schedule from Wakey calendar",
    category="productivity",
    examples=["what's on my calendar", "show my schedule", "meetings today"],
)
def wakey_get_schedule(days: int = 1) -> ToolResult:
    """Get upcoming events."""
    try:
        client = get_wakey_client()
        start = datetime.now()
        end = start + timedelta(days=days)

        events = run_async(client.get_events(start, end))

        if not events:
            return ToolResult(success=True, output=f"No events in the next {days} day(s)")

        output = [f"Upcoming events ({days} day(s)):"]
        for event in events:
            time_str = event.start_time.strftime("%I:%M %p")
            date_str = event.start_time.strftime("%b %d")
            loc = f" @ {event.location}" if event.location else ""
            output.append(f"- {date_str} {time_str}: {event.title}{loc}")

        return ToolResult(success=True, output="\n".join(output))
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="wakey_add_event",
    description="Add an event to Wakey calendar",
    category="productivity",
    examples=["schedule meeting at 3pm", "add event lunch with john"],
)
def wakey_add_event(
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    location: str = None
) -> ToolResult:
    """Create a calendar event."""
    try:
        client = get_wakey_client()

        # Parse start time
        start = datetime.fromisoformat(start_time)
        end = start + timedelta(minutes=duration_minutes)

        event = run_async(client.create_event(title, start, end, location))

        if event:
            return ToolResult(
                success=True,
                output=f"Created event: {event.title} at {event.start_time.strftime('%I:%M %p')}"
            )
        return ToolResult(success=False, error="Failed to create event")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="wakey_set_reminder",
    description="Set a reminder in Wakey",
    category="productivity",
    examples=["remind me to drink water", "set reminder for 3pm"],
)
def wakey_set_reminder(message: str, remind_at: str = None) -> ToolResult:
    """Create a reminder."""
    try:
        client = get_wakey_client()

        # Default to 1 hour from now
        if remind_at:
            remind_time = datetime.fromisoformat(remind_at)
        else:
            remind_time = datetime.now() + timedelta(hours=1)

        success = run_async(client.create_reminder(message, remind_time))

        if success:
            return ToolResult(
                success=True,
                output=f"Reminder set for {remind_time.strftime('%I:%M %p')}: {message}"
            )
        return ToolResult(success=False, error="Failed to set reminder")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def register_wakey_tools():
    """Register all Wakey tools."""
    # Tools are auto-registered via decorators
    pass
```

---

### 4.4 Wakey API Specification (For Electron App)

**File to create in Wakey project:** `API_SPEC.md`

```markdown
# Wakey Local API Specification

Wakey exposes a local HTTP API on `localhost:9876` for integration with JARVIS.

## Base URL
`http://localhost:9876/api`

## Authentication
No authentication required (local-only API).

## Endpoints

### Health Check
```
GET /ping
Response: { "status": "ok", "version": "1.0.0" }
```

### Tasks
```
GET /tasks?completed=false
POST /tasks { title, description?, due_date?, priority? }
PATCH /tasks/:id { completed?, title?, ... }
DELETE /tasks/:id
```

### Notes
```
GET /notes?folder=...
GET /notes/search?q=...
POST /notes { title, content, folder? }
PATCH /notes/:id { title?, content? }
DELETE /notes/:id
```

### Calendar Events
```
GET /events?start=ISO&end=ISO
POST /events { title, start_time, end_time, location? }
PATCH /events/:id { ... }
DELETE /events/:id
```

### Reminders
```
GET /reminders
POST /reminders { message, remind_at }
DELETE /reminders/:id
```
```

---

## Part 5: Implementation Phases

### Phase 1: Critical Fixes (Day 1-2)
1. Fix import collision in `tools/__init__.py`
2. Fix method name mismatches in `ui/server.py`
3. Fix ChromaDB API in `core/memory.py`
4. Create dependency installer script
5. Test basic functionality

### Phase 2: Core Enhancements (Day 3-5)
1. Add conversation context tracking
2. Implement screen context awareness
3. Add smart suggestions engine
4. Create personality system

### Phase 3: Wakey Integration (Day 6-8)
1. Implement WakeyClient
2. Create Wakey tools
3. Add intent mappings for Wakey commands
4. Test integration

### Phase 4: Polish & Testing (Day 9-10)
1. End-to-end testing
2. Error handling improvements
3. Documentation updates
4. Performance optimization

---

## File Change Summary

### Files to Modify:
1. `tools/__init__.py` - Fix imports
2. `ui/server.py` - Fix method names
3. `core/memory.py` - Update ChromaDB API
4. `core/agent.py` - Add conversation context
5. `core/intent_parser.py` - Add Wakey intents

### Files to Rename:
1. `tools/system.py` -> `tools/system_tools.py`

### New Files to Create:
1. `scripts/install.py` - Dependency installer
2. `tools/vision/screen_context.py` - Screen awareness
3. `core/conversation.py` - Conversation tracking
4. `core/suggestions.py` - Smart suggestions
5. `ai/personalities.py` - Multi-personality
6. `integrations/wakey.py` - Wakey client
7. `tools/wakey_tools.py` - Wakey JARVIS tools

---

## Quick Start After Fixes

```bash
# 1. Install dependencies
cd jarvis-ai
python scripts/install.py

# 2. Start Ollama (in separate terminal)
ollama serve

# 3. Pull LLM model
ollama pull phi3:mini

# 4. Run JARVIS
python main.py --text  # Text mode for testing
# or
python main.py  # Voice mode

# 5. Run Web UI
python ui/server.py
```

---

**End of Implementation Plan**
