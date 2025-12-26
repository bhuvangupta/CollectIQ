"""Telephony provider factory."""

import os
from typing import Union

from .mock_provider import MockTelephonyProvider
from .exotel_provider import ExotelProvider


# Singleton instances
_provider_instance = None


def get_telephony_provider() -> Union[MockTelephonyProvider, ExotelProvider]:
    """Get the configured telephony provider.

    Uses TELEPHONY_PROVIDER environment variable.
    Supported values: 'mock' (default), 'exotel'

    Returns:
        Telephony provider instance (singleton)

    Raises:
        ValueError: If unknown provider or missing config
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("TELEPHONY_PROVIDER", "mock").lower()

    print(f"[Telephony] Initializing {provider_name} provider...")

    if provider_name == "mock":
        _provider_instance = MockTelephonyProvider()
        print("[Telephony] Mock provider initialized (for development)")

    elif provider_name == "exotel":
        _provider_instance = ExotelProvider()
        print("[Telephony] Exotel provider initialized (production)")

    else:
        raise ValueError(
            f"Unknown telephony provider: {provider_name}. "
            "Supported providers: mock, exotel"
        )

    return _provider_instance


def reset_provider():
    """Reset the provider instance (for testing)."""
    global _provider_instance
    _provider_instance = None
