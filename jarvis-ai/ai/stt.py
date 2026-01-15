"""
JARVIS Speech-to-Text - Voice recognition using Whisper.

Uses OpenAI's Whisper model for high-quality local transcription.
"""

import os
import tempfile
from typing import Optional, Union
from pathlib import Path
from dataclasses import dataclass

import numpy as np

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Warning: whisper not installed. Run: pip install openai-whisper")


@dataclass
class TranscriptionResult:
    """Result from speech transcription."""
    text: str
    language: str
    confidence: float
    duration: float


class SpeechToText:
    """
    Speech-to-Text using OpenAI's Whisper.
    
    Model sizes:
    - tiny: 39M params, ~1GB VRAM, fastest
    - base: 74M params, ~1GB VRAM
    - small: 244M params, ~2GB VRAM (recommended)
    - medium: 769M params, ~5GB VRAM
    - large: 1550M params, ~10GB VRAM, best quality
    """
    
    MODELS = {
        "tiny": {"params": "39M", "vram": "~1GB"},
        "base": {"params": "74M", "vram": "~1GB"},
        "small": {"params": "244M", "vram": "~2GB"},
        "medium": {"params": "769M", "vram": "~5GB"},
        "large": {"params": "1550M", "vram": "~10GB"},
    }
    
    def __init__(self, model_size: str = "small", device: Optional[str] = None):
        """
        Initialize Whisper STT.
        
        Args:
            model_size: Model size (tiny, base, small, medium, large)
            device: Device to use (cuda, cpu, or None for auto)
        """
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper not installed. Run: pip install openai-whisper")
        
        self.model_size = model_size
        self.device = device
        self.model = None
        
        if model_size not in self.MODELS:
            raise ValueError(f"Invalid model size. Choose from: {list(self.MODELS.keys())}")
    
    def load_model(self):
        """Load the Whisper model (lazy loading)."""
        if self.model is None:
            print(f"Loading Whisper {self.model_size} model...")
            self.model = whisper.load_model(self.model_size, device=self.device)
            print("Whisper model loaded.")
    
    def transcribe(
        self,
        audio: Union[str, Path, np.ndarray],
        language: str = "en",
        task: str = "transcribe",
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.
        
        Args:
            audio: Path to audio file or numpy array of audio samples
            language: Language code (e.g., "en", "es", "fr")
            task: "transcribe" or "translate" (to English)
            
        Returns:
            TranscriptionResult with text and metadata
        """
        self.load_model()
        
        # Handle numpy array input
        temp_file = None
        if isinstance(audio, np.ndarray):
            import soundfile as sf
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            sf.write(temp_file.name, audio, 16000)
            audio_path = temp_file.name
        else:
            audio_path = str(audio)
        
        try:
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_path,
                language=language,
                task=task,
                fp16=self.device != "cpu",  # Use FP16 on GPU
            )
            
            # Extract text and clean it
            text = result["text"].strip()
            
            # Calculate average confidence from segments
            segments = result.get("segments", [])
            if segments:
                avg_confidence = sum(
                    seg.get("no_speech_prob", 0) for seg in segments
                ) / len(segments)
                confidence = 1.0 - avg_confidence  # Convert no_speech_prob to confidence
            else:
                confidence = 0.9
            
            # Calculate duration
            duration = result.get("duration", 0.0) or (
                segments[-1]["end"] if segments else 0.0
            )
            
            return TranscriptionResult(
                text=text,
                language=result.get("language", language),
                confidence=min(1.0, max(0.0, confidence)),
                duration=duration,
            )
        
        finally:
            # Clean up temp file
            if temp_file:
                os.unlink(temp_file.name)
    
    def transcribe_stream(
        self,
        audio_chunks: list,
        sample_rate: int = 16000,
    ) -> str:
        """
        Transcribe streaming audio chunks.
        
        Args:
            audio_chunks: List of numpy arrays with audio data
            sample_rate: Audio sample rate
            
        Returns:
            Transcribed text
        """
        # Concatenate all chunks
        if not audio_chunks:
            return ""
        
        combined = np.concatenate(audio_chunks)
        
        # Resample if needed
        if sample_rate != 16000:
            import librosa
            combined = librosa.resample(combined, orig_sr=sample_rate, target_sr=16000)
        
        result = self.transcribe(combined)
        return result.text


class AudioRecorder:
    """Helper class to record audio from microphone."""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        Initialize audio recorder.
        
        Args:
            sample_rate: Recording sample rate
            channels: Number of audio channels
        """
        self.sample_rate = sample_rate
        self.channels = channels
    
    def record(self, duration: float = 5.0) -> np.ndarray:
        """
        Record audio for specified duration.
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Numpy array with audio samples
        """
        try:
            import sounddevice as sd
        except ImportError:
            raise RuntimeError("sounddevice not installed. Run: pip install sounddevice")
        
        print(f"Recording for {duration} seconds...")
        audio = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
        )
        sd.wait()
        print("Recording complete.")
        
        return audio.flatten()
    
    def record_until_silence(
        self,
        max_duration: float = 10.0,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.0,
    ) -> np.ndarray:
        """
        Record until silence is detected.
        
        Args:
            max_duration: Maximum recording duration
            silence_threshold: RMS threshold for silence detection
            silence_duration: Seconds of silence before stopping
            
        Returns:
            Numpy array with audio samples
        """
        try:
            import sounddevice as sd
        except ImportError:
            raise RuntimeError("sounddevice not installed")
        
        chunks = []
        silence_start = None
        chunk_duration = 0.1  # 100ms chunks
        
        def callback(indata, frames, time, status):
            nonlocal silence_start
            chunks.append(indata.copy())
            
            # Check for silence
            rms = np.sqrt(np.mean(indata**2))
            if rms < silence_threshold:
                if silence_start is None:
                    silence_start = len(chunks) * chunk_duration
            else:
                silence_start = None
        
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=callback,
            blocksize=int(self.sample_rate * chunk_duration),
        ):
            import time
            start = time.time()
            while time.time() - start < max_duration:
                time.sleep(0.1)
                if silence_start is not None:
                    elapsed_silence = len(chunks) * chunk_duration - silence_start
                    if elapsed_silence >= silence_duration:
                        break
        
        if chunks:
            return np.concatenate(chunks).flatten()
        return np.array([])


if __name__ == "__main__":
    # Test STT
    print("Testing Speech-to-Text...")
    
    stt = SpeechToText(model_size="tiny")  # Use tiny for quick test
    recorder = AudioRecorder()
    
    print("\nSpeak now (recording for 5 seconds)...")
    audio = recorder.record(duration=5.0)
    
    print("Transcribing...")
    result = stt.transcribe(audio)
    print(f"You said: {result.text}")
    print(f"Language: {result.language}, Confidence: {result.confidence:.2f}")
