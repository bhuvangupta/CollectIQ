"""TTS provider abstraction for multiple backends.

Usage:
    from tts import get_tts_provider

    tts = get_tts_provider()  # Returns configured provider
    audio = await tts.synthesize("Hello world", voice="female", language="hi")

Configuration:
    Set TTS_PROVIDER environment variable:
    - 'edge' (default): Microsoft Edge TTS (free, requires internet)
    - 'sarvam': Sarvam AI Bulbul (paid, better Indian voices)
"""

from .base import TTSProvider
from .factory import get_tts_provider, reset_provider

__all__ = ["TTSProvider", "get_tts_provider", "reset_provider"]
