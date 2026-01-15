"""
JARVIS Media Control - Audio and media playback control.

Controls system audio, media players, and playback.
"""

import os
from typing import Optional, Dict, Any

try:
    import ctypes
    from ctypes import wintypes
    CTYPES_AVAILABLE = True
except ImportError:
    CTYPES_AVAILABLE = False

try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False


class MediaController:
    """
    System media and audio control.
    
    Features:
    - Volume control
    - Mute/unmute
    - Media playback (play/pause/next/prev)
    - Per-application volume
    """
    
    # Virtual key codes for media
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    VK_MEDIA_NEXT = 0xB0
    VK_MEDIA_PREV = 0xB1
    VK_MEDIA_STOP = 0xB2
    VK_MEDIA_PLAY_PAUSE = 0xB3
    
    def __init__(self):
        if os.name == 'nt' and CTYPES_AVAILABLE:
            self.user32 = ctypes.windll.user32
        else:
            self.user32 = None
    
    def _send_key(self, vk_code: int):
        """Send a virtual key press."""
        if not self.user32:
            return False
        
        # Key down
        self.user32.keybd_event(vk_code, 0, 0, 0)
        # Key up
        self.user32.keybd_event(vk_code, 0, 2, 0)
        return True
    
    def volume_up(self, steps: int = 1) -> bool:
        """Increase system volume."""
        for _ in range(steps):
            self._send_key(self.VK_VOLUME_UP)
        return True
    
    def volume_down(self, steps: int = 1) -> bool:
        """Decrease system volume."""
        for _ in range(steps):
            self._send_key(self.VK_VOLUME_DOWN)
        return True
    
    def mute(self) -> bool:
        """Toggle mute."""
        return self._send_key(self.VK_VOLUME_MUTE)
    
    def play_pause(self) -> bool:
        """Toggle play/pause."""
        return self._send_key(self.VK_MEDIA_PLAY_PAUSE)
    
    def next_track(self) -> bool:
        """Skip to next track."""
        return self._send_key(self.VK_MEDIA_NEXT)
    
    def previous_track(self) -> bool:
        """Go to previous track."""
        return self._send_key(self.VK_MEDIA_PREV)
    
    def stop(self) -> bool:
        """Stop playback."""
        return self._send_key(self.VK_MEDIA_STOP)
    
    def get_volume(self) -> Optional[int]:
        """Get current system volume (0-100)."""
        if not PYCAW_AVAILABLE:
            return None
        
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = interface.QueryInterface(IAudioEndpointVolume)
            
            current = volume.GetMasterVolumeLevelScalar()
            return int(current * 100)
        except Exception:
            return None
    
    def set_volume(self, level: int) -> bool:
        """Set system volume (0-100)."""
        if not PYCAW_AVAILABLE:
            return False
        
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = interface.QueryInterface(IAudioEndpointVolume)
            
            level = max(0, min(100, level))
            volume.SetMasterVolumeLevelScalar(level / 100, None)
            return True
        except Exception:
            return False
    
    def get_app_volume(self, app_name: str) -> Optional[int]:
        """Get volume for a specific application."""
        if not PYCAW_AVAILABLE:
            return None
        
        try:
            sessions = AudioUtilities.GetAllSessions()
            
            for session in sessions:
                if session.Process and app_name.lower() in session.Process.name().lower():
                    volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                    return int(volume.GetMasterVolume() * 100)
            return None
        except Exception:
            return None
    
    def set_app_volume(self, app_name: str, level: int) -> bool:
        """Set volume for a specific application."""
        if not PYCAW_AVAILABLE:
            return False
        
        try:
            sessions = AudioUtilities.GetAllSessions()
            
            for session in sessions:
                if session.Process and app_name.lower() in session.Process.name().lower():
                    volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                    level = max(0, min(100, level))
                    volume.SetMasterVolume(level / 100, None)
                    return True
            return False
        except Exception:
            return False
    
    def list_audio_apps(self) -> list:
        """List applications currently playing audio."""
        if not PYCAW_AVAILABLE:
            return []
        
        try:
            sessions = AudioUtilities.GetAllSessions()
            apps = []
            
            for session in sessions:
                if session.Process:
                    apps.append({
                        "name": session.Process.name(),
                        "pid": session.Process.pid,
                    })
            
            return apps
        except Exception:
            return []


from tools.registry import tool, ToolResult


@tool(
    name="volume",
    description="Control system volume",
    category="media",
    examples=["set volume to 50", "volume up", "mute"],
)
def volume_control(action: str, level: int = None) -> ToolResult:
    """Control volume."""
    try:
        controller = MediaController()
        
        if action == "up":
            controller.volume_up(2)
            return ToolResult(success=True, output="Volume increased")
        elif action == "down":
            controller.volume_down(2)
            return ToolResult(success=True, output="Volume decreased")
        elif action == "mute":
            controller.mute()
            return ToolResult(success=True, output="Toggled mute")
        elif action == "set" and level is not None:
            controller.set_volume(level)
            return ToolResult(success=True, output=f"Volume set to {level}%")
        elif action == "get":
            current = controller.get_volume()
            return ToolResult(success=True, output=f"Volume: {current}%")
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="media",
    description="Control media playback",
    category="media",
    examples=["play music", "next track", "pause"],
)
def media_control(action: str) -> ToolResult:
    """Control media."""
    try:
        controller = MediaController()
        
        actions = {
            "play": controller.play_pause,
            "pause": controller.play_pause,
            "toggle": controller.play_pause,
            "next": controller.next_track,
            "previous": controller.previous_track,
            "prev": controller.previous_track,
            "stop": controller.stop,
        }
        
        if action in actions:
            actions[action]()
            return ToolResult(success=True, output=f"Media: {action}")
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Media Controller...")
    
    controller = MediaController()
    
    # Test volume
    current = controller.get_volume()
    print(f"Current volume: {current}%")
    
    # Test media keys (commented to avoid actual media control)
    # controller.play_pause()
    
    # List audio apps
    apps = controller.list_audio_apps()
    print(f"Audio apps: {len(apps)}")
    for app in apps:
        print(f"  - {app['name']}")
    
    print("\nMedia controller test complete!")
