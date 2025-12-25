"""Audio format conversion utilities."""

import struct
import numpy as np
from typing import Tuple


def pcm16_to_float32(pcm_data: bytes) -> np.ndarray:
    """Convert 16-bit PCM audio to float32 normalized array.

    Args:
        pcm_data: Raw 16-bit PCM audio bytes

    Returns:
        Float32 array normalized to [-1.0, 1.0]
    """
    int16_data = np.frombuffer(pcm_data, dtype=np.int16)
    return int16_data.astype(np.float32) / 32768.0


def float32_to_pcm16(float_data: np.ndarray) -> bytes:
    """Convert float32 audio array to 16-bit PCM bytes.

    Args:
        float_data: Float32 array normalized to [-1.0, 1.0]

    Returns:
        Raw 16-bit PCM audio bytes
    """
    # Clip to valid range and convert
    clipped = np.clip(float_data, -1.0, 1.0)
    int16_data = (clipped * 32767).astype(np.int16)
    return int16_data.tobytes()


def create_wav_header(
    sample_rate: int,
    num_samples: int,
    channels: int = 1,
    bits_per_sample: int = 16
) -> bytes:
    """Create a WAV file header for raw PCM data.

    Args:
        sample_rate: Audio sample rate in Hz
        num_samples: Total number of audio samples
        channels: Number of audio channels (1 for mono)
        bits_per_sample: Bits per sample (16 for PCM16)

    Returns:
        44-byte WAV header
    """
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = num_samples * channels * bits_per_sample // 8

    # RIFF header
    header = struct.pack(
        '<4sI4s',
        b'RIFF',
        36 + data_size,  # File size - 8
        b'WAVE'
    )

    # fmt subchunk
    header += struct.pack(
        '<4sIHHIIHH',
        b'fmt ',
        16,  # Subchunk size
        1,   # Audio format (1 = PCM)
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample
    )

    # data subchunk header
    header += struct.pack(
        '<4sI',
        b'data',
        data_size
    )

    return header


def create_wav_from_pcm(
    pcm_data: bytes,
    sample_rate: int = 16000,
    channels: int = 1
) -> bytes:
    """Create a complete WAV file from PCM data.

    Args:
        pcm_data: Raw 16-bit PCM audio bytes
        sample_rate: Audio sample rate in Hz
        channels: Number of audio channels

    Returns:
        Complete WAV file as bytes
    """
    num_samples = len(pcm_data) // 2  # 16-bit = 2 bytes per sample
    header = create_wav_header(sample_rate, num_samples, channels)
    return header + pcm_data


def resample_audio(
    audio_data: np.ndarray,
    orig_sample_rate: int,
    target_sample_rate: int
) -> np.ndarray:
    """Resample audio to a different sample rate.

    Uses linear interpolation for simplicity.
    For production, consider using scipy.signal.resample or librosa.

    Args:
        audio_data: Float32 audio array
        orig_sample_rate: Original sample rate
        target_sample_rate: Target sample rate

    Returns:
        Resampled audio array
    """
    if orig_sample_rate == target_sample_rate:
        return audio_data

    # Calculate new length
    duration = len(audio_data) / orig_sample_rate
    new_length = int(duration * target_sample_rate)

    # Use numpy interpolation
    old_indices = np.arange(len(audio_data))
    new_indices = np.linspace(0, len(audio_data) - 1, new_length)

    return np.interp(new_indices, old_indices, audio_data)


def get_audio_duration_ms(pcm_data: bytes, sample_rate: int = 16000) -> float:
    """Calculate duration of PCM audio in milliseconds.

    Args:
        pcm_data: Raw 16-bit PCM audio bytes
        sample_rate: Audio sample rate in Hz

    Returns:
        Duration in milliseconds
    """
    num_samples = len(pcm_data) // 2  # 16-bit = 2 bytes per sample
    return (num_samples / sample_rate) * 1000
