"""
JARVIS Tools for Wakey Integration - Productivity tools powered by Wakey.

Provides voice/text commands for:
- Task management
- Notes
- Calendar
- Reminders
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

from tools.registry import tool, ToolResult, RiskLevel
from integrations.wakey import get_wakey_client, run_async


# ===== Task Tools =====

@tool(
    name="wakey_list_tasks",
    description="List your tasks from Wakey productivity app",
    category="productivity",
    examples=["show my tasks", "what do I need to do", "list todos", "pending tasks"],
)
def wakey_list_tasks(include_completed: bool = False) -> ToolResult:
    """
    Get tasks from Wakey.
    
    Args:
        include_completed: Whether to include completed tasks
        
    Returns:
        ToolResult with task list
    """
    try:
        client = get_wakey_client()
        tasks = run_async(client.get_tasks(filter_completed=not include_completed))

        if not tasks:
            return ToolResult(success=True, output="No pending tasks! You're all caught up.")

        output = [f"You have {len(tasks)} task(s):"]
        for i, task in enumerate(tasks[:10], 1):  # Top 10
            status = "✓" if task.completed else "○"
            priority = "!" * task.priority if task.priority > 1 else ""
            due = f" (due: {task.due_date.strftime('%b %d')})" if task.due_date else ""
            output.append(f"  {i}. {status} {priority}{task.title}{due}")

        if len(tasks) > 10:
            output.append(f"  ... and {len(tasks) - 10} more")

        return ToolResult(success=True, output="\n".join(output))
    except Exception as e:
        return ToolResult(success=False, error=f"Could not get tasks: {e}")


@tool(
    name="wakey_add_task",
    description="Add a new task to Wakey",
    category="productivity",
    examples=["add task buy groceries", "remind me to call mom", "create todo finish report"],
)
def wakey_add_task(
    title: str,
    due_date: Optional[str] = None,
    priority: int = 1,
) -> ToolResult:
    """
    Create a task in Wakey.
    
    Args:
        title: Task title
        due_date: Optional due date (tomorrow, next week, or ISO date)
        priority: Priority 1-5 (1 is normal)
        
    Returns:
        ToolResult with created task
    """
    try:
        client = get_wakey_client()

        # Parse due date from natural language
        due = None
        if due_date:
            due_lower = due_date.lower()
            if "tomorrow" in due_lower:
                due = datetime.now() + timedelta(days=1)
            elif "next week" in due_lower:
                due = datetime.now() + timedelta(weeks=1)
            elif "today" in due_lower:
                due = datetime.now()
            elif "monday" in due_lower:
                days_ahead = 0 - datetime.now().weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                due = datetime.now() + timedelta(days=days_ahead)
            else:
                try:
                    due = datetime.fromisoformat(due_date)
                except:
                    pass

        task = run_async(client.create_task(
            title=title,
            due_date=due,
            priority=priority,
        ))

        if task:
            due_str = f" (due: {task.due_date.strftime('%b %d')})" if task.due_date else ""
            return ToolResult(
                success=True,
                output=f"Created task: {task.title}{due_str}"
            )
        return ToolResult(success=False, error="Failed to create task. Is Wakey running?")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="wakey_complete_task",
    description="Mark a task as completed in Wakey",
    category="productivity",
    examples=["complete task 1", "mark task done", "finish task buy groceries"],
)
def wakey_complete_task(task_id: str) -> ToolResult:
    """
    Complete a task.
    
    Args:
        task_id: ID or position of task to complete
        
    Returns:
        ToolResult
    """
    try:
        client = get_wakey_client()
        success = run_async(client.complete_task(task_id))

        if success:
            return ToolResult(success=True, output="Task marked as completed! ✓")
        return ToolResult(success=False, error="Could not complete task")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ===== Notes Tools =====

@tool(
    name="wakey_search_notes",
    description="Search your notes in Wakey",
    category="productivity",
    examples=["search notes for meeting", "find note about project", "look for notes on python"],
)
def wakey_search_notes(query: str) -> ToolResult:
    """
    Search notes in Wakey.
    
    Args:
        query: Search query
        
    Returns:
        ToolResult with matching notes
    """
    try:
        client = get_wakey_client()
        notes = run_async(client.search_notes(query))

        if not notes:
            return ToolResult(success=True, output=f"No notes found for '{query}'")

        output = [f"Found {len(notes)} note(s):"]
        for note in notes[:5]:
            preview = note.content[:80] + "..." if len(note.content) > 80 else note.content
            preview = preview.replace("\n", " ")
            output.append(f"  • {note.title}: {preview}")

        return ToolResult(success=True, output="\n".join(output))
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="wakey_create_note",
    description="Create a new note in Wakey",
    category="productivity",
    examples=["create note meeting summary", "save note about project ideas"],
)
def wakey_create_note(
    title: str,
    content: str,
    folder: str = None,
) -> ToolResult:
    """
    Create a note in Wakey.
    
    Args:
        title: Note title
        content: Note content
        folder: Optional folder name
        
    Returns:
        ToolResult with created note
    """
    try:
        client = get_wakey_client()
        note = run_async(client.create_note(title, content, folder))

        if note:
            folder_str = f" in {folder}" if folder else ""
            return ToolResult(
                success=True,
                output=f"Created note: '{note.title}'{folder_str}"
            )
        return ToolResult(success=False, error="Failed to create note")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="wakey_list_notes",
    description="List your recent notes from Wakey",
    category="productivity",
    examples=["show my notes", "list notes", "what notes do I have"],
)
def wakey_list_notes(folder: str = None, limit: int = 10) -> ToolResult:
    """
    List notes from Wakey.
    
    Args:
        folder: Optional folder to filter
        limit: Maximum notes to show
        
    Returns:
        ToolResult with note list
    """
    try:
        client = get_wakey_client()
        notes = run_async(client.get_notes(folder=folder, limit=limit))

        if not notes:
            folder_str = f" in {folder}" if folder else ""
            return ToolResult(success=True, output=f"No notes found{folder_str}")

        output = [f"Your notes ({len(notes)}):"]
        for note in notes:
            date_str = note.updated_at.strftime("%b %d")
            output.append(f"  • {note.title} ({date_str})")

        return ToolResult(success=True, output="\n".join(output))
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ===== Calendar Tools =====

@tool(
    name="wakey_get_schedule",
    description="Get your schedule from Wakey calendar",
    category="productivity",
    examples=["what's on my calendar", "show my schedule", "meetings today", "events this week"],
)
def wakey_get_schedule(days: int = 1) -> ToolResult:
    """
    Get upcoming events.
    
    Args:
        days: Number of days to look ahead
        
    Returns:
        ToolResult with event list
    """
    try:
        client = get_wakey_client()
        start = datetime.now()
        end = start + timedelta(days=days)

        events = run_async(client.get_events(start, end))

        if not events:
            day_str = "today" if days == 1 else f"the next {days} days"
            return ToolResult(success=True, output=f"No events scheduled for {day_str}")

        day_str = "Today" if days == 1 else f"Next {days} days"
        output = [f"{day_str}'s schedule ({len(events)} event(s)):"]
        
        for event in events:
            time_str = event.start_time.strftime("%I:%M %p")
            date_str = event.start_time.strftime("%a %b %d")
            loc = f" @ {event.location}" if event.location else ""
            output.append(f"  • {date_str} {time_str}: {event.title}{loc}")

        return ToolResult(success=True, output="\n".join(output))
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="wakey_add_event",
    description="Add an event to Wakey calendar",
    category="productivity",
    examples=["schedule meeting at 3pm", "add event lunch with john at noon"],
)
def wakey_add_event(
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    location: str = None,
) -> ToolResult:
    """
    Create a calendar event.
    
    Args:
        title: Event title
        start_time: Start time (ISO format or natural language)
        duration_minutes: Duration in minutes (default: 60)
        location: Optional location
        
    Returns:
        ToolResult with created event
    """
    try:
        client = get_wakey_client()

        # Parse start time
        try:
            start = datetime.fromisoformat(start_time)
        except:
            # Try to parse natural language (basic support)
            return ToolResult(
                success=False,
                error="Please provide time in ISO format (e.g., 2024-01-15T15:00:00)"
            )

        end = start + timedelta(minutes=duration_minutes)

        event = run_async(client.create_event(title, start, end, location))

        if event:
            time_str = event.start_time.strftime("%I:%M %p on %b %d")
            loc_str = f" at {location}" if location else ""
            return ToolResult(
                success=True,
                output=f"Created event: {event.title}{loc_str} ({time_str})"
            )
        return ToolResult(success=False, error="Failed to create event")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="wakey_set_reminder",
    description="Set a reminder in Wakey",
    category="productivity",
    examples=["remind me to drink water", "set reminder for 3pm to call mom"],
)
def wakey_set_reminder(
    message: str,
    remind_at: str = None,
    minutes_from_now: int = None,
) -> ToolResult:
    """
    Create a reminder.
    
    Args:
        message: Reminder message
        remind_at: When to remind (ISO format)
        minutes_from_now: Alternative: minutes from now
        
    Returns:
        ToolResult
    """
    try:
        client = get_wakey_client()

        # Determine reminder time
        if remind_at:
            try:
                remind_time = datetime.fromisoformat(remind_at)
            except:
                return ToolResult(
                    success=False,
                    error="Please provide time in ISO format"
                )
        elif minutes_from_now:
            remind_time = datetime.now() + timedelta(minutes=minutes_from_now)
        else:
            # Default to 1 hour from now
            remind_time = datetime.now() + timedelta(hours=1)

        success = run_async(client.create_reminder(message, remind_time))

        if success:
            time_str = remind_time.strftime("%I:%M %p")
            return ToolResult(
                success=True,
                output=f"Reminder set for {time_str}: {message}"
            )
        return ToolResult(success=False, error="Failed to set reminder")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def register_wakey_tools():
    """Register all Wakey tools. Called by tool registry on import."""
    # Tools are auto-registered via @tool decorator
    pass


if __name__ == "__main__":
    # Test Wakey tools
    print("Testing Wakey Tools...")
    
    # Test list tasks
    result = wakey_list_tasks()
    print(f"\nList tasks: {result.success}")
    print(result.output or result.error)
    
    print("\nWakey tools test complete!")
    print("Note: Full testing requires Wakey app running with local API enabled.")
