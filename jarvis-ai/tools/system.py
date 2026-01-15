"""
JARVIS System Tools - Operating system control and automation.

Provides tools for application management, window control, and system operations.
"""

import subprocess
import os
from typing import Optional, List, Dict
import psutil

from tools.registry import tool, ToolResult, RiskLevel, get_registry


@tool(
    name="close_app",
    description="Close an application by name or the active window",
    risk_level=RiskLevel.MEDIUM,
    category="system",
    examples=["close notepad", "close this window"],
)
def close_app(target: str = "active_window") -> ToolResult:
    """Close an application or window."""
    try:
        if target == "active_window":
            # Close active window using Alt+F4
            import pyautogui
            pyautogui.hotkey("alt", "F4")
            return ToolResult(success=True, output="Closed active window")
        
        # Find and kill process by name
        killed = False
        for proc in psutil.process_iter(['name']):
            if target.lower() in proc.info['name'].lower():
                proc.terminate()
                killed = True
        
        if killed:
            return ToolResult(success=True, output=f"Closed {target}")
        else:
            return ToolResult(success=False, error=f"Process {target} not found")
    
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="minimize_window",
    description="Minimize the active window",
    category="system",
)
def minimize_window() -> ToolResult:
    """Minimize active window."""
    try:
        import pyautogui
        pyautogui.hotkey("win", "down")
        return ToolResult(success=True, output="Minimized window")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="maximize_window",
    description="Maximize the active window",
    category="system",
)
def maximize_window() -> ToolResult:
    """Maximize active window."""
    try:
        import pyautogui
        pyautogui.hotkey("win", "up")
        return ToolResult(success=True, output="Maximized window")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="switch_window",
    description="Switch to another window using Alt+Tab",
    category="system",
)
def switch_window(times: int = 1) -> ToolResult:
    """Switch windows."""
    try:
        import pyautogui
        for _ in range(times):
            pyautogui.hotkey("alt", "tab")
        return ToolResult(success=True, output=f"Switched window {times}x")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_system_info",
    description="Get system information (CPU, memory, disk)",
    category="system",
)
def get_system_info() -> ToolResult:
    """Get system resource information."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        info = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
        }
        
        return ToolResult(success=True, output=info)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="list_running_apps",
    description="List all running applications",
    category="system",
)
def list_running_apps() -> ToolResult:
    """List running applications."""
    try:
        apps = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                info = proc.info
                if info['memory_percent'] and info['memory_percent'] > 0.1:
                    apps.append({
                        "name": info['name'],
                        "pid": info['pid'],
                        "memory": round(info['memory_percent'], 2),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by memory usage
        apps.sort(key=lambda x: x['memory'], reverse=True)
        
        return ToolResult(success=True, output=apps[:20])  # Top 20
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="run_command",
    description="Run a shell command",
    risk_level=RiskLevel.HIGH,
    category="system",
    examples=["run dir", "run python --version"],
)
def run_command(command: str, timeout: int = 30) -> ToolResult:
    """Execute a shell command."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        output = result.stdout or result.stderr
        return ToolResult(
            success=result.returncode == 0,
            output=output.strip() if output else "Command completed",
            error=result.stderr if result.returncode != 0 else None,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error=f"Command timed out after {timeout}s")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="screenshot",
    description="Take a screenshot",
    category="system",
)
def screenshot(save_path: Optional[str] = None) -> ToolResult:
    """Take a screenshot."""
    try:
        import mss
        from datetime import datetime
        
        if not save_path:
            save_path = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        with mss.mss() as sct:
            sct.shot(output=save_path)
        
        return ToolResult(
            success=True,
            output=f"Screenshot saved to: {save_path}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="lock_screen",
    description="Lock the computer screen",
    category="system",
)
def lock_screen() -> ToolResult:
    """Lock the screen."""
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return ToolResult(success=True, output="Screen locked")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="set_volume",
    description="Set system volume (0-100)",
    category="system",
)
def set_volume(level: int) -> ToolResult:
    """Set system volume."""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None
        )
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # Convert 0-100 to 0.0-1.0
        volume.SetMasterVolumeLevelScalar(level / 100, None)
        
        return ToolResult(success=True, output=f"Volume set to {level}%")
    except ImportError:
        return ToolResult(success=False, error="pycaw not installed for volume control")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def register_system_tools():
    """Ensure all system tools are registered."""
    # Tools are auto-registered via decorators
    # This function exists for explicit registration if needed
    pass


if __name__ == "__main__":
    print("Testing System Tools...")
    
    registry = get_registry()
    
    # Test get_system_info
    print("\nSystem Info:")
    result = registry.execute("get_system_info", {})
    if result.success:
        for key, value in result.output.items():
            print(f"  {key}: {value}")
    
    # Test list_running_apps
    print("\nTop Running Apps:")
    result = registry.execute("list_running_apps", {})
    if result.success:
        for app in result.output[:5]:
            print(f"  {app['name']}: {app['memory']}% memory")
