"""
JARVIS Tool Registry - Plugin system for executable actions.

Provides a decorator-based system for registering tools with metadata
about risk levels, reversibility, and confirmation requirements.
"""

import subprocess
import webbrowser
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps


class RiskLevel(Enum):
    """Risk levels for tools."""
    LOW = "low"        # Read-only, reversible
    MEDIUM = "medium"  # Some side effects, mostly reversible  
    HIGH = "high"      # Destructive, hard to reverse


@dataclass
class Tool:
    """Tool definition with metadata."""
    name: str
    description: str
    handler: Callable
    risk_level: RiskLevel = RiskLevel.LOW
    reversible: bool = True
    requires_confirmation: bool = False
    category: str = "general"
    examples: List[str] = field(default_factory=list)


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    can_undo: bool = False
    undo_data: Optional[Dict] = None


class ToolRegistry:
    """
    Registry of executable tools/actions.
    
    Tools are registered with metadata and can be executed by name.
    Supports undo tracking for reversible operations.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.undo_stack: List[Dict] = []
        self.max_undo_history = 50
    
    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[Tool]:
        """List all registered tools, optionally filtered by category."""
        tools = list(self.tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools
    
    def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        track_undo: bool = True,
    ) -> ToolResult:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool
            track_undo: Whether to track for undo
            
        Returns:
            ToolResult with success status and output
        """
        tool = self.tools.get(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
        
        try:
            # Execute the tool handler
            result = tool.handler(**params)
            
            # Wrap result if not already ToolResult
            if not isinstance(result, ToolResult):
                result = ToolResult(success=True, output=result)
            
            # Track for undo if applicable
            if track_undo and tool.reversible and result.success:
                self._track_undo(tool_name, params, result)
            
            return result
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
            )
    
    def _track_undo(self, tool_name: str, params: Dict, result: ToolResult):
        """Track action for potential undo."""
        if result.undo_data:
            self.undo_stack.append({
                "tool": tool_name,
                "params": params,
                "undo_data": result.undo_data,
            })
            
            # Limit undo history
            if len(self.undo_stack) > self.max_undo_history:
                self.undo_stack.pop(0)
    
    def undo_last(self) -> ToolResult:
        """Undo the last reversible action."""
        if not self.undo_stack:
            return ToolResult(
                success=False,
                error="Nothing to undo",
            )
        
        action = self.undo_stack.pop()
        # Execute undo based on tool type
        # This would be implemented per-tool
        return ToolResult(
            success=True,
            output=f"Undid: {action['tool']}",
        )


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get or create global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def tool(
    name: str,
    description: str = "",
    risk_level: RiskLevel = RiskLevel.LOW,
    reversible: bool = True,
    category: str = "general",
    examples: Optional[List[str]] = None,
):
    """
    Decorator to register a function as a tool.
    
    Usage:
        @tool("open_app", "Open an application", category="system")
        def open_app(app: str) -> ToolResult:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Create and register tool
        t = Tool(
            name=name,
            description=description or func.__doc__ or "",
            handler=wrapper,
            risk_level=risk_level,
            reversible=reversible,
            category=category,
            examples=examples or [],
        )
        get_registry().register(t)
        
        return wrapper
    
    return decorator


# ===== Built-in Tools =====

@tool(
    name="open_app",
    description="Open an application by name",
    category="system",
    examples=["open chrome", "open notepad"],
)
def open_app(app: str) -> ToolResult:
    """Open an application."""
    try:
        # Handle special cases
        if app.startswith("ms-settings:"):
            subprocess.Popen(["start", app], shell=True)
        else:
            subprocess.Popen(app, shell=True)
        
        return ToolResult(
            success=True,
            output=f"Opened {app}",
            can_undo=False,
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="web_search",
    description="Search the web using default browser",
    category="web",
    examples=["search python tutorials", "google machine learning"],
)
def web_search(query: str, engine: str = "google") -> ToolResult:
    """Perform a web search."""
    try:
        engines = {
            "google": f"https://www.google.com/search?q={query}",
            "bing": f"https://www.bing.com/search?q={query}",
            "duckduckgo": f"https://duckduckgo.com/?q={query}",
        }
        url = engines.get(engine, engines["google"])
        webbrowser.open(url)
        
        return ToolResult(
            success=True,
            output=f"Searching for: {query}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="open_url",
    description="Open a URL in the default browser",
    category="web",
    examples=["open youtube.com", "go to github.com"],
)
def open_url(url: str) -> ToolResult:
    """Open a URL."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        
        return ToolResult(
            success=True,
            output=f"Opened {url}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="type_text",
    description="Type text at the current cursor position",
    category="input",
    examples=["type hello world", "type my email address"],
)
def type_text(text: str, interval: float = 0.02) -> ToolResult:
    """Type text using keyboard simulation."""
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=interval)
        
        return ToolResult(
            success=True,
            output=f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="press_key",
    description="Press a keyboard key or shortcut",
    category="input",
    examples=["press enter", "press ctrl+c"],
)
def press_key(key: str) -> ToolResult:
    """Press a keyboard key or combination."""
    try:
        import pyautogui
        
        # Handle key combinations
        if "+" in key:
            keys = [k.strip() for k in key.split("+")]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key)
        
        return ToolResult(
            success=True,
            output=f"Pressed: {key}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_clipboard",
    description="Get current clipboard contents",
    category="clipboard",
)
def get_clipboard() -> ToolResult:
    """Get clipboard contents."""
    try:
        import pyperclip
        content = pyperclip.paste()
        
        return ToolResult(
            success=True,
            output=content,
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="set_clipboard",
    description="Set clipboard contents",
    category="clipboard",
    reversible=True,
)
def set_clipboard(text: str) -> ToolResult:
    """Set clipboard contents."""
    try:
        import pyperclip
        
        # Save old content for undo
        old_content = pyperclip.paste()
        pyperclip.copy(text)
        
        return ToolResult(
            success=True,
            output=f"Copied to clipboard",
            can_undo=True,
            undo_data={"old_content": old_content},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    # Test tool registry
    print("Testing Tool Registry...")
    
    registry = get_registry()
    
    print(f"\nRegistered tools: {len(registry.tools)}")
    for name, tool in registry.tools.items():
        print(f"  - {name}: {tool.description}")
    
    print("\nExecuting 'open_app' with notepad...")
    result = registry.execute("open_app", {"app": "notepad"})
    print(f"Result: {result}")
    
    print("\nExecuting 'web_search'...")
    result = registry.execute("web_search", {"query": "JARVIS AI assistant"})
    print(f"Result: {result}")
