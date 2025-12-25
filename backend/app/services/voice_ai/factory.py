"""Factory for creating Voice AI providers."""

import os
from typing import Optional

from .base import VoiceAIProvider


_provider_instance: Optional[VoiceAIProvider] = None


def get_voice_ai_provider() -> VoiceAIProvider:
    """Get the configured Voice AI provider.

    Returns a singleton instance based on VOICE_AI_PROVIDER environment variable.

    Supported providers:
    - 'bolna' (default) - Bolna AI for Indian languages
    - 'vapi' - Vapi.ai (future)
    - 'retell' - Retell AI (future)
    - 'bland' - Bland AI (future)
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("VOICE_AI_PROVIDER", "bolna").lower()

    if provider_name == "bolna":
        from .bolna_provider import BolnaProvider
        _provider_instance = BolnaProvider()
    elif provider_name == "elevenlabs":
        from .elevenlabs_provider import ElevenLabsProvider
        _provider_instance = ElevenLabsProvider()
    # Future providers can be added here:
    # elif provider_name == "vapi":
    #     from .vapi_provider import VapiProvider
    #     _provider_instance = VapiProvider()
    # elif provider_name == "retell":
    #     from .retell_provider import RetellProvider
    #     _provider_instance = RetellProvider()
    else:
        raise ValueError(
            f"Unknown Voice AI provider: {provider_name}. "
            f"Supported: 'bolna', 'elevenlabs'"
        )

    print(f"Voice AI Provider: {_provider_instance.provider_name}")
    return _provider_instance


def reset_provider():
    """Reset the provider instance (useful for testing)."""
    global _provider_instance
    _provider_instance = None
