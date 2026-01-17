"""
JARVIS Voice Shortcuts - Custom voice command triggers
======================================================

Allows registering short phrases that map to specific actions.
"""

import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Callable
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class VoiceShortcut:
    """Voice shortcut definition."""
    phrase: str
    action: str
    params: Dict[str, Any]
    aliases: List[str]
    enabled: bool = True


class VoiceShortcuts:
    """
    Voice command shortcut manager.
    
    Matches spoken phrases to registered shortcuts.
    
    Usage:
        shortcuts = VoiceShortcuts()
        shortcuts.register("open code", "open_app", {"app": "vscode"})
        match = shortcuts.match("hey open code please")
    """
    
    # Common filler words to ignore
    FILLER_WORDS = {
        'please', 'hey', 'jarvis', 'can', 'you', 'would',
        'could', 'just', 'now', 'the', 'a', 'an', 'my'
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize voice shortcuts.
        
        Args:
            config_path: Path to shortcuts configuration
        """
        self.shortcuts: Dict[str, VoiceShortcut] = {}
        self.config_path = Path(config_path) if config_path else None
        
        # Minimum similarity for fuzzy matching
        self.similarity_threshold = 0.7
        
        # Load config
        if self.config_path and self.config_path.exists():
            self._load_config()
        else:
            self._register_defaults()
    
    def register(
        self,
        phrase: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None
    ) -> bool:
        """
        Register a voice shortcut.
        
        Args:
            phrase: Trigger phrase
            action: Action/tool to execute
            params: Parameters for the action
            aliases: Alternative phrases
            
        Returns:
            True if registered
        """
        phrase = phrase.lower().strip()
        
        shortcut = VoiceShortcut(
            phrase=phrase,
            action=action,
            params=params or {},
            aliases=aliases or []
        )
        
        self.shortcuts[phrase] = shortcut
        
        # Also register aliases
        for alias in shortcut.aliases:
            alias = alias.lower().strip()
            self.shortcuts[alias] = shortcut
        
        return True
    
    def unregister(self, phrase: str) -> bool:
        """
        Unregister a voice shortcut.
        
        Args:
            phrase: Trigger phrase to remove
            
        Returns:
            True if removed
        """
        phrase = phrase.lower().strip()
        
        if phrase in self.shortcuts:
            # Also remove aliases
            shortcut = self.shortcuts[phrase]
            for alias in shortcut.aliases:
                self.shortcuts.pop(alias.lower(), None)
            del self.shortcuts[phrase]
            return True
        
        return False
    
    def match(
        self,
        text: str,
        fuzzy: bool = True
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Match spoken text against registered shortcuts.
        
        Args:
            text: Spoken text
            fuzzy: Allow fuzzy matching
            
        Returns:
            Tuple of (action, params) if matched, None otherwise
        """
        text = text.lower().strip()
        
        # Clean text
        cleaned = self._clean_text(text)
        
        # Try exact match first
        for phrase, shortcut in self.shortcuts.items():
            if not shortcut.enabled:
                continue
            
            # Exact match
            if phrase in cleaned or cleaned in phrase:
                return (shortcut.action, shortcut.params)
            
            # Check if phrase is contained in text
            if phrase in text:
                return (shortcut.action, shortcut.params)
        
        # Try fuzzy matching
        if fuzzy:
            best_match = None
            best_score = 0
            
            for phrase, shortcut in self.shortcuts.items():
                if not shortcut.enabled:
                    continue
                
                score = self._similarity(cleaned, phrase)
                
                if score > best_score and score >= self.similarity_threshold:
                    best_score = score
                    best_match = shortcut
            
            if best_match:
                return (best_match.action, best_match.params)
        
        return None
    
    def list_shortcuts(self) -> Dict[str, Dict[str, Any]]:
        """List all registered shortcuts."""
        seen = set()
        result = {}
        
        for phrase, shortcut in self.shortcuts.items():
            if shortcut.phrase in seen:
                continue
            seen.add(shortcut.phrase)
            
            result[shortcut.phrase] = {
                "action": shortcut.action,
                "params": shortcut.params,
                "aliases": shortcut.aliases,
                "enabled": shortcut.enabled
            }
        
        return result
    
    def enable(self, phrase: str) -> bool:
        """Enable a shortcut."""
        phrase = phrase.lower().strip()
        if phrase in self.shortcuts:
            self.shortcuts[phrase].enabled = True
            return True
        return False
    
    def disable(self, phrase: str) -> bool:
        """Disable a shortcut."""
        phrase = phrase.lower().strip()
        if phrase in self.shortcuts:
            self.shortcuts[phrase].enabled = False
            return True
        return False
    
    def _clean_text(self, text: str) -> str:
        """Remove filler words and clean text."""
        words = text.split()
        cleaned = [w for w in words if w not in self.FILLER_WORDS]
        return ' '.join(cleaned)
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, a, b).ratio()
    
    def _register_defaults(self):
        """Register default shortcuts."""
        defaults = [
            ("open code", "open_app", {"app": "vscode"}, ["open editor", "start vscode"]),
            ("open browser", "open_app", {"app": "chrome"}, ["start chrome", "open chrome"]),
            ("open terminal", "open_app", {"app": "terminal"}, ["start terminal", "open cmd"]),
            ("check mail", "email_summary", {}, ["check email", "read mail"]),
            ("focus mode", "start_focus", {"duration": 25}, ["start focus", "pomodoro"]),
            ("take screenshot", "screenshot", {}, ["capture screen", "screenshot"]),
            ("what time is it", "get_time", {}, ["current time", "time"]),
            ("show clipboard", "clipboard_history", {}, ["clipboard"]),
            ("quick note", "create_note", {}, ["new note", "take note"]),
            ("search for", "web_search", {}, ["look up", "google"]),
            ("play music", "media_play", {}, ["start music", "resume"]),
            ("pause music", "media_pause", {}, ["stop music", "pause"]),
            ("next track", "media_next", {}, ["skip", "next song"]),
            ("volume up", "volume_up", {"amount": 10}, ["louder", "increase volume"]),
            ("volume down", "volume_down", {"amount": 10}, ["quieter", "decrease volume"]),
            ("mute", "volume_mute", {}, ["silence", "mute audio"]),
            ("lock screen", "lock_screen", {}, ["lock computer", "lock"]),
            ("sleep", "system_sleep", {}, ["go to sleep", "hibernate"]),
        ]
        
        for item in defaults:
            phrase, action, params, aliases = item
            self.register(phrase, action, params, aliases)
    
    def _load_config(self):
        """Load shortcuts from config file."""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
            
            for phrase, data in config.items():
                self.register(
                    phrase,
                    data.get("action"),
                    data.get("params", {}),
                    data.get("aliases", [])
                )
        except Exception:
            self._register_defaults()
    
    def save_config(self):
        """Save shortcuts to config file."""
        if not self.config_path:
            return
        
        config = {}
        seen = set()
        
        for phrase, shortcut in self.shortcuts.items():
            if shortcut.phrase in seen:
                continue
            seen.add(shortcut.phrase)
            
            config[shortcut.phrase] = {
                "action": shortcut.action,
                "params": shortcut.params,
                "aliases": shortcut.aliases
            }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)


# Singleton instance
_voice_shortcuts: Optional[VoiceShortcuts] = None


def get_voice_shortcuts() -> VoiceShortcuts:
    """Get or create global voice shortcuts manager."""
    global _voice_shortcuts
    if _voice_shortcuts is None:
        _voice_shortcuts = VoiceShortcuts()
    return _voice_shortcuts
