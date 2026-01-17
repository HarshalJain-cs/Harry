"""
JARVIS Macro Recorder - Record and playback user actions
========================================================

Records keyboard and mouse actions for workflow automation.
"""

import json
import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Key, KeyCode
    from pynput.mouse import Button
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


class ActionType(Enum):
    """Types of recordable actions."""
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_SCROLL = "mouse_scroll"
    WAIT = "wait"
    CUSTOM = "custom"


@dataclass
class MacroAction:
    """Single recorded action."""
    action_type: str
    data: Dict[str, Any]
    timestamp: float = 0.0
    delay: float = 0.0  # Delay from previous action


@dataclass
class Macro:
    """Complete recorded macro."""
    name: str
    actions: List[MacroAction] = field(default_factory=list)
    created_at: str = ""
    description: str = ""
    total_duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "actions": [
                {
                    "action_type": a.action_type,
                    "data": a.data,
                    "delay": a.delay
                }
                for a in self.actions
            ],
            "created_at": self.created_at,
            "description": self.description,
            "total_duration": self.total_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Macro":
        """Create from dictionary."""
        actions = [
            MacroAction(
                action_type=a["action_type"],
                data=a["data"],
                delay=a.get("delay", 0)
            )
            for a in data.get("actions", [])
        ]
        return cls(
            name=data["name"],
            actions=actions,
            created_at=data.get("created_at", ""),
            description=data.get("description", ""),
            total_duration=data.get("total_duration", 0)
        )


class MacroRecorder:
    """
    Records user keyboard and mouse actions.
    
    Usage:
        recorder = MacroRecorder()
        recorder.start_recording()
        # ... user performs actions ...
        macro = recorder.stop_recording()
        recorder.save_macro("my_macro", macro)
    """
    
    def __init__(self, storage_path: str = "./data/macros"):
        """
        Initialize macro recorder.
        
        Args:
            storage_path: Directory to store macros
        """
        if not PYNPUT_AVAILABLE:
            raise ImportError("pynput not installed. Run: pip install pynput")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._recording = False
        self._current_actions: List[MacroAction] = []
        self._start_time: float = 0
        self._last_action_time: float = 0
        
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None
        
        # Recording options
        self.record_mouse_moves = False  # Can be noisy
        self.min_action_delay = 0.01  # Minimum delay to record
    
    def start_recording(self):
        """Start recording actions."""
        if self._recording:
            return
        
        self._recording = True
        self._current_actions = []
        self._start_time = time.time()
        self._last_action_time = self._start_time
        
        # Start keyboard listener
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._keyboard_listener.start()
        
        # Start mouse listener
        self._mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll,
            on_move=self._on_mouse_move if self.record_mouse_moves else None
        )
        self._mouse_listener.start()
    
    def stop_recording(self) -> Macro:
        """
        Stop recording and return macro.
        
        Returns:
            Recorded macro
        """
        if not self._recording:
            return Macro(name="empty", actions=[])
        
        self._recording = False
        
        # Stop listeners
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()
        
        # Create macro
        total_duration = time.time() - self._start_time
        macro = Macro(
            name="recorded_macro",
            actions=self._current_actions.copy(),
            created_at=datetime.now().isoformat(),
            total_duration=total_duration
        )
        
        self._current_actions = []
        
        return macro
    
    def save_macro(self, name: str, macro: Macro) -> bool:
        """
        Save macro to file.
        
        Args:
            name: Macro name
            macro: Macro to save
            
        Returns:
            True if saved
        """
        macro.name = name
        filepath = self.storage_path / f"{name}.json"
        
        try:
            with open(filepath, 'w') as f:
                json.dump(macro.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving macro: {e}")
            return False
    
    def load_macro(self, name: str) -> Optional[Macro]:
        """
        Load macro from file.
        
        Args:
            name: Macro name
            
        Returns:
            Loaded macro or None
        """
        filepath = self.storage_path / f"{name}.json"
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath) as f:
                data = json.load(f)
            return Macro.from_dict(data)
        except Exception as e:
            print(f"Error loading macro: {e}")
            return None
    
    def list_macros(self) -> List[str]:
        """List all saved macros."""
        return [
            f.stem for f in self.storage_path.glob("*.json")
        ]
    
    def delete_macro(self, name: str) -> bool:
        """Delete a macro."""
        filepath = self.storage_path / f"{name}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    def _record_action(self, action_type: str, data: Dict[str, Any]):
        """Record an action with timing."""
        current_time = time.time()
        delay = current_time - self._last_action_time
        
        # Skip very rapid actions
        if delay < self.min_action_delay:
            return
        
        action = MacroAction(
            action_type=action_type,
            data=data,
            timestamp=current_time - self._start_time,
            delay=delay
        )
        
        self._current_actions.append(action)
        self._last_action_time = current_time
    
    def _key_to_string(self, key) -> str:
        """Convert key to string representation."""
        if isinstance(key, Key):
            return f"Key.{key.name}"
        elif isinstance(key, KeyCode):
            if key.char:
                return key.char
            return f"KeyCode({key.vk})"
        return str(key)
    
    def _on_key_press(self, key):
        """Handle key press."""
        if not self._recording:
            return
        
        self._record_action(
            ActionType.KEY_PRESS.value,
            {"key": self._key_to_string(key)}
        )
    
    def _on_key_release(self, key):
        """Handle key release."""
        if not self._recording:
            return
        
        self._record_action(
            ActionType.KEY_RELEASE.value,
            {"key": self._key_to_string(key)}
        )
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click."""
        if not self._recording:
            return
        
        self._record_action(
            ActionType.MOUSE_CLICK.value,
            {
                "x": x,
                "y": y,
                "button": button.name,
                "pressed": pressed
            }
        )
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll."""
        if not self._recording:
            return
        
        self._record_action(
            ActionType.MOUSE_SCROLL.value,
            {"x": x, "y": y, "dx": dx, "dy": dy}
        )
    
    def _on_mouse_move(self, x, y):
        """Handle mouse move (optional)."""
        if not self._recording or not self.record_mouse_moves:
            return
        
        self._record_action(
            ActionType.MOUSE_MOVE.value,
            {"x": x, "y": y}
        )


class MacroPlayer:
    """
    Plays back recorded macros.
    
    Usage:
        player = MacroPlayer()
        player.play(macro)
    """
    
    def __init__(self):
        """Initialize macro player."""
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("pyautogui not installed. Run: pip install pyautogui")
        
        # Safety: enable fail-safe (move mouse to corner to abort)
        pyautogui.FAILSAFE = True
        
        self._playing = False
        self._paused = False
        self._stop_requested = False
    
    def play(
        self,
        macro: Macro,
        speed: float = 1.0,
        preserve_timing: bool = True
    ) -> bool:
        """
        Play a macro.
        
        Args:
            macro: Macro to play
            speed: Playback speed multiplier
            preserve_timing: Whether to preserve original timing
            
        Returns:
            True if completed successfully
        """
        if self._playing:
            return False
        
        self._playing = True
        self._paused = False
        self._stop_requested = False
        
        try:
            for action in macro.actions:
                if self._stop_requested:
                    break
                
                # Handle pause
                while self._paused and not self._stop_requested:
                    time.sleep(0.1)
                
                if self._stop_requested:
                    break
                
                # Wait for timing
                if preserve_timing and action.delay > 0:
                    time.sleep(action.delay / speed)
                
                # Execute action
                self._execute_action(action)
            
            return not self._stop_requested
            
        finally:
            self._playing = False
    
    def play_with_retry(
        self,
        macro: Macro,
        retries: int = 3,
        speed: float = 1.0
    ) -> bool:
        """
        Play macro with retry on failure.
        
        Args:
            macro: Macro to play
            retries: Maximum retry attempts
            speed: Playback speed
            
        Returns:
            True if successful
        """
        for attempt in range(retries):
            try:
                if self.play(macro, speed):
                    return True
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(1)
        
        return False
    
    def pause(self):
        """Pause playback."""
        self._paused = True
    
    def resume(self):
        """Resume playback."""
        self._paused = False
    
    def stop(self):
        """Stop playback."""
        self._stop_requested = True
        self._paused = False
    
    @property
    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._playing
    
    def _execute_action(self, action: MacroAction):
        """Execute a single action."""
        action_type = action.action_type
        data = action.data
        
        if action_type == ActionType.KEY_PRESS.value:
            key_str = data["key"]
            self._press_key(key_str)
        
        elif action_type == ActionType.KEY_RELEASE.value:
            # pyautogui handles press and release together
            pass
        
        elif action_type == ActionType.MOUSE_CLICK.value:
            x, y = data["x"], data["y"]
            button = data.get("button", "left")
            pressed = data.get("pressed", True)
            
            if pressed:
                pyautogui.click(x, y, button=button)
        
        elif action_type == ActionType.MOUSE_MOVE.value:
            x, y = data["x"], data["y"]
            pyautogui.moveTo(x, y)
        
        elif action_type == ActionType.MOUSE_SCROLL.value:
            dx, dy = data.get("dx", 0), data.get("dy", 0)
            pyautogui.scroll(dy)
        
        elif action_type == ActionType.WAIT.value:
            duration = data.get("duration", 0)
            time.sleep(duration)
    
    def _press_key(self, key_str: str):
        """Press a key from string representation."""
        if key_str.startswith("Key."):
            # Special key
            key_name = key_str[4:]
            key_map = {
                'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
                'alt_l': 'alt', 'alt_r': 'alt',
                'shift': 'shift', 'shift_l': 'shift', 'shift_r': 'shift',
                'enter': 'enter', 'return': 'enter',
                'space': 'space',
                'tab': 'tab',
                'esc': 'esc', 'escape': 'esc',
                'backspace': 'backspace',
                'delete': 'delete',
                'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
            }
            pyautogui.press(key_map.get(key_name, key_name))
        elif len(key_str) == 1:
            # Single character
            pyautogui.press(key_str)
        else:
            # Try as key name
            try:
                pyautogui.press(key_str)
            except Exception:
                pass


# Singleton instances
_recorder: Optional[MacroRecorder] = None
_player: Optional[MacroPlayer] = None


def get_macro_recorder() -> MacroRecorder:
    """Get or create global macro recorder."""
    global _recorder
    if _recorder is None:
        _recorder = MacroRecorder()
    return _recorder


def get_macro_player() -> MacroPlayer:
    """Get or create global macro player."""
    global _player
    if _player is None:
        _player = MacroPlayer()
    return _player
