"""Factory for creating Voice AI providers."""

import os
from typing import Optional

from .base import VoiceAIProvider


_provider_instance: Optional[VoiceAIProvider] = None


def get_voice_ai_provider() -> VoiceAIProvider:
    """Get the configured Voice AI provider.

    Returns a singleton instance based on VOICE_AI_PROVIDER environment variable.

    Supported providers:
    - 'livekit' (default) - LiveKit with Sarvam AI (recommended)
    - 'sarvam' - Sarvam AI with Exotel telephony
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("VOICE_AI_PROVIDER", "livekit").lower()

    if provider_name == "livekit":
        # LiveKit uses its own agent system, return None
        # LiveKit endpoints are handled separately in the API
        from .livekit_agent import get_livekit_service
        print("Voice AI Provider: LiveKit (use /voice/livekit/* endpoints)")
        return None
    elif provider_name == "sarvam":
        from .sarvam_provider import SarvamProvider
        _provider_instance = SarvamProvider()
    else:
        raise ValueError(
            f"Unknown Voice AI provider: {provider_name}. "
            f"Supported: 'livekit', 'sarvam'"
        )

    print(f"Voice AI Provider: {_provider_instance.provider_name}")
    return _provider_instance


def reset_provider():
    """Reset the provider instance (useful for testing)."""
    global _provider_instance
    _provider_instance = None
