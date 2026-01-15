"""
JARVIS Reminders - Time-based task reminders.

Provides scheduling and notification for reminders.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import time

from tools.registry import tool, ToolResult


@dataclass
class Reminder:
    """A reminder entry."""
    id: str
    message: str
    due_time: datetime
    created_at: datetime
    repeat: Optional[str] = None  # daily, weekly, monthly
    completed: bool = False
    notified: bool = False


class ReminderManager:
    """
    Manage time-based reminders.
    
    Features:
    - One-time and recurring reminders
    - Natural language time parsing
    - Persistence to JSON
    - Background notification thread
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/reminders.json",
        on_reminder: Optional[Callable[[Reminder], None]] = None,
    ):
        """
        Initialize reminder manager.
        
        Args:
            storage_path: Path to store reminders
            on_reminder: Callback when reminder is due
        """
        self.storage_path = storage_path
        self.on_reminder = on_reminder
        self.reminders: Dict[str, Reminder] = {}
        self._load()
        
        # Background checker
        self._running = False
        self._thread = None
    
    def _load(self):
        """Load reminders from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                for item in data:
                    item['due_time'] = datetime.fromisoformat(item['due_time'])
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                    reminder = Reminder(**item)
                    self.reminders[reminder.id] = reminder
            except Exception:
                pass
    
    def _save(self):
        """Save reminders to storage."""
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = []
        for r in self.reminders.values():
            item = asdict(r)
            item['due_time'] = r.due_time.isoformat()
            item['created_at'] = r.created_at.isoformat()
            data.append(item)
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add(
        self,
        message: str,
        due_time: datetime,
        repeat: Optional[str] = None,
    ) -> Reminder:
        """Add a new reminder."""
        reminder_id = f"rem_{datetime.now().timestamp()}"
        
        reminder = Reminder(
            id=reminder_id,
            message=message,
            due_time=due_time,
            created_at=datetime.now(),
            repeat=repeat,
        )
        
        self.reminders[reminder_id] = reminder
        self._save()
        
        return reminder
    
    def add_from_text(self, text: str) -> Reminder:
        """
        Add reminder from natural language.
        
        Examples:
        - "remind me to call mom in 30 minutes"
        - "meeting at 3pm tomorrow"
        """
        message, due_time = self._parse_reminder_text(text)
        return self.add(message, due_time)
    
    def _parse_reminder_text(self, text: str) -> tuple[str, datetime]:
        """Parse natural language reminder text."""
        now = datetime.now()
        text_lower = text.lower()
        
        # Extract time patterns
        if "in " in text_lower:
            # Relative time: "in 30 minutes", "in 2 hours"
            import re
            match = re.search(r'in (\d+) (minute|hour|day|week)s?', text_lower)
            if match:
                amount = int(match.group(1))
                unit = match.group(2)
                
                if unit == 'minute':
                    due_time = now + timedelta(minutes=amount)
                elif unit == 'hour':
                    due_time = now + timedelta(hours=amount)
                elif unit == 'day':
                    due_time = now + timedelta(days=amount)
                elif unit == 'week':
                    due_time = now + timedelta(weeks=amount)
                else:
                    due_time = now + timedelta(hours=1)
                
                # Extract message (remove time part)
                message = re.sub(r'in \d+ \w+s?', '', text).strip()
                message = message.replace('remind me to', '').replace('remind me', '').strip()
                
                return message or text, due_time
        
        if "tomorrow" in text_lower:
            due_time = now + timedelta(days=1)
            due_time = due_time.replace(hour=9, minute=0)
            message = text_lower.replace('tomorrow', '').strip()
            return message or text, due_time
        
        # Default: 1 hour from now
        return text, now + timedelta(hours=1)
    
    def get(self, reminder_id: str) -> Optional[Reminder]:
        """Get reminder by ID."""
        return self.reminders.get(reminder_id)
    
    def list_pending(self) -> List[Reminder]:
        """List all pending reminders."""
        return [
            r for r in self.reminders.values()
            if not r.completed
        ]
    
    def list_due(self) -> List[Reminder]:
        """List reminders that are due now."""
        now = datetime.now()
        return [
            r for r in self.reminders.values()
            if not r.completed and r.due_time <= now
        ]
    
    def complete(self, reminder_id: str) -> bool:
        """Mark reminder as completed."""
        reminder = self.reminders.get(reminder_id)
        if reminder:
            if reminder.repeat:
                # Reschedule recurring reminder
                if reminder.repeat == 'daily':
                    reminder.due_time += timedelta(days=1)
                elif reminder.repeat == 'weekly':
                    reminder.due_time += timedelta(weeks=1)
                elif reminder.repeat == 'monthly':
                    reminder.due_time += timedelta(days=30)
                reminder.notified = False
            else:
                reminder.completed = True
            
            self._save()
            return True
        return False
    
    def delete(self, reminder_id: str) -> bool:
        """Delete a reminder."""
        if reminder_id in self.reminders:
            del self.reminders[reminder_id]
            self._save()
            return True
        return False
    
    def start_background_checker(self, interval: int = 60):
        """Start background thread to check for due reminders."""
        if self._running:
            return
        
        self._running = True
        
        def checker():
            while self._running:
                due = self.list_due()
                for reminder in due:
                    if not reminder.notified:
                        reminder.notified = True
                        if self.on_reminder:
                            self.on_reminder(reminder)
                        self._save()
                time.sleep(interval)
        
        self._thread = threading.Thread(target=checker, daemon=True)
        self._thread.start()
    
    def stop_background_checker(self):
        """Stop background checker."""
        self._running = False


# Tool registrations
@tool(
    name="set_reminder",
    description="Set a reminder for a future time",
    category="productivity",
    examples=["remind me to call mom in 30 minutes", "set reminder for meeting at 3pm"],
)
def set_reminder(text: str) -> ToolResult:
    """Set a reminder from natural language."""
    try:
        manager = ReminderManager()
        reminder = manager.add_from_text(text)
        
        return ToolResult(
            success=True,
            output={
                "id": reminder.id,
                "message": reminder.message,
                "due": reminder.due_time.strftime("%Y-%m-%d %H:%M"),
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="list_reminders",
    description="List all pending reminders",
    category="productivity",
)
def list_reminders() -> ToolResult:
    """List pending reminders."""
    try:
        manager = ReminderManager()
        pending = manager.list_pending()
        
        reminders = [
            {
                "id": r.id,
                "message": r.message,
                "due": r.due_time.strftime("%Y-%m-%d %H:%M"),
            }
            for r in sorted(pending, key=lambda x: x.due_time)
        ]
        
        return ToolResult(success=True, output=reminders)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="complete_reminder",
    description="Mark a reminder as completed",
    category="productivity",
)
def complete_reminder(reminder_id: str) -> ToolResult:
    """Complete a reminder."""
    try:
        manager = ReminderManager()
        success = manager.complete(reminder_id)
        
        if success:
            return ToolResult(success=True, output="Reminder completed")
        else:
            return ToolResult(success=False, error="Reminder not found")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Reminders...")
    
    manager = ReminderManager(storage_path="./test_reminders.json")
    
    # Add reminder
    reminder = manager.add_from_text("remind me to check email in 30 minutes")
    print(f"Added: {reminder.message} at {reminder.due_time}")
    
    # List pending
    print(f"\nPending reminders: {len(manager.list_pending())}")
    
    # Complete
    manager.complete(reminder.id)
    print(f"Completed: {reminder.id}")
    
    # Cleanup
    os.remove("./test_reminders.json")
    print("\nTests complete!")
