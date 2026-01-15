"""
JARVIS Calendar Integration - Calendar and event management.

Provides calendar access and event scheduling.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CalendarEvent:
    """A calendar event."""
    id: str
    title: str
    start: datetime
    end: datetime
    description: str = ""
    location: str = ""
    all_day: bool = False
    recurring: Optional[str] = None  # daily, weekly, monthly
    reminder_minutes: int = 15
    calendar: str = "default"


class CalendarManager:
    """
    Local calendar manager.
    
    Features:
    - Event creation/editing
    - Recurring events
    - Reminders
    - Multiple calendars
    - Free/busy checking
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/calendar.json",
    ):
        """
        Initialize calendar manager.
        
        Args:
            storage_path: Path for calendar data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.events: List[CalendarEvent] = []
        self.calendars: List[str] = ["default", "work", "personal"]
        
        self._load()
    
    def _load(self):
        """Load calendar data."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                self.calendars = data.get("calendars", self.calendars)
                
                for event_data in data.get("events", []):
                    event_data['start'] = datetime.fromisoformat(event_data['start'])
                    event_data['end'] = datetime.fromisoformat(event_data['end'])
                    self.events.append(CalendarEvent(**event_data))
            except Exception:
                pass
    
    def _save(self):
        """Save calendar data."""
        data = {
            "calendars": self.calendars,
            "events": [
                {
                    **asdict(e),
                    "start": e.start.isoformat(),
                    "end": e.end.isoformat(),
                }
                for e in self.events
            ],
        }
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_event(
        self,
        title: str,
        start: datetime,
        end: datetime = None,
        description: str = "",
        location: str = "",
        all_day: bool = False,
        calendar: str = "default",
        recurring: str = None,
        reminder_minutes: int = 15,
    ) -> CalendarEvent:
        """
        Add a calendar event.
        
        Args:
            title: Event title
            start: Start time
            end: End time (defaults to 1 hour after start)
            description: Event description
            location: Event location
            all_day: All-day event
            calendar: Calendar name
            recurring: Recurrence pattern
            reminder_minutes: Minutes before to remind
            
        Returns:
            CalendarEvent
        """
        if end is None:
            end = start + timedelta(hours=1)
        
        event = CalendarEvent(
            id=f"evt_{datetime.now().timestamp()}",
            title=title,
            start=start,
            end=end,
            description=description,
            location=location,
            all_day=all_day,
            recurring=recurring,
            reminder_minutes=reminder_minutes,
            calendar=calendar,
        )
        
        self.events.append(event)
        self._save()
        
        return event
    
    def update_event(self, event_id: str, **kwargs) -> Optional[CalendarEvent]:
        """Update an event."""
        for event in self.events:
            if event.id == event_id:
                for key, value in kwargs.items():
                    if hasattr(event, key):
                        setattr(event, key, value)
                self._save()
                return event
        return None
    
    def delete_event(self, event_id: str) -> bool:
        """Delete an event."""
        for i, event in enumerate(self.events):
            if event.id == event_id:
                del self.events[i]
                self._save()
                return True
        return False
    
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get event by ID."""
        for event in self.events:
            if event.id == event_id:
                return event
        return None
    
    def get_events_for_day(self, date: datetime) -> List[CalendarEvent]:
        """Get events for a specific day."""
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        events = []
        for event in self.events:
            if event.start >= day_start and event.start < day_end:
                events.append(event)
        
        return sorted(events, key=lambda e: e.start)
    
    def get_today(self) -> List[CalendarEvent]:
        """Get today's events."""
        return self.get_events_for_day(datetime.now())
    
    def get_upcoming(self, days: int = 7) -> List[CalendarEvent]:
        """Get upcoming events."""
        now = datetime.now()
        future = now + timedelta(days=days)
        
        events = []
        for event in self.events:
            if event.start >= now and event.start <= future:
                events.append(event)
        
        return sorted(events, key=lambda e: e.start)
    
    def get_events_range(
        self,
        start: datetime,
        end: datetime,
        calendar: str = None,
    ) -> List[CalendarEvent]:
        """Get events in a date range."""
        events = []
        for event in self.events:
            if event.start >= start and event.end <= end:
                if calendar is None or event.calendar == calendar:
                    events.append(event)
        
        return sorted(events, key=lambda e: e.start)
    
    def is_busy(self, start: datetime, end: datetime) -> bool:
        """Check if time slot is busy."""
        for event in self.events:
            if event.all_day:
                continue
            
            # Check for overlap
            if start < event.end and end > event.start:
                return True
        
        return False
    
    def find_free_slot(
        self,
        duration_minutes: int = 60,
        start_from: datetime = None,
        within_hours: int = 24,
    ) -> Optional[datetime]:
        """
        Find a free time slot.
        
        Args:
            duration_minutes: Required duration
            start_from: Start searching from
            within_hours: Search window
            
        Returns:
            Start time of free slot or None
        """
        if start_from is None:
            start_from = datetime.now()
        
        end_search = start_from + timedelta(hours=within_hours)
        duration = timedelta(minutes=duration_minutes)
        
        # Check slots every 30 minutes
        current = start_from.replace(minute=0, second=0, microsecond=0)
        if current < start_from:
            current += timedelta(hours=1)
        
        while current + duration <= end_search:
            if not self.is_busy(current, current + duration):
                return current
            current += timedelta(minutes=30)
        
        return None
    
    def get_due_reminders(self) -> List[CalendarEvent]:
        """Get events with due reminders."""
        now = datetime.now()
        upcoming = []
        
        for event in self.events:
            reminder_time = event.start - timedelta(minutes=event.reminder_minutes)
            
            if reminder_time <= now < event.start:
                upcoming.append(event)
        
        return upcoming


from tools.registry import tool, ToolResult


@tool(
    name="add_event",
    description="Add a calendar event",
    category="calendar",
    examples=["add meeting tomorrow at 2pm", "schedule call for Friday at 10am"],
)
def add_event(
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str = "",
) -> ToolResult:
    """Add calendar event."""
    try:
        calendar = CalendarManager()
        
        # Parse start time (simplified)
        try:
            start = datetime.fromisoformat(start_time)
        except:
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M"]:
                try:
                    start = datetime.strptime(start_time, fmt)
                    if fmt == "%H:%M":
                        today = datetime.now().date()
                        start = datetime.combine(today, start.time())
                    break
                except:
                    continue
            else:
                return ToolResult(success=False, error=f"Invalid time: {start_time}")
        
        end = start + timedelta(minutes=duration_minutes)
        event = calendar.add_event(title, start, end, description)
        
        return ToolResult(
            success=True,
            output={
                "title": event.title,
                "start": event.start.strftime("%Y-%m-%d %H:%M"),
                "end": event.end.strftime("%H:%M"),
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_calendar",
    description="Get calendar events",
    category="calendar",
    examples=["what's on my calendar today", "show upcoming events"],
)
def get_calendar(days: int = 1) -> ToolResult:
    """Get calendar events."""
    try:
        calendar = CalendarManager()
        
        if days == 1:
            events = calendar.get_today()
        else:
            events = calendar.get_upcoming(days)
        
        return ToolResult(
            success=True,
            output=[
                {
                    "title": e.title,
                    "start": e.start.strftime("%a %H:%M"),
                    "location": e.location or "-",
                }
                for e in events
            ],
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="find_free_time",
    description="Find a free time slot on calendar",
    category="calendar",
)
def find_free_time(duration_minutes: int = 60) -> ToolResult:
    """Find free slot."""
    try:
        calendar = CalendarManager()
        slot = calendar.find_free_slot(duration_minutes)
        
        if slot:
            return ToolResult(
                success=True,
                output=f"Free slot: {slot.strftime('%A %Y-%m-%d %H:%M')}",
            )
        return ToolResult(success=False, error="No free slot found")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Calendar Manager...")
    
    calendar = CalendarManager(storage_path="./test_calendar.json")
    
    # Add events
    now = datetime.now()
    calendar.add_event("Team Meeting", now + timedelta(hours=2))
    calendar.add_event("Lunch", now + timedelta(hours=4), location="Cafe")
    calendar.add_event("Review", now + timedelta(days=1))
    
    print(f"Added {len(calendar.events)} events")
    
    # Today
    print("\nToday's events:")
    for event in calendar.get_today():
        print(f"  {event.start.strftime('%H:%M')} - {event.title}")
    
    # Upcoming
    print("\nUpcoming events:")
    for event in calendar.get_upcoming(7):
        print(f"  {event.start.strftime('%a %d')} - {event.title}")
    
    # Free slot
    slot = calendar.find_free_slot(30)
    if slot:
        print(f"\nFree slot: {slot.strftime('%H:%M')}")
    
    # Cleanup
    if os.path.exists("./test_calendar.json"):
        os.remove("./test_calendar.json")
    
    print("\nCalendar test complete!")
