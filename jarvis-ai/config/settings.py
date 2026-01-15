"""
JARVIS Settings - Configuration management.

Handles loading settings from config.json and environment variables.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class VoiceSettings:
    """Voice configuration."""
    wake_word: str = "jarvis"
    default_voice: str = "aria"  # "aria" (female) or "atlas" (male)
    stt_model: str = "small"  # whisper model: tiny, base, small, medium
    tts_speed: float = 1.0
    listen_timeout: float = 5.0  # seconds to listen for command


@dataclass
class LLMSettings:
    """Language model configuration."""
    model: str = "phi3:mini"  # Ollama model name
    temperature: float = 0.7
    max_tokens: int = 500
    timeout: float = 30.0


@dataclass
class ConfidenceSettings:
    """Confidence scoring thresholds."""
    execute_threshold: float = 0.85
    confirm_threshold: float = 0.60
    risk_weights: dict = field(default_factory=lambda: {
        "low": 1.0,
        "medium": 0.8,
        "high": 0.6
    })


@dataclass 
class Settings:
    """Main JARVIS settings container."""
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    confidence: ConfidenceSettings = field(default_factory=ConfidenceSettings)
    
    # Paths
    data_dir: str = "./storage"
    log_file: str = "./storage/jarvis.log"
    
    # Features
    debug_mode: bool = False
    enable_screen_monitoring: bool = True
    enable_emotion_detection: bool = False  # Phase 2
    
    @classmethod
    def from_file(cls, config_path: str = "config.json") -> "Settings":
        """Load settings from JSON file."""
        settings = cls()
        
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = json.load(f)
            
            # Update voice settings
            if "voice" in data:
                for key, value in data["voice"].items():
                    if hasattr(settings.voice, key):
                        setattr(settings.voice, key, value)
            
            # Update LLM settings
            if "llm" in data:
                for key, value in data["llm"].items():
                    if hasattr(settings.llm, key):
                        setattr(settings.llm, key, value)
            
            # Update confidence settings
            if "confidence" in data:
                for key, value in data["confidence"].items():
                    if hasattr(settings.confidence, key):
                        setattr(settings.confidence, key, value)
            
            # Update top-level settings
            for key in ["data_dir", "log_file", "debug_mode", 
                       "enable_screen_monitoring", "enable_emotion_detection"]:
                if key in data:
                    setattr(settings, key, data[key])
        
        # Override with environment variables
        settings._load_env_overrides()
        
        return settings
    
    def _load_env_overrides(self):
        """Override settings from environment variables."""
        if os.getenv("JARVIS_MODEL"):
            self.llm.model = os.getenv("JARVIS_MODEL")
        if os.getenv("JARVIS_VOICE"):
            self.voice.default_voice = os.getenv("JARVIS_VOICE")
        if os.getenv("JARVIS_DEBUG"):
            self.debug_mode = os.getenv("JARVIS_DEBUG").lower() == "true"
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return {
            "voice": {
                "wake_word": self.voice.wake_word,
                "default_voice": self.voice.default_voice,
                "stt_model": self.voice.stt_model,
                "tts_speed": self.voice.tts_speed,
                "listen_timeout": self.voice.listen_timeout,
            },
            "llm": {
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout,
            },
            "confidence": {
                "execute_threshold": self.confidence.execute_threshold,
                "confirm_threshold": self.confidence.confirm_threshold,
                "risk_weights": self.confidence.risk_weights,
            },
            "data_dir": self.data_dir,
            "log_file": self.log_file,
            "debug_mode": self.debug_mode,
            "enable_screen_monitoring": self.enable_screen_monitoring,
            "enable_emotion_detection": self.enable_emotion_detection,
        }
    
    def save(self, config_path: str = "config.json"):
        """Save settings to JSON file."""
        with open(config_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.from_file()
    return _settings
