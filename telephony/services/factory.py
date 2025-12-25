"""Telephony provider factory."""

import os
from typing import Union

from .mock_provider import MockTelephonyProvider


def get_telephony_provider() -> Union[MockTelephonyProvider, "ExotelProvider"]:
    """Get the configured telephony provider.

    Uses TELEPHONY_PROVIDER environment variable.
    Supported values: 'mock' (default), 'exotel'

    Returns:
        Telephony provider instance

    Raises:
        ValueError: If unknown provider or missing config
    """
    provider_name = os.getenv("TELEPHONY_PROVIDER", "mock").lower()

    print(f"[Telephony] Initializing {provider_name} provider...")

    if provider_name == "mock":
        provider = MockTelephonyProvider()
        print("[Telephony] Mock provider initialized (for development)")
        return provider

    elif provider_name == "exotel":
        from .exotel_provider import ExotelProvider
        provider = ExotelProvider()
        print("[Telephony] Exotel provider initialized (production)")
        return provider

    else:
        raise ValueError(
            f"Unknown telephony provider: {provider_name}. "
            "Supported providers: mock, exotel"
        )
