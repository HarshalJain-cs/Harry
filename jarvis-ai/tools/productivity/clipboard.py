"""
JARVIS Clipboard Manager - Enhanced clipboard with history.

Provides clipboard history, search, and smart paste features.
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from pathlib import Path
import threading

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

from tools.registry import tool, ToolResult


@dataclass
class ClipboardEntry:
    """A clipboard history entry."""
    id: str
    content: str
    content_type: str  # text, url, code, etc.
    source_app: Optional[str]
    timestamp: datetime
    pinned: bool = False


class ClipboardManager:
    """
    Enhanced clipboard with history and search.
    
    Features:
    - Clipboard history (last N items)
    - Content type detection
    - Search through history
    - Pinned items
    - Background monitoring
    """
    
    MAX_HISTORY = 100
    MAX_CONTENT_LENGTH = 100000  # 100KB per entry
    
    def __init__(
        self,
        storage_path: str = "./storage/clipboard.json",
        monitor: bool = False,
    ):
        """
        Initialize clipboard manager.
        
        Args:
            storage_path: Path to store history
            monitor: Whether to start background monitoring
        """
        self.storage_path = storage_path
        self.history: List[ClipboardEntry] = []
        self._load()
        
        self._monitoring = False
        self._monitor_thread = None
        self._last_content = ""
        
        if monitor:
            self.start_monitoring()
    
    def _load(self):
        """Load history from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                for item in data:
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    self.history.append(ClipboardEntry(**item))
            except Exception:
                pass
    
    def _save(self):
        """Save history to storage."""
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = []
        for entry in self.history:
            item = asdict(entry)
            item['timestamp'] = entry.timestamp.isoformat()
            data.append(item)
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _detect_content_type(self, content: str) -> str:
        """Detect content type from content."""
        content_lower = content.lower().strip()
        
        # URL detection
        if content_lower.startswith(('http://', 'https://', 'www.')):
            return 'url'
        
        # Email detection
        if '@' in content and '.' in content:
            import re
            if re.match(r'^[\w.-]+@[\w.-]+\.\w+$', content.strip()):
                return 'email'
        
        # Code detection (simple heuristics)
        code_indicators = [
            'def ', 'class ', 'import ', 'function ', 'const ',
            'let ', 'var ', '{', '}', '=>', '->'
        ]
        if any(ind in content for ind in code_indicators):
            return 'code'
        
        # File path detection
        if (content.startswith('/') or content.startswith('C:\\') or 
            content.startswith('~/')):
            return 'path'
        
        return 'text'
    
    def get_current(self) -> Optional[str]:
        """Get current clipboard content."""
        if not PYPERCLIP_AVAILABLE:
            return None
        
        try:
            return pyperclip.paste()
        except Exception:
            return None
    
    def set_current(self, content: str):
        """Set clipboard content."""
        if not PYPERCLIP_AVAILABLE:
            raise RuntimeError("pyperclip not available")
        
        pyperclip.copy(content)
        self._add_to_history(content)
    
    def _add_to_history(self, content: str, source_app: str = None):
        """Add content to history."""
        # Skip if same as last
        if self.history and self.history[0].content == content:
            return
        
        # Skip if too large
        if len(content) > self.MAX_CONTENT_LENGTH:
            return
        
        entry = ClipboardEntry(
            id=f"clip_{datetime.now().timestamp()}",
            content=content,
            content_type=self._detect_content_type(content),
            source_app=source_app,
            timestamp=datetime.now(),
        )
        
        self.history.insert(0, entry)
        
        # Trim history (keep pinned items)
        unpinned = [e for e in self.history if not e.pinned]
        pinned = [e for e in self.history if e.pinned]
        
        if len(unpinned) > self.MAX_HISTORY:
            unpinned = unpinned[:self.MAX_HISTORY]
        
        self.history = pinned + unpinned
        self._save()
    
    def get_history(self, limit: int = 20) -> List[ClipboardEntry]:
        """Get recent clipboard history."""
        return self.history[:limit]
    
    def search(self, query: str) -> List[ClipboardEntry]:
        """Search clipboard history."""
        query_lower = query.lower()
        return [
            e for e in self.history
            if query_lower in e.content.lower()
        ]
    
    def get_by_type(self, content_type: str) -> List[ClipboardEntry]:
        """Get history by content type."""
        return [e for e in self.history if e.content_type == content_type]
    
    def pin(self, entry_id: str) -> bool:
        """Pin a history entry."""
        for entry in self.history:
            if entry.id == entry_id:
                entry.pinned = True
                self._save()
                return True
        return False
    
    def delete(self, entry_id: str) -> bool:
        """Delete a history entry."""
        for i, entry in enumerate(self.history):
            if entry.id == entry_id:
                del self.history[i]
                self._save()
                return True
        return False
    
    def clear_history(self, keep_pinned: bool = True):
        """Clear clipboard history."""
        if keep_pinned:
            self.history = [e for e in self.history if e.pinned]
        else:
            self.history = []
        self._save()
    
    def start_monitoring(self, interval: float = 1.0):
        """Start background clipboard monitoring."""
        if self._monitoring or not PYPERCLIP_AVAILABLE:
            return
        
        self._monitoring = True
        self._last_content = self.get_current() or ""
        
        def monitor():
            while self._monitoring:
                try:
                    current = pyperclip.paste()
                    if current != self._last_content:
                        self._add_to_history(current)
                        self._last_content = current
                except Exception:
                    pass
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop clipboard monitoring."""
        self._monitoring = False


# Tool registrations
@tool(
    name="get_clipboard",
    description="Get current clipboard content",
    category="productivity",
)
def get_clipboard() -> ToolResult:
    """Get clipboard."""
    try:
        manager = ClipboardManager()
        content = manager.get_current()
        
        if content is None:
            return ToolResult(success=False, error="Could not access clipboard")
        
        return ToolResult(
            success=True,
            output={
                "content": content[:1000],
                "length": len(content),
                "type": manager._detect_content_type(content),
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="set_clipboard",
    description="Copy text to clipboard",
    category="productivity",
)
def set_clipboard(text: str) -> ToolResult:
    """Set clipboard."""
    try:
        manager = ClipboardManager()
        manager.set_current(text)
        
        return ToolResult(success=True, output="Copied to clipboard")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="clipboard_history",
    description="Show clipboard history",
    category="productivity",
)
def clipboard_history(limit: int = 10) -> ToolResult:
    """Show clipboard history."""
    try:
        manager = ClipboardManager()
        history = manager.get_history(limit)
        
        entries = [
            {
                "id": e.id,
                "preview": e.content[:50] + ("..." if len(e.content) > 50 else ""),
                "type": e.content_type,
                "time": e.timestamp.strftime("%H:%M"),
                "pinned": e.pinned,
            }
            for e in history
        ]
        
        return ToolResult(success=True, output=entries)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_clipboard",
    description="Search clipboard history",
    category="productivity",
)
def search_clipboard(query: str) -> ToolResult:
    """Search clipboard."""
    try:
        manager = ClipboardManager()
        results = manager.search(query)
        
        entries = [
            {
                "id": e.id,
                "preview": e.content[:100],
                "type": e.content_type,
            }
            for e in results[:10]
        ]
        
        return ToolResult(success=True, output=entries)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="paste_from_history",
    description="Paste a previous clipboard item",
    category="productivity",
)
def paste_from_history(entry_id: str) -> ToolResult:
    """Paste from history."""
    try:
        manager = ClipboardManager()
        
        for entry in manager.history:
            if entry.id == entry_id:
                manager.set_current(entry.content)
                return ToolResult(success=True, output="Set clipboard to historical item")
        
        return ToolResult(success=False, error="Entry not found")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Clipboard Manager...")
    
    if not PYPERCLIP_AVAILABLE:
        print("pyperclip not available")
    else:
        manager = ClipboardManager(storage_path="./test_clipboard.json")
        
        # Get current
        current = manager.get_current()
        print(f"Current clipboard: {current[:50] if current else 'empty'}...")
        
        # Set content
        manager.set_current("Test content from JARVIS")
        print("Set new content")
        
        # Get history
        history = manager.get_history(5)
        print(f"History: {len(history)} items")
        
        # Cleanup
        if os.path.exists("./test_clipboard.json"):
            os.remove("./test_clipboard.json")
    
    print("\nTests complete!")
