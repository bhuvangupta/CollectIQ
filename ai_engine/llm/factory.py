"""Factory for creating LLM providers."""

import os
from typing import Optional

from .base import LLMProvider


_provider_instance: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider.

    Returns a singleton instance based on LLM_PROVIDER environment variable.
    Supported values: 'ollama' (default), 'groq', 'sarvam'
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider_name == "groq":
        from .groq_provider import GroqProvider
        _provider_instance = GroqProvider()
    elif provider_name == "ollama":
        from .ollama_provider import OllamaProvider
        _provider_instance = OllamaProvider()
    elif provider_name == "sarvam":
        from .sarvam_provider import SarvamProvider
        _provider_instance = SarvamProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}. Supported: 'ollama', 'groq', 'sarvam'")

    print(f"LLM Provider: {provider_name} (model: {_provider_instance.model_name})")
    return _provider_instance


def reset_provider():
    """Reset the provider instance (useful for testing)."""
    global _provider_instance
    _provider_instance = None
