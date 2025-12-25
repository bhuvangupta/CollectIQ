"""TTS provider factory."""

import os
from typing import Optional
from .base import TTSProvider


# Global singleton instance
_provider_instance: Optional[TTSProvider] = None


def get_tts_provider() -> TTSProvider:
    """Get the configured TTS provider singleton.

    Uses TTS_PROVIDER environment variable to determine which provider to use.
    Supported values: 'edge' (default), 'sarvam'

    Returns:
        TTSProvider instance

    Raises:
        ValueError: If unknown provider specified
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("TTS_PROVIDER", "edge").lower()

    print(f"[TTS] Initializing {provider_name} provider...")

    if provider_name == "edge":
        from .edge_provider import EdgeTTSProvider
        _provider_instance = EdgeTTSProvider()

    elif provider_name == "sarvam":
        from .sarvam_provider import SarvamTTSProvider
        _provider_instance = SarvamTTSProvider()

    else:
        raise ValueError(
            f"Unknown TTS provider: {provider_name}. "
            "Supported providers: edge, sarvam"
        )

    print(f"[TTS] {_provider_instance.provider_name} provider initialized")
    return _provider_instance


def reset_provider():
    """Reset the provider singleton. Useful for testing."""
    global _provider_instance
    _provider_instance = None
