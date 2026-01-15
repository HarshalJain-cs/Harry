"""
JARVIS Text-to-Speech - Voice synthesis using Piper.

Provides natural-sounding TTS with multiple voice characters.
"""

import os
import tempfile
import subprocess
from typing import Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class VoiceCharacter(Enum):
    """Available voice characters."""
    ARIA = "aria"      # Female, warm and friendly
    ATLAS = "atlas"    # Male, calm and professional


@dataclass
class VoiceConfig:
    """Configuration for a voice character."""
    name: str
    model: str  # Piper model name
    speed: float = 1.0
    pitch: float = 1.0


class TextToSpeech:
    """
    Text-to-Speech using Piper TTS.
    
    Piper is a fast, local neural TTS system with high-quality voices.
    """
    
    # Voice configurations
    VOICES = {
        VoiceCharacter.ARIA: VoiceConfig(
            name="Aria",
            model="en_US-amy-medium",
            speed=1.0,
        ),
        VoiceCharacter.ATLAS: VoiceConfig(
            name="Atlas", 
            model="en_US-ryan-medium",
            speed=1.0,
        ),
    }
    
    # Alternative voices if primary not available
    FALLBACK_VOICES = [
        "en_US-lessac-medium",
        "en_US-libritts-high",
        "en_GB-alan-medium",
    ]
    
    def __init__(self, voice: VoiceCharacter = VoiceCharacter.ARIA):
        """
        Initialize TTS.
        
        Args:
            voice: Voice character to use
        """
        self.current_voice = voice
        self.voice_config = self.VOICES[voice]
        self._piper_available = self._check_piper()
    
    def _check_piper(self) -> bool:
        """Check if Piper is installed."""
        try:
            result = subprocess.run(
                ["piper", "--version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            print("Warning: Piper not found. Install with: pip install piper-tts")
            return False
    
    def set_voice(self, voice: VoiceCharacter):
        """Change voice character."""
        self.current_voice = voice
        self.voice_config = self.VOICES[voice]
    
    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> str:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to speak
            output_path: Path to save audio file (optional)
            speed: Speech speed multiplier (optional)
            
        Returns:
            Path to generated audio file
        """
        if not text.strip():
            return ""
        
        # Create output path
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")
        
        if self._piper_available:
            return self._synthesize_piper(text, output_path, speed)
        else:
            return self._synthesize_fallback(text, output_path)
    
    def _synthesize_piper(
        self,
        text: str,
        output_path: str,
        speed: Optional[float] = None,
    ) -> str:
        """Synthesize using Piper TTS."""
        model = self.voice_config.model
        speech_speed = speed or self.voice_config.speed
        
        # Build piper command
        cmd = [
            "piper",
            "--model", model,
            "--output_file", output_path,
        ]
        
        if speech_speed != 1.0:
            cmd.extend(["--length_scale", str(1.0 / speech_speed)])
        
        # Run piper with text input
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(input=text.encode())
            
            if process.returncode != 0:
                print(f"Piper error: {stderr.decode()}")
                return self._synthesize_fallback(text, output_path)
            
            return output_path
        except Exception as e:
            print(f"TTS error: {e}")
            return self._synthesize_fallback(text, output_path)
    
    def _synthesize_fallback(self, text: str, output_path: str) -> str:
        """Fallback TTS using system voice or edge-tts."""
        try:
            # Try edge-tts as fallback
            import edge_tts
            import asyncio
            
            async def generate():
                communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
                await communicate.save(output_path)
            
            asyncio.run(generate())
            return output_path
        except ImportError:
            pass
        
        # Windows SAPI fallback
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            return output_path
        except:
            pass
        
        print("No TTS engine available. Install piper-tts or edge-tts")
        return ""
    
    def speak(
        self,
        text: str,
        voice: Optional[VoiceCharacter] = None,
        block: bool = True,
    ):
        """
        Speak text out loud.
        
        Args:
            text: Text to speak
            voice: Voice character (uses current if None)
            block: If True, wait for speech to complete
        """
        if voice:
            self.set_voice(voice)
        
        audio_path = self.synthesize(text)
        
        if audio_path and os.path.exists(audio_path):
            self._play_audio(audio_path, block=block)
            
            # Clean up temp file
            if audio_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(audio_path)
                except:
                    pass
    
    def _play_audio(self, audio_path: str, block: bool = True):
        """Play audio file."""
        if not AUDIO_AVAILABLE:
            print(f"Audio playback not available. Audio saved to: {audio_path}")
            return
        
        try:
            data, samplerate = sf.read(audio_path)
            sd.play(data, samplerate)
            if block:
                sd.wait()
        except Exception as e:
            print(f"Audio playback error: {e}")
    
    def say(self, text: str):
        """Quick speak (alias for speak with defaults)."""
        self.speak(text, block=True)


# Convenience functions
def say(text: str, voice: str = "aria"):
    """Quick TTS function."""
    tts = TextToSpeech(
        VoiceCharacter.ARIA if voice == "aria" else VoiceCharacter.ATLAS
    )
    tts.speak(text)


if __name__ == "__main__":
    # Test TTS
    print("Testing Text-to-Speech...")
    
    tts = TextToSpeech(VoiceCharacter.ARIA)
    
    print("Speaking as Aria...")
    tts.speak("Hello! I am JARVIS, your personal AI assistant. How can I help you today?")
    
    print("Speaking as Atlas...")
    tts.speak(
        "Good morning. I am Atlas, the male voice of JARVIS.",
        voice=VoiceCharacter.ATLAS,
    )
    
    print("TTS test complete.")
