"""Base class for TTS providers."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, List, Dict, Any


class TTSProvider(ABC):
    """Abstract base class for TTS providers.

    All TTS providers must implement this interface to be used
    interchangeably in the voice pipeline.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the TTS provider."""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        language: str = "hi",
        **kwargs
    ) -> bytes:
        """Convert text to speech.

        Args:
            text: Text to convert to speech
            voice: Voice type ('male', 'female', 'default') or specific voice ID
            language: Language code (hi, en, ta, te, bn, mr, gu, kn, ml)
            **kwargs: Provider-specific options (rate, pitch, etc.)

        Returns:
            Audio data as bytes (format depends on provider)
        """
        pass

    @abstractmethod
    async def synthesize_stream(
        self,
        text: str,
        voice: str = "default",
        language: str = "hi",
        **kwargs
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio generation for real-time playback.

        Args:
            text: Text to synthesize
            voice: Voice type or ID
            language: Language code
            **kwargs: Provider-specific options

        Yields:
            Audio chunks as they are generated
        """
        pass

    def get_available_voices(self, language: str = None) -> List[Dict[str, Any]]:
        """Get available voices, optionally filtered by language.

        Args:
            language: Optional language code to filter by

        Returns:
            List of voice dictionaries with id, name, gender, language
        """
        return []
