"""
JARVIS Noise Cancellation - Audio preprocessing
================================================

Provides noise reduction for cleaner voice input.
Uses noisereduce library as a lightweight alternative to DeepFilterNet.
"""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False


@dataclass
class AudioConfig:
    """Audio configuration."""
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "float32"


class NoiseFilter:
    """
    Audio noise filter.
    
    Uses spectral gating to reduce background noise.
    
    Usage:
        filter = NoiseFilter()
        clean_audio = filter.process_audio(noisy_audio)
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        stationary: bool = True,
        prop_decrease: float = 0.75
    ):
        """
        Initialize noise filter.
        
        Args:
            sample_rate: Audio sample rate
            stationary: Use stationary noise reduction
            prop_decrease: Proportion of noise to reduce (0-1)
        """
        self.sample_rate = sample_rate
        self.stationary = stationary
        self.prop_decrease = prop_decrease
        
        # Noise profile for non-stationary reduction
        self._noise_profile: Optional[np.ndarray] = None
        
        self._enabled = True
    
    @property
    def available(self) -> bool:
        """Check if noise reduction is available."""
        return NOISEREDUCE_AVAILABLE
    
    def process_audio(
        self,
        audio: np.ndarray,
        noise_sample: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Apply noise reduction to audio.
        
        Args:
            audio: Audio data as numpy array
            noise_sample: Optional noise sample for better reduction
            
        Returns:
            Cleaned audio array
        """
        if not self._enabled or not NOISEREDUCE_AVAILABLE:
            return audio
        
        try:
            # Use provided noise sample or stored profile
            y_noise = noise_sample if noise_sample is not None else self._noise_profile
            
            if self.stationary:
                # Stationary noise reduction (faster)
                cleaned = nr.reduce_noise(
                    y=audio,
                    sr=self.sample_rate,
                    stationary=True,
                    prop_decrease=self.prop_decrease
                )
            else:
                # Non-stationary noise reduction (better for variable noise)
                cleaned = nr.reduce_noise(
                    y=audio,
                    sr=self.sample_rate,
                    stationary=False,
                    y_noise=y_noise,
                    prop_decrease=self.prop_decrease
                )
            
            return cleaned
            
        except Exception as e:
            # Return original audio on error
            print(f"Noise reduction error: {e}")
            return audio
    
    def process_file(
        self,
        input_path: str,
        output_path: str
    ) -> bool:
        """
        Process an audio file.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save cleaned audio
            
        Returns:
            True if successful
        """
        if not SOUNDFILE_AVAILABLE:
            raise ImportError("soundfile not installed. Run: pip install soundfile")
        
        try:
            # Read audio
            audio, sr = sf.read(input_path)
            
            # Process
            cleaned = self.process_audio(audio)
            
            # Save
            sf.write(output_path, cleaned, sr)
            
            return True
            
        except Exception as e:
            print(f"File processing error: {e}")
            return False
    
    def set_noise_profile(self, noise_audio: np.ndarray):
        """
        Set a noise profile for non-stationary reduction.
        
        Record a few seconds of ambient noise to improve reduction.
        
        Args:
            noise_audio: Sample of background noise
        """
        self._noise_profile = noise_audio
    
    def enable(self):
        """Enable noise filtering."""
        self._enabled = True
    
    def disable(self):
        """Disable noise filtering."""
        self._enabled = False
    
    @property
    def enabled(self) -> bool:
        """Check if filtering is enabled."""
        return self._enabled


class VoiceActivityDetector:
    """
    Voice Activity Detection (VAD).
    
    Detects speech segments in audio.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 2
    ):
        """
        Initialize VAD.
        
        Args:
            sample_rate: Audio sample rate
            frame_duration_ms: Frame duration in milliseconds
            aggressiveness: VAD aggressiveness (0-3)
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.aggressiveness = aggressiveness
        
        self._vad = None
        self._init_vad()
    
    def _init_vad(self):
        """Initialize webrtcvad."""
        try:
            import webrtcvad
            self._vad = webrtcvad.Vad(self.aggressiveness)
        except ImportError:
            pass
    
    def is_speech(self, audio_frame: bytes) -> bool:
        """
        Check if audio frame contains speech.
        
        Args:
            audio_frame: Audio data as bytes
            
        Returns:
            True if speech detected
        """
        if self._vad is None:
            # Fallback: use energy-based detection
            return self._energy_vad(audio_frame)
        
        try:
            return self._vad.is_speech(audio_frame, self.sample_rate)
        except Exception:
            return self._energy_vad(audio_frame)
    
    def _energy_vad(self, audio_frame: bytes) -> bool:
        """Simple energy-based VAD fallback."""
        # Convert bytes to numpy array
        audio = np.frombuffer(audio_frame, dtype=np.int16)
        
        # Calculate energy
        energy = np.sqrt(np.mean(audio.astype(float) ** 2))
        
        # Threshold (adjust as needed)
        threshold = 500
        
        return energy > threshold
    
    def get_speech_segments(
        self,
        audio: np.ndarray,
        min_duration_ms: int = 100
    ) -> list:
        """
        Get speech segments from audio.
        
        Args:
            audio: Audio data as numpy array
            min_duration_ms: Minimum segment duration
            
        Returns:
            List of (start_ms, end_ms) tuples
        """
        frame_samples = int(self.sample_rate * self.frame_duration_ms / 1000)
        segments = []
        
        is_speaking = False
        start_idx = 0
        
        for i in range(0, len(audio) - frame_samples, frame_samples):
            frame = audio[i:i + frame_samples]
            
            # Convert to bytes for VAD
            frame_bytes = (frame * 32767).astype(np.int16).tobytes()
            
            if self.is_speech(frame_bytes):
                if not is_speaking:
                    is_speaking = True
                    start_idx = i
            else:
                if is_speaking:
                    is_speaking = False
                    # Calculate duration
                    duration_ms = (i - start_idx) / self.sample_rate * 1000
                    if duration_ms >= min_duration_ms:
                        segments.append((
                            int(start_idx / self.sample_rate * 1000),
                            int(i / self.sample_rate * 1000)
                        ))
        
        # Handle ongoing speech at end
        if is_speaking:
            duration_ms = (len(audio) - start_idx) / self.sample_rate * 1000
            if duration_ms >= min_duration_ms:
                segments.append((
                    int(start_idx / self.sample_rate * 1000),
                    int(len(audio) / self.sample_rate * 1000)
                ))
        
        return segments


# Singleton instance
_noise_filter: Optional[NoiseFilter] = None


def get_noise_filter() -> NoiseFilter:
    """Get or create global noise filter."""
    global _noise_filter
    if _noise_filter is None:
        _noise_filter = NoiseFilter()
    return _noise_filter
