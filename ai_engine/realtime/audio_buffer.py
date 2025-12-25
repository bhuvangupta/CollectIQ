"""Audio buffer for accumulating audio chunks."""

import numpy as np
from typing import Optional, List
from .audio_utils import pcm16_to_float32, get_audio_duration_ms


class AudioBuffer:
    """Manages audio chunk accumulation with proper format handling.

    Accumulates incoming audio chunks until they can be processed
    as a complete utterance.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        max_duration_ms: float = 30000  # 30 seconds max
    ):
        """Initialize audio buffer.

        Args:
            sample_rate: Expected sample rate of incoming audio
            channels: Number of audio channels (1 for mono)
            max_duration_ms: Maximum buffer duration before auto-reset
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.max_duration_ms = max_duration_ms
        self.chunks: List[bytes] = []
        self._total_bytes = 0

    def append(self, chunk: bytes) -> None:
        """Add an audio chunk to the buffer.

        Args:
            chunk: Raw 16-bit PCM audio bytes
        """
        self.chunks.append(chunk)
        self._total_bytes += len(chunk)

        # Auto-reset if buffer gets too long
        if self.get_duration_ms() > self.max_duration_ms:
            print(f"Audio buffer exceeded {self.max_duration_ms}ms, resetting")
            self.reset()

    def get_bytes(self) -> bytes:
        """Get all accumulated audio as raw bytes.

        Returns:
            Combined raw PCM bytes
        """
        return b''.join(self.chunks)

    def get_float32(self) -> np.ndarray:
        """Get all accumulated audio as float32 array.

        Returns:
            Float32 numpy array normalized to [-1.0, 1.0]
        """
        pcm_data = self.get_bytes()
        if not pcm_data:
            return np.array([], dtype=np.float32)
        return pcm16_to_float32(pcm_data)

    def get_and_reset(self) -> bytes:
        """Get all audio and reset the buffer.

        Returns:
            Combined raw PCM bytes
        """
        result = self.get_bytes()
        self.reset()
        return result

    def get_float32_and_reset(self) -> np.ndarray:
        """Get all audio as float32 and reset the buffer.

        Returns:
            Float32 numpy array
        """
        result = self.get_float32()
        self.reset()
        return result

    def reset(self) -> None:
        """Clear the buffer."""
        self.chunks = []
        self._total_bytes = 0

    def get_duration_ms(self) -> float:
        """Get current buffer duration in milliseconds.

        Returns:
            Duration in milliseconds
        """
        # For 16-bit audio: 2 bytes per sample
        num_samples = self._total_bytes // 2
        return (num_samples / self.sample_rate) * 1000

    def get_sample_count(self) -> int:
        """Get number of samples in buffer.

        Returns:
            Number of audio samples
        """
        return self._total_bytes // 2

    def is_empty(self) -> bool:
        """Check if buffer is empty.

        Returns:
            True if no audio in buffer
        """
        return self._total_bytes == 0

    def __len__(self) -> int:
        """Return number of bytes in buffer."""
        return self._total_bytes
