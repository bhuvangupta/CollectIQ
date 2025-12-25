"""Speech-to-Text provider abstraction for multiple backends."""

from .base import STTProvider, TranscriptionResult
from .factory import get_stt_provider

__all__ = ["STTProvider", "TranscriptionResult", "get_stt_provider"]
