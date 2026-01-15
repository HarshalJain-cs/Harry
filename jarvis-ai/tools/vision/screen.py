"""
JARVIS Screen Intelligence - Screen capture and understanding.

Provides screen capture, window detection, and visual context awareness.
"""

import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
import numpy as np

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import win32gui
    import win32process
    import psutil
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from tools.registry import tool, ToolResult


@dataclass
class WindowInfo:
    """Information about a window."""
    hwnd: int
    title: str
    process_name: str
    rect: Tuple[int, int, int, int]  # left, top, right, bottom
    is_visible: bool


@dataclass
class ScreenRegion:
    """A region of the screen."""
    x: int
    y: int
    width: int
    height: int
    
    def to_bbox(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)


class ScreenCapture:
    """
    Capture screen content efficiently.
    
    Features:
    - Full screen capture
    - Region capture
    - Window capture
    - Multi-monitor support
    """
    
    def __init__(self):
        if not MSS_AVAILABLE:
            raise RuntimeError("mss not installed")
        self.sct = mss.mss()
    
    def get_monitors(self) -> List[Dict]:
        """Get all monitors."""
        return [
            {
                "id": i,
                "x": m["left"],
                "y": m["top"],
                "width": m["width"],
                "height": m["height"],
            }
            for i, m in enumerate(self.sct.monitors)
        ]
    
    def capture_full(self, monitor: int = 0) -> np.ndarray:
        """Capture full screen."""
        mon = self.sct.monitors[monitor]
        screenshot = self.sct.grab(mon)
        return np.array(screenshot)
    
    def capture_region(self, region: ScreenRegion) -> np.ndarray:
        """Capture a specific region."""
        screenshot = self.sct.grab({
            "left": region.x,
            "top": region.y,
            "width": region.width,
            "height": region.height,
        })
        return np.array(screenshot)
    
    def capture_window(self, hwnd: int) -> Optional[np.ndarray]:
        """Capture a specific window."""
        if not WIN32_AVAILABLE:
            return None
        
        try:
            rect = win32gui.GetWindowRect(hwnd)
            region = ScreenRegion(
                x=rect[0],
                y=rect[1],
                width=rect[2] - rect[0],
                height=rect[3] - rect[1],
            )
            return self.capture_region(region)
        except Exception:
            return None
    
    def save_screenshot(
        self,
        path: Optional[str] = None,
        monitor: int = 0,
    ) -> str:
        """Capture and save screenshot."""
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"screenshot_{timestamp}.png"
        
        screenshot = self.capture_full(monitor)
        
        if PIL_AVAILABLE:
            # Convert BGRA to RGB
            img = Image.fromarray(screenshot[:, :, :3][:, :, ::-1])
            img.save(path)
        else:
            # Use mss directly
            mon = self.sct.monitors[monitor]
            mss.tools.to_png(self.sct.grab(mon).rgb, mon["size"], output=path)
        
        return path


class ScreenIntelligence:
    """
    Understand screen content and context.
    
    Features:
    - Active window detection
    - Window enumeration
    - UI element detection
    - Color sampling
    """
    
    def __init__(self):
        self.capture = ScreenCapture() if MSS_AVAILABLE else None
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get the currently active window."""
        if not WIN32_AVAILABLE:
            return None
        
        try:
            hwnd = win32gui.GetForegroundWindow()
            return self._get_window_info(hwnd)
        except Exception:
            return None
    
    def _get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        """Get info for a window handle."""
        try:
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            
            # Get process name
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name()
            except:
                process_name = "unknown"
            
            is_visible = win32gui.IsWindowVisible(hwnd)
            
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                rect=rect,
                is_visible=is_visible,
            )
        except Exception:
            return None
    
    def list_windows(self, visible_only: bool = True) -> List[WindowInfo]:
        """List all windows."""
        if not WIN32_AVAILABLE:
            return []
        
        windows = []
        
        def enum_callback(hwnd, _):
            if visible_only and not win32gui.IsWindowVisible(hwnd):
                return
            
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            
            info = self._get_window_info(hwnd)
            if info:
                windows.append(info)
        
        win32gui.EnumWindows(enum_callback, None)
        return windows
    
    def find_window(self, title_contains: str) -> Optional[WindowInfo]:
        """Find a window by title."""
        windows = self.list_windows()
        title_lower = title_contains.lower()
        
        for win in windows:
            if title_lower in win.title.lower():
                return win
        
        return None
    
    def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """Get color at screen position."""
        if not self.capture:
            return (0, 0, 0)
        
        region = ScreenRegion(x=x, y=y, width=1, height=1)
        img = self.capture.capture_region(region)
        
        # Return RGB (mss captures as BGRA)
        return (img[0, 0, 2], img[0, 0, 1], img[0, 0, 0])
    
    def detect_ui_elements(
        self,
        image: Optional[np.ndarray] = None,
    ) -> List[Dict]:
        """
        Detect UI elements using edge detection.
        
        This is a basic implementation - for production use,
        consider using YOLO or specialized UI detection models.
        """
        if not CV2_AVAILABLE:
            return []
        
        if image is None:
            if not self.capture:
                return []
            image = self.capture.capture_full()
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        elements = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by size
            if w < 20 or h < 10 or w > 1000 or h > 500:
                continue
            
            area = cv2.contourArea(contour)
            if area < 200:
                continue
            
            elements.append({
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "area": area,
            })
        
        # Sort by position (top to bottom, left to right)
        elements.sort(key=lambda e: (e["y"], e["x"]))
        
        return elements[:50]  # Limit results


# Tool registrations
@tool(
    name="screenshot",
    description="Take a screenshot",
    category="vision",
    examples=["take screenshot", "capture screen"],
)
def take_screenshot(
    path: Optional[str] = None,
    monitor: int = 0,
) -> ToolResult:
    """Take a screenshot."""
    try:
        capture = ScreenCapture()
        saved_path = capture.save_screenshot(path, monitor)
        
        return ToolResult(
            success=True,
            output=f"Screenshot saved to: {saved_path}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_active_window",
    description="Get information about the active window",
    category="vision",
)
def get_active_window() -> ToolResult:
    """Get active window info."""
    try:
        intel = ScreenIntelligence()
        window = intel.get_active_window()
        
        if not window:
            return ToolResult(success=False, error="Could not get active window")
        
        return ToolResult(
            success=True,
            output={
                "title": window.title,
                "app": window.process_name,
                "position": window.rect[:2],
                "size": (window.rect[2] - window.rect[0], window.rect[3] - window.rect[1]),
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="list_windows",
    description="List all visible windows",
    category="vision",
)
def list_windows() -> ToolResult:
    """List all windows."""
    try:
        intel = ScreenIntelligence()
        windows = intel.list_windows(visible_only=True)
        
        result = [
            {
                "title": w.title[:50],
                "app": w.process_name,
            }
            for w in windows[:20]
        ]
        
        return ToolResult(success=True, output=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="find_window",
    description="Find a window by title",
    category="vision",
)
def find_window(title: str) -> ToolResult:
    """Find window by title."""
    try:
        intel = ScreenIntelligence()
        window = intel.find_window(title)
        
        if not window:
            return ToolResult(success=False, error=f"Window not found: {title}")
        
        return ToolResult(
            success=True,
            output={
                "title": window.title,
                "app": window.process_name,
                "hwnd": window.hwnd,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_monitors",
    description="Get information about connected monitors",
    category="vision",
)
def get_monitors() -> ToolResult:
    """Get monitor info."""
    try:
        capture = ScreenCapture()
        monitors = capture.get_monitors()
        
        return ToolResult(success=True, output=monitors)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Screen Intelligence...")
    
    if not MSS_AVAILABLE:
        print("mss not available")
    else:
        capture = ScreenCapture()
        
        # Get monitors
        monitors = capture.get_monitors()
        print(f"\nMonitors: {len(monitors)}")
        for m in monitors:
            print(f"  {m}")
        
        # Screenshot
        path = capture.save_screenshot("test_screenshot.png")
        print(f"\nScreenshot: {path}")
        
        if os.path.exists("test_screenshot.png"):
            os.remove("test_screenshot.png")
    
    if WIN32_AVAILABLE:
        intel = ScreenIntelligence()
        
        # Active window
        active = intel.get_active_window()
        if active:
            print(f"\nActive window: {active.title}")
            print(f"App: {active.process_name}")
        
        # List windows
        windows = intel.list_windows()
        print(f"\nVisible windows: {len(windows)}")
        for w in windows[:5]:
            print(f"  - {w.title[:40]} ({w.process_name})")
    
    print("\nTests complete!")
