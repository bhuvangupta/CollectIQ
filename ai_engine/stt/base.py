"""Abstract base class for STT providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TranscriptionSegment:
    """A segment of transcribed audio."""
    start: float
    end: float
    text: str
    confidence: float = 0.0


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""
    text: str
    segments: List[TranscriptionSegment] = field(default_factory=list)
    language: str = "en"
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "segments": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "confidence": s.confidence
                }
                for s in self.segments
            ],
            "language": self.language,
            "confidence": self.confidence
        }


class STTProvider(ABC):
    """Abstract base class for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hi",
        audio_format: str = "wav"
    ) -> TranscriptionResult:
        """Transcribe audio data to text.

        Args:
            audio_data: Raw audio bytes.
            language: Language code (e.g., 'hi', 'en').
            audio_format: Audio format (e.g., 'wav', 'mp3', 'webm').

        Returns:
            TranscriptionResult with text and segments.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider."""
        pass

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming transcription."""
        return False
