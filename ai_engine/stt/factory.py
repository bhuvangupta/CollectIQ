"""Factory for creating STT providers."""

import os
from typing import Optional

from .base import STTProvider
from .whisper_provider import WhisperLocalProvider
from .groq_provider import GroqSTTProvider


_provider_instance: Optional[STTProvider] = None


def get_stt_provider() -> STTProvider:
    """Get the configured STT provider.

    Returns a singleton instance based on STT_PROVIDER environment variable.
    Supported values: 'whisper' (default), 'groq'
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("STT_PROVIDER", "whisper").lower()

    if provider_name == "groq":
        _provider_instance = GroqSTTProvider()
    elif provider_name in ("whisper", "whisper-local"):
        _provider_instance = WhisperLocalProvider()
    else:
        raise ValueError(f"Unknown STT provider: {provider_name}. Supported: 'whisper', 'groq'")

    print(f"STT Provider: {_provider_instance.provider_name}")
    return _provider_instance


def reset_provider():
    """Reset the provider instance (useful for testing)."""
    global _provider_instance
    _provider_instance = None
