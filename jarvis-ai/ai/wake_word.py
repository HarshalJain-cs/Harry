"""
JARVIS Wake Word Detection - Always-on listening for activation.

Uses OpenWakeWord for fully offline wake word detection.
Falls back to Porcupine if available.
"""

import struct
import time
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False


class WakeWordEngine(Enum):
    """Available wake word detection engines."""
    OPENWAKEWORD = "openwakeword"
    PORCUPINE = "porcupine"


@dataclass
class WakeWordConfig:
    """Wake word configuration."""
    keyword: str = "jarvis"
    sensitivity: float = 0.5
    sample_rate: int = 16000
    frame_length: int = 512


class WakeWordDetector:
    """
    Wake word detector for hands-free activation.
    
    Supports:
    - OpenWakeWord (free, offline)
    - Porcupine (requires API key)
    """
    
    def __init__(
        self,
        keyword: str = "jarvis",
        engine: WakeWordEngine = WakeWordEngine.OPENWAKEWORD,
        sensitivity: float = 0.5,
        access_key: Optional[str] = None,
    ):
        """
        Initialize wake word detector.
        
        Args:
            keyword: Wake word to listen for
            engine: Detection engine to use
            sensitivity: Detection sensitivity (0.0-1.0)
            access_key: Porcupine API key (if using Porcupine)
        """
        self.keyword = keyword.lower()
        self.engine = engine
        self.sensitivity = sensitivity
        self.access_key = access_key
        
        self.config = WakeWordConfig(
            keyword=self.keyword,
            sensitivity=sensitivity,
        )
        
        self._detector = None
        self._audio = None
        self._stream = None
        self._running = False
        
        self._init_detector()
    
    def _init_detector(self):
        """Initialize the detection engine."""
        if self.engine == WakeWordEngine.OPENWAKEWORD:
            self._init_openwakeword()
        else:
            self._init_porcupine()
    
    def _init_openwakeword(self):
        """Initialize OpenWakeWord detector."""
        try:
            from openwakeword import Model
            from openwakeword.utils import download_models
            
            # Download models if needed
            download_models()
            
            # Load model - OpenWakeWord has pre-trained models
            self._detector = Model(
                wakeword_models=["hey_jarvis"],  # Use closest model
                inference_framework="onnx",
            )
            
            print("OpenWakeWord initialized")
        except ImportError:
            print("OpenWakeWord not installed. Run: pip install openwakeword")
            self._detector = None
        except Exception as e:
            print(f"OpenWakeWord init failed: {e}")
            self._detector = None
    
    def _init_porcupine(self):
        """Initialize Porcupine detector."""
        if not self.access_key:
            print("Porcupine requires access_key. Get free key at console.picovoice.ai")
            return
        
        try:
            import pvporcupine
            
            self._detector = pvporcupine.create(
                access_key=self.access_key,
                keywords=[self.keyword] if self.keyword in pvporcupine.KEYWORDS else ["jarvis"],
                sensitivities=[self.sensitivity],
            )
            
            self.config.sample_rate = self._detector.sample_rate
            self.config.frame_length = self._detector.frame_length
            
            print("Porcupine initialized")
        except ImportError:
            print("Porcupine not installed. Run: pip install pvporcupine")
        except Exception as e:
            print(f"Porcupine init failed: {e}")
    
    def _init_audio(self):
        """Initialize audio stream."""
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not installed. Run: pip install pyaudio")
        
        if self._audio is None:
            self._audio = pyaudio.PyAudio()
        
        if self._stream is None:
            self._stream = self._audio.open(
                rate=self.config.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.config.frame_length,
            )
    
    def listen(self, timeout: Optional[float] = None) -> bool:
        """
        Listen for wake word (blocking).
        
        Args:
            timeout: Maximum time to wait (None for infinite)
            
        Returns:
            True if wake word detected, False if timed out
        """
        if self._detector is None:
            print("No wake word detector available")
            return self._fallback_listen()
        
        self._init_audio()
        self._running = True
        
        start_time = time.time()
        
        try:
            while self._running:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    return False
                
                # Read audio frame
                pcm = self._stream.read(
                    self.config.frame_length,
                    exception_on_overflow=False,
                )
                
                # Process based on engine
                if self.engine == WakeWordEngine.OPENWAKEWORD:
                    detected = self._process_openwakeword(pcm)
                else:
                    detected = self._process_porcupine(pcm)
                
                if detected:
                    return True
        
        except KeyboardInterrupt:
            return False
        
        return False
    
    def _process_openwakeword(self, pcm: bytes) -> bool:
        """Process audio with OpenWakeWord."""
        # Convert to numpy
        audio_int16 = np.frombuffer(pcm, dtype=np.int16)
        audio_float = audio_int16.astype(np.float32) / 32768.0
        
        # Run prediction
        prediction = self._detector.predict(audio_float)
        
        # Check if wake word detected
        for key, score in prediction.items():
            if score > self.sensitivity:
                return True
        
        return False
    
    def _process_porcupine(self, pcm: bytes) -> bool:
        """Process audio with Porcupine."""
        pcm_unpacked = struct.unpack_from(
            "h" * self.config.frame_length,
            pcm,
        )
        
        keyword_index = self._detector.process(pcm_unpacked)
        return keyword_index >= 0
    
    def _fallback_listen(self) -> bool:
        """Fallback: wait for Enter key."""
        print(f"\n[No wake word detector - Press Enter to simulate '{self.keyword}']")
        try:
            input()
            return True
        except:
            return False
    
    def listen_continuous(
        self,
        callback: Callable[[], None],
        stop_callback: Optional[Callable[[], bool]] = None,
    ):
        """
        Continuously listen for wake word.
        
        Args:
            callback: Function to call when wake word detected
            stop_callback: Optional function that returns True to stop
        """
        print(f"Listening for '{self.keyword}'... (Ctrl+C to stop)")
        
        while True:
            if stop_callback and stop_callback():
                break
            
            if self.listen(timeout=0.5):
                callback()
    
    def stop(self):
        """Stop listening."""
        self._running = False
    
    def cleanup(self):
        """Clean up resources."""
        self._running = False
        
        if self._stream:
            self._stream.close()
            self._stream = None
        
        if self._audio:
            self._audio.terminate()
            self._audio = None
        
        if self._detector:
            if hasattr(self._detector, "delete"):
                self._detector.delete()
            self._detector = None


if __name__ == "__main__":
    # Test wake word detection
    print("Testing Wake Word Detection...")
    print("Say 'Jarvis' to trigger (or press Enter if no audio)")
    
    detector = WakeWordDetector()
    
    if detector.listen(timeout=10):
        print("Wake word detected!")
    else:
        print("Timeout - no wake word detected")
    
    detector.cleanup()
