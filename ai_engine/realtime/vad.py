"""Voice Activity Detection for real-time speech processing."""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class VADResult:
    """Result from VAD processing."""
    is_speech: bool
    speech_probability: float
    is_speech_end: bool = False


class EnergyVAD:
    """Simple energy-based Voice Activity Detection.

    Uses audio energy levels to detect speech vs silence.
    Faster and lighter than neural VAD, good for initial demo.
    """

    def __init__(
        self,
        energy_threshold: float = 0.01,
        min_speech_ms: int = 250,
        min_silence_ms: int = 700,
        sample_rate: int = 16000
    ):
        """Initialize energy-based VAD.

        Args:
            energy_threshold: RMS energy threshold for speech detection
            min_speech_ms: Minimum speech duration to consider valid
            min_silence_ms: Silence duration to mark end of speech
            sample_rate: Audio sample rate in Hz
        """
        self.energy_threshold = energy_threshold
        self.min_speech_samples = int(min_speech_ms * sample_rate / 1000)
        self.min_silence_samples = int(min_silence_ms * sample_rate / 1000)
        self.sample_rate = sample_rate

        # State tracking
        self.speech_started = False
        self.speech_samples = 0
        self.silence_samples = 0

    def process(self, audio_chunk: np.ndarray) -> VADResult:
        """Process an audio chunk and detect speech activity.

        Args:
            audio_chunk: Float32 audio array [-1.0, 1.0]

        Returns:
            VADResult with speech detection info
        """
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        is_speech = rms > self.energy_threshold

        # Normalize to 0-1 probability-like score
        speech_prob = min(1.0, rms / (self.energy_threshold * 3))

        is_speech_end = False

        if is_speech:
            self.speech_started = True
            self.speech_samples += len(audio_chunk)
            self.silence_samples = 0
        else:
            if self.speech_started:
                self.silence_samples += len(audio_chunk)

                # Check if silence is long enough to end speech
                if self.silence_samples >= self.min_silence_samples:
                    # Only mark as speech end if we had enough speech
                    if self.speech_samples >= self.min_speech_samples:
                        is_speech_end = True
                    self.reset()

        return VADResult(
            is_speech=is_speech,
            speech_probability=speech_prob,
            is_speech_end=is_speech_end
        )

    def reset(self) -> None:
        """Reset VAD state."""
        self.speech_started = False
        self.speech_samples = 0
        self.silence_samples = 0

    def has_speech(self) -> bool:
        """Check if speech has been detected."""
        return self.speech_started


class SileroVAD:
    """Voice Activity Detection using Silero VAD model.

    High-accuracy neural VAD for production use.
    Falls back to EnergyVAD if Silero model fails to load.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_ms: int = 250,
        min_silence_ms: int = 700,
        sample_rate: int = 16000
    ):
        """Initialize Silero VAD.

        Args:
            threshold: Speech probability threshold (0.0-1.0)
            min_speech_ms: Minimum speech duration to consider valid
            min_silence_ms: Silence duration to mark end of speech
            sample_rate: Audio sample rate (must be 16000 for Silero)
        """
        self.threshold = threshold
        self.min_speech_samples = int(min_speech_ms * sample_rate / 1000)
        self.min_silence_samples = int(min_silence_ms * sample_rate / 1000)
        self.sample_rate = sample_rate

        # State tracking
        self.speech_started = False
        self.speech_samples = 0
        self.silence_samples = 0

        # Try to load Silero model
        self.model = None
        self.utils = None
        self._fallback_vad = None
        self._load_model()

    def _load_model(self) -> None:
        """Load Silero VAD model."""
        try:
            import torch
            self.model, self.utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            print("Silero VAD model loaded successfully")
        except Exception as e:
            print(f"Failed to load Silero VAD model: {e}")
            print("Falling back to energy-based VAD")
            self._fallback_vad = EnergyVAD(
                min_speech_ms=self.min_speech_samples * 1000 // self.sample_rate,
                min_silence_ms=self.min_silence_samples * 1000 // self.sample_rate,
                sample_rate=self.sample_rate
            )

    def process(self, audio_chunk: np.ndarray) -> VADResult:
        """Process an audio chunk and detect speech activity.

        Args:
            audio_chunk: Float32 audio array [-1.0, 1.0]

        Returns:
            VADResult with speech detection info
        """
        # Use fallback if model not available
        if self._fallback_vad:
            return self._fallback_vad.process(audio_chunk)

        import torch

        # Ensure correct shape for Silero (expects 1D tensor)
        if len(audio_chunk.shape) > 1:
            audio_chunk = audio_chunk.flatten()

        # Convert to tensor
        tensor = torch.from_numpy(audio_chunk).float()

        # Get speech probability from Silero
        speech_prob = self.model(tensor, self.sample_rate).item()
        is_speech = speech_prob > self.threshold

        is_speech_end = False

        if is_speech:
            self.speech_started = True
            self.speech_samples += len(audio_chunk)
            self.silence_samples = 0
        else:
            if self.speech_started:
                self.silence_samples += len(audio_chunk)

                # Check if silence is long enough to end speech
                if self.silence_samples >= self.min_silence_samples:
                    if self.speech_samples >= self.min_speech_samples:
                        is_speech_end = True
                    self.reset()

        return VADResult(
            is_speech=is_speech,
            speech_probability=speech_prob,
            is_speech_end=is_speech_end
        )

    def reset(self) -> None:
        """Reset VAD state."""
        self.speech_started = False
        self.speech_samples = 0
        self.silence_samples = 0

        # Reset model state if using Silero
        if self.model is not None:
            self.model.reset_states()

        if self._fallback_vad:
            self._fallback_vad.reset()

    def has_speech(self) -> bool:
        """Check if speech has been detected."""
        return self.speech_started


def create_vad(
    use_silero: bool = True,
    threshold: float = 0.5,
    min_speech_ms: int = 250,
    min_silence_ms: int = 700,
    sample_rate: int = 16000
):
    """Factory function to create a VAD instance.

    Args:
        use_silero: Whether to try using Silero VAD
        threshold: Speech probability threshold
        min_speech_ms: Minimum speech duration
        min_silence_ms: Silence duration for speech end
        sample_rate: Audio sample rate

    Returns:
        VAD instance (SileroVAD or EnergyVAD)
    """
    if use_silero:
        return SileroVAD(
            threshold=threshold,
            min_speech_ms=min_speech_ms,
            min_silence_ms=min_silence_ms,
            sample_rate=sample_rate
        )
    else:
        return EnergyVAD(
            energy_threshold=0.01,
            min_speech_ms=min_speech_ms,
            min_silence_ms=min_silence_ms,
            sample_rate=sample_rate
        )
