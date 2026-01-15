"""
JARVIS GUI Automation - Desktop GUI control.

Provides mouse and keyboard automation for desktop applications.
"""

import time
from typing import Optional, Tuple, List
from dataclasses import dataclass

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

from tools.registry import tool, ToolResult, RiskLevel


@dataclass
class MousePosition:
    """Mouse position."""
    x: int
    y: int


class GUIAutomation:
    """
    Automate GUI interactions.
    
    Features:
    - Mouse movement and clicks
    - Keyboard input
    - Screen coordinates
    - Image-based element finding
    """
    
    def __init__(self):
        if not PYAUTOGUI_AVAILABLE:
            raise RuntimeError("pyautogui not installed")
    
    # ===== Mouse Operations =====
    
    def get_mouse_position(self) -> MousePosition:
        """Get current mouse position."""
        x, y = pyautogui.position()
        return MousePosition(x=x, y=y)
    
    def move_mouse(self, x: int, y: int, duration: float = 0.2):
        """Move mouse to position."""
        pyautogui.moveTo(x, y, duration=duration)
    
    def move_mouse_relative(self, dx: int, dy: int, duration: float = 0.2):
        """Move mouse relative to current position."""
        pyautogui.moveRel(dx, dy, duration=duration)
    
    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
    ):
        """Click at position (or current position if not specified)."""
        if x is not None and y is not None:
            pyautogui.click(x, y, clicks=clicks, button=button)
        else:
            pyautogui.click(clicks=clicks, button=button)
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        """Double-click at position."""
        self.click(x, y, clicks=2)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        """Right-click at position."""
        self.click(x, y, button="right")
    
    def drag(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        duration: float = 0.5,
    ):
        """Drag from start to end position."""
        self.move_mouse(start[0], start[1])
        pyautogui.drag(
            end[0] - start[0],
            end[1] - start[1],
            duration=duration,
        )
    
    def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None):
        """Scroll at position (positive = up, negative = down)."""
        if x is not None and y is not None:
            pyautogui.scroll(amount, x, y)
        else:
            pyautogui.scroll(amount)
    
    # ===== Keyboard Operations =====
    
    def type_text(self, text: str, interval: float = 0.02):
        """Type text."""
        pyautogui.typewrite(text, interval=interval)
    
    def type_unicode(self, text: str):
        """Type text including unicode characters."""
        pyautogui.write(text)
    
    def press_key(self, key: str):
        """Press a single key."""
        pyautogui.press(key)
    
    def hotkey(self, *keys: str):
        """Press key combination."""
        pyautogui.hotkey(*keys)
    
    def hold_key(self, key: str, duration: float = 0.5):
        """Hold a key for duration."""
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)
    
    # ===== Screen Operations =====
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        return pyautogui.size()
    
    def locate_on_screen(
        self,
        image_path: str,
        confidence: float = 0.8,
    ) -> Optional[Tuple[int, int]]:
        """Find image on screen and return center coordinates."""
        try:
            location = pyautogui.locateCenterOnScreen(
                image_path,
                confidence=confidence,
            )
            return location
        except Exception:
            return None
    
    def click_image(
        self,
        image_path: str,
        confidence: float = 0.8,
    ) -> bool:
        """Find and click an image on screen."""
        location = self.locate_on_screen(image_path, confidence)
        if location:
            self.click(location[0], location[1])
            return True
        return False
    
    # ===== Utility Operations =====
    
    def alert(self, message: str, title: str = "JARVIS"):
        """Show an alert dialog."""
        pyautogui.alert(message, title)
    
    def confirm(self, message: str, title: str = "JARVIS") -> bool:
        """Show confirmation dialog."""
        result = pyautogui.confirm(message, title)
        return result == "OK"
    
    def prompt(self, message: str, title: str = "JARVIS") -> Optional[str]:
        """Show input prompt."""
        return pyautogui.prompt(message, title)


# Tool registrations
@tool(
    name="mouse_click",
    description="Click at a screen position",
    risk_level=RiskLevel.LOW,
    category="automation",
    examples=["click at 100,200", "click the button"],
)
def mouse_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    double: bool = False,
) -> ToolResult:
    """Click at position."""
    try:
        gui = GUIAutomation()
        
        if double:
            gui.double_click(x, y)
            action = "Double-clicked"
        else:
            gui.click(x, y, button=button)
            action = f"{button.capitalize()}-clicked"
        
        pos = gui.get_mouse_position()
        return ToolResult(
            success=True,
            output=f"{action} at ({pos.x}, {pos.y})",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="mouse_move",
    description="Move mouse to a position",
    category="automation",
)
def mouse_move(x: int, y: int) -> ToolResult:
    """Move mouse."""
    try:
        gui = GUIAutomation()
        gui.move_mouse(x, y)
        
        return ToolResult(success=True, output=f"Moved to ({x}, {y})")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="keyboard_type",
    description="Type text using keyboard",
    category="automation",
    examples=["type 'hello world'", "enter my email"],
)
def keyboard_type(text: str) -> ToolResult:
    """Type text."""
    try:
        gui = GUIAutomation()
        gui.type_unicode(text)
        
        preview = text[:30] + ("..." if len(text) > 30 else "")
        return ToolResult(success=True, output=f"Typed: {preview}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="keyboard_press",
    description="Press a key or key combination",
    category="automation",
    examples=["press enter", "press ctrl+c", "press alt+tab"],
)
def keyboard_press(keys: str) -> ToolResult:
    """Press key or combination."""
    try:
        gui = GUIAutomation()
        
        # Handle combinations (e.g., "ctrl+c")
        if "+" in keys:
            key_list = [k.strip() for k in keys.split("+")]
            gui.hotkey(*key_list)
        else:
            gui.press_key(keys)
        
        return ToolResult(success=True, output=f"Pressed: {keys}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="mouse_scroll",
    description="Scroll the mouse wheel",
    category="automation",
)
def mouse_scroll(amount: int, x: Optional[int] = None, y: Optional[int] = None) -> ToolResult:
    """Scroll mouse wheel."""
    try:
        gui = GUIAutomation()
        gui.scroll(amount, x, y)
        
        direction = "up" if amount > 0 else "down"
        return ToolResult(success=True, output=f"Scrolled {direction} by {abs(amount)}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_mouse_position",
    description="Get current mouse position",
    category="automation",
)
def get_mouse_position() -> ToolResult:
    """Get mouse position."""
    try:
        gui = GUIAutomation()
        pos = gui.get_mouse_position()
        
        return ToolResult(
            success=True,
            output={"x": pos.x, "y": pos.y},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="find_and_click",
    description="Find an image on screen and click it",
    category="automation",
)
def find_and_click(image_path: str, confidence: float = 0.8) -> ToolResult:
    """Find and click image."""
    try:
        import os
        if not os.path.exists(image_path):
            return ToolResult(success=False, error=f"Image not found: {image_path}")
        
        gui = GUIAutomation()
        
        if gui.click_image(image_path, confidence):
            return ToolResult(success=True, output="Found and clicked image")
        else:
            return ToolResult(success=False, error="Image not found on screen")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing GUI Automation...")
    
    if not PYAUTOGUI_AVAILABLE:
        print("pyautogui not available")
    else:
        gui = GUIAutomation()
        
        # Get mouse position
        pos = gui.get_mouse_position()
        print(f"Mouse position: ({pos.x}, {pos.y})")
        
        # Get screen size
        width, height = gui.get_screen_size()
        print(f"Screen size: {width}x{height}")
        
        print("\nGUI automation ready!")
    
    print("\nTests complete!")
