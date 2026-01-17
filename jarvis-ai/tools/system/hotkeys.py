"""
JARVIS Hotkey Manager - Global keyboard shortcuts
=================================================

Provides global hotkey registration and handling using pynput.
"""

import json
import threading
from pathlib import Path
from typing import Callable, Dict, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


class HotkeyAction(Enum):
    """Built-in hotkey actions."""
    ACTIVATE = "activate"
    DICTATION = "dictation"
    SCREENSHOT = "screenshot_analyze"
    CLIPBOARD_HISTORY = "clipboard_history"
    COMMAND_PALETTE = "command_palette"
    FOCUS_MODE = "focus_mode"
    QUICK_NOTE = "quick_note"


@dataclass
class Hotkey:
    """Hotkey definition."""
    combo: str  # e.g., "ctrl+alt+j"
    action: str
    callback: Optional[Callable] = None
    description: str = ""
    enabled: bool = True


class HotkeyManager:
    """
    Global hotkey manager.
    
    Registers and handles global keyboard shortcuts.
    
    Usage:
        manager = HotkeyManager()
        manager.register("ctrl+alt+j", "activate", callback)
        manager.start()
    """
    
    # Key mappings for normalization
    KEY_ALIASES = {
        'ctrl': 'ctrl',
        'control': 'ctrl',
        'alt': 'alt',
        'option': 'alt',
        'shift': 'shift',
        'cmd': 'cmd',
        'win': 'cmd',
        'super': 'cmd',
        'meta': 'cmd',
    }
    
    # SPECIAL_KEYS is set dynamically in __init__ when pynput is available
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize hotkey manager.
        
        Args:
            config_path: Path to hotkey configuration file
        """
        if not PYNPUT_AVAILABLE:
            raise ImportError(
                "pynput not installed. Run: pip install pynput"
            )
        
        self.hotkeys: Dict[str, Hotkey] = {}
        self.config_path = Path(config_path) if config_path else None
        
        # Current key state
        self._pressed_keys: Set = set()
        self._listener: Optional[keyboard.Listener] = None
        self._running = False
        
        # Callbacks for actions
        self._action_callbacks: Dict[str, Callable] = {}
        
        # Load config if provided
        if self.config_path and self.config_path.exists():
            self._load_config()
    
    def register(
        self,
        combo: str,
        action: str,
        callback: Optional[Callable] = None,
        description: str = ""
    ) -> bool:
        """
        Register a hotkey.
        
        Args:
            combo: Key combination (e.g., "ctrl+alt+j")
            action: Action identifier
            callback: Optional callback function
            description: Human-readable description
            
        Returns:
            True if registered successfully
        """
        combo = self._normalize_combo(combo)
        
        hotkey = Hotkey(
            combo=combo,
            action=action,
            callback=callback,
            description=description or action,
            enabled=True
        )
        
        self.hotkeys[combo] = hotkey
        
        if callback:
            self._action_callbacks[action] = callback
        
        return True
    
    def unregister(self, combo: str) -> bool:
        """
        Unregister a hotkey.
        
        Args:
            combo: Key combination to unregister
            
        Returns:
            True if unregistered
        """
        combo = self._normalize_combo(combo)
        
        if combo in self.hotkeys:
            del self.hotkeys[combo]
            return True
        
        return False
    
    def set_callback(self, action: str, callback: Callable):
        """Set callback for an action."""
        self._action_callbacks[action] = callback
        
        # Update any hotkeys with this action
        for hotkey in self.hotkeys.values():
            if hotkey.action == action:
                hotkey.callback = callback
    
    def list_hotkeys(self) -> Dict[str, Dict[str, Any]]:
        """List all registered hotkeys."""
        return {
            combo: {
                "action": hk.action,
                "description": hk.description,
                "enabled": hk.enabled
            }
            for combo, hk in self.hotkeys.items()
        }
    
    def enable(self, combo: str) -> bool:
        """Enable a hotkey."""
        combo = self._normalize_combo(combo)
        if combo in self.hotkeys:
            self.hotkeys[combo].enabled = True
            return True
        return False
    
    def disable(self, combo: str) -> bool:
        """Disable a hotkey."""
        combo = self._normalize_combo(combo)
        if combo in self.hotkeys:
            self.hotkeys[combo].enabled = False
            return True
        return False
    
    def start(self):
        """Start listening for hotkeys."""
        if self._running:
            return
        
        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()
    
    def stop(self):
        """Stop listening for hotkeys."""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()
    
    def _on_press(self, key):
        """Handle key press."""
        self._pressed_keys.add(self._key_to_string(key))
        self._check_hotkeys()
    
    def _on_release(self, key):
        """Handle key release."""
        key_str = self._key_to_string(key)
        self._pressed_keys.discard(key_str)
    
    def _check_hotkeys(self):
        """Check if any hotkey matches current pressed keys."""
        current_combo = '+'.join(sorted(self._pressed_keys))
        
        for combo, hotkey in self.hotkeys.items():
            if not hotkey.enabled:
                continue
            
            # Check if combo matches
            combo_parts = set(combo.split('+'))
            if combo_parts == self._pressed_keys:
                self._trigger_hotkey(hotkey)
                break
    
    def _trigger_hotkey(self, hotkey: Hotkey):
        """Trigger a hotkey action."""
        callback = hotkey.callback or self._action_callbacks.get(hotkey.action)
        
        if callback:
            # Run callback in separate thread to avoid blocking
            thread = threading.Thread(target=callback, daemon=True)
            thread.start()
    
    def _key_to_string(self, key) -> str:
        """Convert pynput key to string."""
        if isinstance(key, Key):
            key_name = key.name
            # Normalize modifier keys
            if 'ctrl' in key_name:
                return 'ctrl'
            if 'alt' in key_name:
                return 'alt'
            if 'shift' in key_name:
                return 'shift'
            if 'cmd' in key_name or 'super' in key_name:
                return 'cmd'
            return key_name
        elif isinstance(key, KeyCode):
            if key.char:
                return key.char.lower()
            return str(key.vk) if key.vk else ''
        return ''
    
    def _normalize_combo(self, combo: str) -> str:
        """Normalize key combination string."""
        parts = combo.lower().replace(' ', '').split('+')
        normalized = []
        
        for part in parts:
            # Apply aliases
            part = self.KEY_ALIASES.get(part, part)
            normalized.append(part)
        
        # Sort for consistent comparison
        return '+'.join(sorted(normalized))
    
    def _load_config(self):
        """Load hotkey configuration from file."""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
            
            for action, combo in config.items():
                if action != 'custom' and isinstance(combo, str):
                    self.register(combo, action)
                elif action == 'custom' and isinstance(combo, dict):
                    for custom_action, custom_combo in combo.items():
                        self.register(custom_combo, custom_action)
        except Exception:
            pass
    
    def save_config(self):
        """Save current hotkey configuration."""
        if not self.config_path:
            return
        
        config = {}
        for combo, hotkey in self.hotkeys.items():
            config[hotkey.action] = combo
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)


# Default configuration
DEFAULT_HOTKEYS = {
    "activate": "ctrl+alt+j",
    "dictation": "ctrl+alt+d",
    "screenshot_analyze": "ctrl+alt+s",
    "clipboard_history": "ctrl+alt+c",
    "command_palette": "ctrl+alt+q",
    "focus_mode": "ctrl+alt+f"
}


# Singleton instance
_hotkey_manager: Optional[HotkeyManager] = None


def get_hotkey_manager(config_path: Optional[str] = None) -> HotkeyManager:
    """Get or create global hotkey manager."""
    global _hotkey_manager
    if _hotkey_manager is None:
        _hotkey_manager = HotkeyManager(config_path)
    return _hotkey_manager


def register_default_hotkeys(callbacks: Dict[str, Callable]):
    """Register default hotkeys with provided callbacks."""
    manager = get_hotkey_manager()
    
    for action, combo in DEFAULT_HOTKEYS.items():
        callback = callbacks.get(action)
        manager.register(combo, action, callback)
    
    return manager
