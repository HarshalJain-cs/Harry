"""
JARVIS Notes Manager - Quick notes and snippets.

Provides persistent note storage with search and organization.
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from pathlib import Path

from tools.registry import tool, ToolResult


@dataclass
class Note:
    """A note entry."""
    id: str
    title: str
    content: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    pinned: bool = False


class NotesManager:
    """
    Manage quick notes and snippets.
    
    Features:
    - Create/read/update/delete notes
    - Tag-based organization
    - Full-text search
    - Pinned notes
    """
    
    def __init__(self, storage_path: str = "./storage/notes.json"):
        """Initialize notes manager."""
        self.storage_path = storage_path
        self.notes: Dict[str, Note] = {}
        self._load()
    
    def _load(self):
        """Load notes from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                for item in data:
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                    item['updated_at'] = datetime.fromisoformat(item['updated_at'])
                    note = Note(**item)
                    self.notes[note.id] = note
            except Exception:
                pass
    
    def _save(self):
        """Save notes to storage."""
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = []
        for n in self.notes.values():
            item = asdict(n)
            item['created_at'] = n.created_at.isoformat()
            item['updated_at'] = n.updated_at.isoformat()
            data.append(item)
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create(
        self,
        content: str,
        title: Optional[str] = None,
        tags: List[str] = None,
    ) -> Note:
        """Create a new note."""
        note_id = f"note_{datetime.now().timestamp()}"
        now = datetime.now()
        
        # Auto-generate title from first line if not provided
        if not title:
            first_line = content.split('\n')[0][:50]
            title = first_line if first_line else "Untitled"
        
        note = Note(
            id=note_id,
            title=title,
            content=content,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )
        
        self.notes[note_id] = note
        self._save()
        
        return note
    
    def get(self, note_id: str) -> Optional[Note]:
        """Get note by ID."""
        return self.notes.get(note_id)
    
    def update(
        self,
        note_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Note]:
        """Update an existing note."""
        note = self.notes.get(note_id)
        if not note:
            return None
        
        if content is not None:
            note.content = content
        if title is not None:
            note.title = title
        if tags is not None:
            note.tags = tags
        
        note.updated_at = datetime.now()
        self._save()
        
        return note
    
    def delete(self, note_id: str) -> bool:
        """Delete a note."""
        if note_id in self.notes:
            del self.notes[note_id]
            self._save()
            return True
        return False
    
    def search(self, query: str) -> List[Note]:
        """Search notes by content or title."""
        query_lower = query.lower()
        results = []
        
        for note in self.notes.values():
            if (query_lower in note.title.lower() or
                query_lower in note.content.lower()):
                results.append(note)
        
        return sorted(results, key=lambda x: x.updated_at, reverse=True)
    
    def list_by_tag(self, tag: str) -> List[Note]:
        """List notes with a specific tag."""
        tag_lower = tag.lower()
        return [
            n for n in self.notes.values()
            if tag_lower in [t.lower() for t in n.tags]
        ]
    
    def list_recent(self, limit: int = 10) -> List[Note]:
        """List recent notes."""
        return sorted(
            self.notes.values(),
            key=lambda x: x.updated_at,
            reverse=True,
        )[:limit]
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags."""
        tags = set()
        for note in self.notes.values():
            tags.update(note.tags)
        return sorted(list(tags))
    
    def pin(self, note_id: str) -> bool:
        """Pin a note."""
        note = self.notes.get(note_id)
        if note:
            note.pinned = True
            self._save()
            return True
        return False
    
    def unpin(self, note_id: str) -> bool:
        """Unpin a note."""
        note = self.notes.get(note_id)
        if note:
            note.pinned = False
            self._save()
            return True
        return False
    
    def list_pinned(self) -> List[Note]:
        """List pinned notes."""
        return [n for n in self.notes.values() if n.pinned]


# Tool registrations
@tool(
    name="create_note",
    description="Create a quick note",
    category="productivity",
    examples=["note: buy groceries", "save note meeting at 3pm with team"],
)
def create_note(content: str, title: Optional[str] = None, tags: Optional[str] = None) -> ToolResult:
    """Create a note."""
    try:
        manager = NotesManager()
        
        tag_list = []
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
        
        note = manager.create(content, title, tag_list)
        
        return ToolResult(
            success=True,
            output={
                "id": note.id,
                "title": note.title,
                "preview": note.content[:100],
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_notes",
    description="Search through notes",
    category="productivity",
)
def search_notes(query: str) -> ToolResult:
    """Search notes."""
    try:
        manager = NotesManager()
        results = manager.search(query)
        
        notes = [
            {
                "id": n.id,
                "title": n.title,
                "preview": n.content[:50],
                "updated": n.updated_at.strftime("%Y-%m-%d"),
            }
            for n in results[:10]
        ]
        
        return ToolResult(success=True, output=notes)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="list_notes",
    description="List recent notes",
    category="productivity",
)
def list_notes(limit: int = 10) -> ToolResult:
    """List recent notes."""
    try:
        manager = NotesManager()
        recent = manager.list_recent(limit)
        
        notes = [
            {
                "id": n.id,
                "title": n.title,
                "tags": n.tags,
                "updated": n.updated_at.strftime("%Y-%m-%d"),
            }
            for n in recent
        ]
        
        return ToolResult(success=True, output=notes)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_note",
    description="Get full content of a note",
    category="productivity",
)
def get_note(note_id: str) -> ToolResult:
    """Get note content."""
    try:
        manager = NotesManager()
        note = manager.get(note_id)
        
        if not note:
            return ToolResult(success=False, error="Note not found")
        
        return ToolResult(
            success=True,
            output={
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "tags": note.tags,
                "created": note.created_at.strftime("%Y-%m-%d %H:%M"),
                "updated": note.updated_at.strftime("%Y-%m-%d %H:%M"),
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="delete_note",
    description="Delete a note",
    category="productivity",
)
def delete_note(note_id: str) -> ToolResult:
    """Delete note."""
    try:
        manager = NotesManager()
        success = manager.delete(note_id)
        
        if success:
            return ToolResult(success=True, output="Note deleted")
        else:
            return ToolResult(success=False, error="Note not found")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Notes Manager...")
    
    manager = NotesManager(storage_path="./test_notes.json")
    
    # Create note
    note = manager.create("Buy milk and eggs", "Shopping List", ["shopping"])
    print(f"Created: {note.title}")
    
    # Search
    results = manager.search("milk")
    print(f"Search results: {len(results)}")
    
    # List recent
    recent = manager.list_recent(5)
    print(f"Recent notes: {len(recent)}")
    
    # Cleanup
    os.remove("./test_notes.json")
    print("\nTests complete!")
