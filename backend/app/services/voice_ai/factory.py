"""Factory for creating Voice AI providers."""

import os
from typing import Optional

from .base import VoiceAIProvider


_provider_instance: Optional[VoiceAIProvider] = None


def get_voice_ai_provider() -> VoiceAIProvider:
    """Get the configured Voice AI provider.

    Returns a singleton instance based on VOICE_AI_PROVIDER environment variable.

    Supported providers:
    - 'mock' (default) - Mock provider for development/testing
    - 'bolna' - Bolna AI (Indian voice AI platform)
    - 'sarvam' - Sarvam AI with Exotel telephony
    - 'livekit' - LiveKit with Sarvam AI
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("VOICE_AI_PROVIDER", "mock").lower()

    if provider_name == "mock":
        from .mock_provider import MockVoiceAIProvider
        _provider_instance = MockVoiceAIProvider()
        print("[Voice AI] Using Mock provider (for development)")
    elif provider_name == "bolna":
        from .bolna_provider import BolnaProvider
        _provider_instance = BolnaProvider()
        print("[Voice AI] Using Bolna provider")
    elif provider_name == "sarvam":
        from .sarvam_provider import SarvamProvider
        _provider_instance = SarvamProvider()
        print("[Voice AI] Using Sarvam provider")
    elif provider_name == "livekit":
        # LiveKit uses its own agent system but we still need a fallback
        from .mock_provider import MockVoiceAIProvider
        _provider_instance = MockVoiceAIProvider()
        print("[Voice AI] LiveKit mode - using Mock for /voice/call, use /voice/livekit/* for real calls")
    else:
        raise ValueError(
            f"Unknown Voice AI provider: {provider_name}. "
            f"Supported: 'mock', 'bolna', 'sarvam', 'livekit'"
        )

    return _provider_instance


def reset_provider():
    """Reset the provider instance (useful for testing)."""
    global _provider_instance
    _provider_instance = None
