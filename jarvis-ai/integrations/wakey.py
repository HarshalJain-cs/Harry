"""
JARVIS-Wakey Integration - Sync with Wakey productivity app.

Connects to Wakey Electron app's local HTTP API for:
- Task management
- Notes
- Calendar events
- Reminders
"""

import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


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

    Wakey exposes a local HTTP API on localhost for JARVIS integration.
    
    Features:
    - Task management (create, list, complete)
    - Notes (create, search)
    - Calendar (events, scheduling)
    - Reminders
    """

    DEFAULT_PORT = 9876  # Wakey's local API port

    def __init__(self, port: int = None):
        """
        Initialize Wakey client.
        
        Args:
            port: Port number for Wakey API (default: 9876)
        """
        self.port = port or self.DEFAULT_PORT
        self.base_url = f"http://localhost:{self.port}/api"
        self.connected = False
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """
        Test connection to Wakey.
        
        Returns:
            True if connected successfully
        """
        if not AIOHTTP_AVAILABLE:
            print("aiohttp not installed. Run: pip install aiohttp")
            return False

        try:
            self._session = aiohttp.ClientSession()
            async with self._session.get(f"{self.base_url}/ping", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    self.connected = True
                    return True
        except Exception as e:
            print(f"Could not connect to Wakey: {e}")
        return False

    async def disconnect(self):
        """Close connection."""
        if self._session:
            await self._session.close()
            self._session = None
        self.connected = False

    async def _ensure_connected(self) -> bool:
        """Ensure we have a valid connection."""
        if not self.connected or not self._session:
            return await self.connect()
        return True

    # ===== Tasks API =====

    async def get_tasks(self, filter_completed: bool = True) -> List[WakeyTask]:
        """
        Get all tasks from Wakey.
        
        Args:
            filter_completed: If True, only return incomplete tasks
            
        Returns:
            List of WakeyTask objects
        """
        if not await self._ensure_connected():
            return []

        try:
            params = {"completed": "false"} if filter_completed else {}
            async with self._session.get(f"{self.base_url}/tasks", params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [self._parse_task(t) for t in data.get("tasks", [])]
        except Exception as e:
            print(f"Error getting tasks: {e}")
        return []

    async def create_task(
        self,
        title: str,
        description: str = None,
        due_date: datetime = None,
        priority: int = 1,
        tags: List[str] = None,
    ) -> Optional[WakeyTask]:
        """
        Create a new task in Wakey.
        
        Args:
            title: Task title
            description: Optional description
            due_date: Optional due date
            priority: Priority level (1-5)
            tags: Optional list of tags
            
        Returns:
            Created WakeyTask or None
        """
        if not await self._ensure_connected():
            return None

        payload = {
            "title": title,
            "description": description,
            "due_date": due_date.isoformat() if due_date else None,
            "priority": priority,
            "tags": tags or [],
        }

        try:
            async with self._session.post(f"{self.base_url}/tasks", json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return self._parse_task(data)
        except Exception as e:
            print(f"Error creating task: {e}")
        return None

    async def complete_task(self, task_id: str) -> bool:
        """
        Mark a task as completed.
        
        Args:
            task_id: ID of the task to complete
            
        Returns:
            True if successful
        """
        if not await self._ensure_connected():
            return False

        try:
            async with self._session.patch(
                f"{self.base_url}/tasks/{task_id}",
                json={"completed": True}
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"Error completing task: {e}")
        return False

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if not await self._ensure_connected():
            return False

        try:
            async with self._session.delete(f"{self.base_url}/tasks/{task_id}") as resp:
                return resp.status == 200
        except:
            return False

    # ===== Notes API =====

    async def get_notes(self, folder: str = None, limit: int = 20) -> List[WakeyNote]:
        """
        Get notes from Wakey.
        
        Args:
            folder: Optional folder to filter by
            limit: Maximum number of notes to return
            
        Returns:
            List of WakeyNote objects
        """
        if not await self._ensure_connected():
            return []

        try:
            params = {"limit": limit}
            if folder:
                params["folder"] = folder
                
            async with self._session.get(f"{self.base_url}/notes", params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [self._parse_note(n) for n in data.get("notes", [])]
        except Exception as e:
            print(f"Error getting notes: {e}")
        return []

    async def create_note(
        self,
        title: str,
        content: str,
        folder: str = None,
    ) -> Optional[WakeyNote]:
        """
        Create a note in Wakey.
        
        Args:
            title: Note title
            content: Note content
            folder: Optional folder name
            
        Returns:
            Created WakeyNote or None
        """
        if not await self._ensure_connected():
            return None

        payload = {"title": title, "content": content}
        if folder:
            payload["folder"] = folder

        try:
            async with self._session.post(f"{self.base_url}/notes", json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return self._parse_note(data)
        except Exception as e:
            print(f"Error creating note: {e}")
        return None

    async def search_notes(self, query: str) -> List[WakeyNote]:
        """
        Search notes by content.
        
        Args:
            query: Search query
            
        Returns:
            List of matching WakeyNote objects
        """
        if not await self._ensure_connected():
            return []

        try:
            async with self._session.get(
                f"{self.base_url}/notes/search",
                params={"q": query}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [self._parse_note(n) for n in data.get("notes", [])]
        except Exception as e:
            print(f"Error searching notes: {e}")
        return []

    # ===== Calendar API =====

    async def get_events(
        self,
        start: datetime = None,
        end: datetime = None,
    ) -> List[WakeyEvent]:
        """
        Get calendar events from Wakey.
        
        Args:
            start: Start of date range
            end: End of date range
            
        Returns:
            List of WakeyEvent objects
        """
        if not await self._ensure_connected():
            return []

        try:
            params = {}
            if start:
                params["start"] = start.isoformat()
            if end:
                params["end"] = end.isoformat()

            async with self._session.get(f"{self.base_url}/events", params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [self._parse_event(e) for e in data.get("events", [])]
        except Exception as e:
            print(f"Error getting events: {e}")
        return []

    async def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        location: str = None,
        description: str = None,
    ) -> Optional[WakeyEvent]:
        """
        Create a calendar event in Wakey.
        
        Args:
            title: Event title
            start_time: Event start time
            end_time: Event end time
            location: Optional location
            description: Optional description
            
        Returns:
            Created WakeyEvent or None
        """
        if not await self._ensure_connected():
            return None

        payload = {
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
        if location:
            payload["location"] = location
        if description:
            payload["description"] = description

        try:
            async with self._session.post(f"{self.base_url}/events", json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return self._parse_event(data)
        except Exception as e:
            print(f"Error creating event: {e}")
        return None

    # ===== Reminders API =====

    async def get_reminders(self) -> List[Dict]:
        """
        Get active reminders.
        
        Returns:
            List of reminder dictionaries
        """
        if not await self._ensure_connected():
            return []

        try:
            async with self._session.get(f"{self.base_url}/reminders") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("reminders", [])
        except Exception as e:
            print(f"Error getting reminders: {e}")
        return []

    async def create_reminder(self, message: str, remind_at: datetime) -> bool:
        """
        Create a reminder in Wakey.
        
        Args:
            message: Reminder message
            remind_at: When to remind
            
        Returns:
            True if successful
        """
        if not await self._ensure_connected():
            return False

        try:
            async with self._session.post(
                f"{self.base_url}/reminders",
                json={"message": message, "remind_at": remind_at.isoformat()}
            ) as resp:
                return resp.status == 201
        except Exception as e:
            print(f"Error creating reminder: {e}")
        return False

    # ===== Parsers =====

    def _parse_task(self, data: Dict) -> WakeyTask:
        """Parse task from API response."""
        return WakeyTask(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            priority=data.get("priority", 1),
            completed=data.get("completed", False),
            tags=data.get("tags", []),
        )

    def _parse_note(self, data: Dict) -> WakeyNote:
        """Parse note from API response."""
        return WakeyNote(
            id=data.get("id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            folder=data.get("folder"),
        )

    def _parse_event(self, data: Dict) -> WakeyEvent:
        """Parse event from API response."""
        return WakeyEvent(
            id=data.get("id", ""),
            title=data.get("title", ""),
            start_time=datetime.fromisoformat(data.get("start_time", datetime.now().isoformat())),
            end_time=datetime.fromisoformat(data.get("end_time", datetime.now().isoformat())),
            location=data.get("location"),
            description=data.get("description"),
        )


# Sync singleton
_wakey_client: Optional[WakeyClient] = None


def get_wakey_client() -> WakeyClient:
    """Get or create Wakey client singleton."""
    global _wakey_client
    if _wakey_client is None:
        _wakey_client = WakeyClient()
    return _wakey_client


# Synchronous wrapper for tools
def run_async(coro):
    """Run async code from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, use nest_asyncio
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except ImportError:
                pass
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


if __name__ == "__main__":
    # Test Wakey client
    print("Testing Wakey Client...")
    
    async def test():
        client = WakeyClient()
        
        # Try to connect
        connected = await client.connect()
        print(f"Connected to Wakey: {connected}")
        
        if connected:
            # Get tasks
            tasks = await client.get_tasks()
            print(f"Tasks: {len(tasks)}")
            
            # Get notes
            notes = await client.get_notes()
            print(f"Notes: {len(notes)}")
        else:
            print("Could not connect to Wakey.")
            print("Make sure Wakey is running with local API enabled.")
        
        await client.disconnect()
    
    asyncio.run(test())
    print("\nWakey client test complete!")
