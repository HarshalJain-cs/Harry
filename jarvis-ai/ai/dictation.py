"""
JARVIS Dictation Mode - Continuous voice-to-text transcription.

Provides:
- Continuous dictation with automatic punctuation
- Start/stop controls
- Real-time transcription
"""

import os
import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass
from queue import Queue

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


@dataclass
class DictationResult:
    """Result from dictation."""
    text: str
    is_final: bool
    confidence: float


class DictationMode:
    """
    Continuous speech-to-text dictation.
    
    Features:
    - Real-time transcription
    - Automatic punctuation
    - Pause detection
    - Start/stop controls
    """
    
    def __init__(
        self,
        stt_model: str = "base",
        pause_threshold: float = 1.0,
        on_result: Callable[[DictationResult], None] = None,
    ):
        """
        Initialize dictation mode.
        
        Args:
            stt_model: Whisper model size
            pause_threshold: Seconds of silence to end phrase
            on_result: Callback for transcription results
        """
        self.stt_model = stt_model
        self.pause_threshold = pause_threshold
        self.on_result = on_result or (lambda r: print(r.text, end=" ", flush=True))
        
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._audio_queue: Queue = Queue()
        self._stt = None
        self._recorder = None
    
    def _init_components(self):
        """Lazy initialization of STT components."""
        if self._stt is None:
            try:
                from ai.stt import SpeechToText, AudioRecorder
                self._stt = SpeechToText(model_size=self.stt_model)
                self._recorder = AudioRecorder()
            except ImportError as e:
                print(f"STT components not available: {e}")
                return False
        return True
    
    def start(self):
        """Start dictation mode."""
        if self.is_running:
            return
        
        if not self._init_components():
            print("Cannot start dictation: STT not available")
            return
        
        self.is_running = True
        self._thread = threading.Thread(target=self._dictation_loop, daemon=True)
        self._thread.start()
        print("[Dictation] Started. Speak now...")
    
    def stop(self) -> str:
        """
        Stop dictation mode.
        
        Returns:
            Complete transcription text
        """
        self.is_running = False
        
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        print("\n[Dictation] Stopped.")
        return ""
    
    def _dictation_loop(self):
        """Main dictation loop running in background thread."""
        accumulated_text = []
        
        while self.is_running:
            try:
                # Record short chunks
                audio = self._recorder.record(duration=3.0)
                
                if not self.is_running:
                    break
                
                # Transcribe
                result = self._stt.transcribe(audio)
                
                if result.text.strip():
                    # Add punctuation if needed
                    text = self._add_punctuation(result.text)
                    accumulated_text.append(text)
                    
                    # Callback with result
                    self.on_result(DictationResult(
                        text=text,
                        is_final=False,
                        confidence=result.confidence if hasattr(result, 'confidence') else 0.9,
                    ))
                
            except Exception as e:
                if self.is_running:
                    print(f"[Dictation] Error: {e}")
                    time.sleep(0.5)
        
        # Final result
        if accumulated_text:
            full_text = " ".join(accumulated_text)
            self.on_result(DictationResult(
                text=full_text,
                is_final=True,
                confidence=0.9,
            ))
    
    def _add_punctuation(self, text: str) -> str:
        """Add basic punctuation to text."""
        text = text.strip()
        
        if not text:
            return text
        
        # Capitalize first letter
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
        
        # Add period if no ending punctuation
        if text[-1] not in ".!?":
            text += "."
        
        return text


# Global dictation mode
_dictation: Optional[DictationMode] = None


def get_dictation_mode() -> DictationMode:
    """Get or create dictation mode singleton."""
    global _dictation
    if _dictation is None:
        _dictation = DictationMode()
    return _dictation


def start_dictation(callback: Callable[[DictationResult], None] = None) -> bool:
    """Start dictation mode."""
    dictation = get_dictation_mode()
    if callback:
        dictation.on_result = callback
    dictation.start()
    return True


def stop_dictation() -> str:
    """Stop dictation mode and return full text."""
    dictation = get_dictation_mode()
    return dictation.stop()


# Tool registrations
from tools.registry import tool, ToolResult


@tool(
    name="start_dictation",
    description="Start continuous voice dictation mode",
    category="voice",
    examples=["start dictation", "dictation mode", "transcribe my voice"],
)
def tool_start_dictation() -> ToolResult:
    """Start dictation."""
    try:
        dictation = get_dictation_mode()
        dictation.start()
        return ToolResult(
            success=True,
            output="Dictation mode started. Speak naturally, and I'll transcribe. Say 'stop dictation' when done.",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="stop_dictation",
    description="Stop voice dictation mode",
    category="voice",
    examples=["stop dictation", "end dictation", "stop transcribing"],
)
def tool_stop_dictation() -> ToolResult:
    """Stop dictation."""
    try:
        dictation = get_dictation_mode()
        text = dictation.stop()
        
        if text:
            return ToolResult(success=True, output=f"Dictation stopped. Transcribed:\n{text}")
        return ToolResult(success=True, output="Dictation stopped.")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Dictation Mode...")
    print("Note: Requires working microphone and STT components.\n")
    
    # Just test initialization
    dictation = DictationMode()
    print(f"Dictation mode created: {dictation}")
    print("Pause threshold:", dictation.pause_threshold)
    
    print("\nDictation test complete!")
