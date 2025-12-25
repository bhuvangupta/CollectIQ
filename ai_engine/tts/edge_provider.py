"""Edge TTS provider (Microsoft)."""

import os
import tempfile
from typing import AsyncGenerator, List, Dict, Any

import edge_tts

from .base import TTSProvider


class EdgeTTSProvider(TTSProvider):
    """TTS provider using Microsoft Edge TTS.

    Features:
    - Free to use
    - Multiple Indian language voices
    - Streaming support
    - Adjustable rate and volume
    """

    # Voice mappings for Indian languages
    VOICE_MAP = {
        "hi": {
            "female": "hi-IN-SwaraNeural",
            "male": "hi-IN-MadhurNeural",
            "default": "hi-IN-SwaraNeural",
        },
        "en": {
            "female": "en-IN-NeerjaNeural",
            "male": "en-IN-PrabhatNeural",
            "default": "en-IN-NeerjaNeural",
        },
        "ta": {
            "female": "ta-IN-PallaviNeural",
            "male": "ta-IN-ValluvarNeural",
            "default": "ta-IN-PallaviNeural",
        },
        "te": {
            "female": "te-IN-ShrutiNeural",
            "male": "te-IN-MohanNeural",
            "default": "te-IN-ShrutiNeural",
        },
        "bn": {
            "female": "bn-IN-TanishaaNeural",
            "male": "bn-IN-BashkarNeural",
            "default": "bn-IN-TanishaaNeural",
        },
        "mr": {
            "female": "mr-IN-AarohiNeural",
            "male": "mr-IN-ManoharNeural",
            "default": "mr-IN-AarohiNeural",
        },
        "gu": {
            "female": "gu-IN-DhwaniNeural",
            "male": "gu-IN-NiranjanNeural",
            "default": "gu-IN-DhwaniNeural",
        },
        "kn": {
            "female": "kn-IN-SapnaNeural",
            "male": "kn-IN-GaganNeural",
            "default": "kn-IN-SapnaNeural",
        },
        "ml": {
            "female": "ml-IN-SobhanaNeural",
            "male": "ml-IN-MidhunNeural",
            "default": "ml-IN-SobhanaNeural",
        },
    }

    def __init__(self):
        self.default_rate = os.getenv("TTS_RATE", "+0%")
        self.default_volume = "+0%"

    @property
    def provider_name(self) -> str:
        return "Edge TTS"

    def _get_voice(self, language: str, voice: str = "default") -> str:
        """Get the voice ID for a language and voice type."""
        lang_voices = self.VOICE_MAP.get(language, self.VOICE_MAP["en"])

        if voice in ["male", "female"]:
            return lang_voices.get(voice, lang_voices["default"])
        elif voice == "default":
            return lang_voices["default"]
        else:
            # Custom voice ID provided
            return voice

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        language: str = "hi",
        rate: str = None,
        volume: str = None,
        **kwargs
    ) -> bytes:
        """Convert text to speech.

        Args:
            text: Text to convert to speech
            voice: Voice type ('male', 'female', 'default') or specific voice ID
            language: Language code (hi, en, ta, te, bn, mr, gu, kn, ml)
            rate: Speech rate (e.g., '+10%', '-20%')
            volume: Volume level (e.g., '+10%', '-20%')

        Returns:
            Audio data as bytes (MP3 format)
        """
        if not text or not text.strip():
            return self._empty_audio()

        voice_id = self._get_voice(language, voice)
        rate = rate or self.default_rate
        volume = volume or self.default_volume

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice_id,
                rate=rate,
                volume=volume,
            )

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            await communicate.save(tmp_path)

            with open(tmp_path, "rb") as f:
                audio_data = f.read()

            os.unlink(tmp_path)
            return audio_data

        except Exception as e:
            print(f"[Edge TTS] Error: {e}")
            return self._empty_audio()

    async def synthesize_stream(
        self,
        text: str,
        voice: str = "default",
        language: str = "hi",
        rate: str = None,
        **kwargs
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio generation for real-time playback.

        Yields audio chunks as they are generated.
        """
        voice_id = self._get_voice(language, voice)
        rate = rate or os.getenv("TTS_RATE", "+10%")

        try:
            communicate = edge_tts.Communicate(text=text, voice=voice_id, rate=rate)

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        except Exception as e:
            print(f"[Edge TTS] Streaming error: {e}")

    def _empty_audio(self) -> bytes:
        """Return minimal valid MP3 (silence)."""
        return bytes([
            0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        ])

    def get_available_voices(self, language: str = None) -> List[Dict[str, Any]]:
        """Get available voices, optionally filtered by language."""
        voices = []
        languages = [language] if language else self.VOICE_MAP.keys()

        for lang in languages:
            if lang in self.VOICE_MAP:
                lang_voices = self.VOICE_MAP[lang]
                voices.append({
                    "language": lang,
                    "voices": [
                        {"id": lang_voices["female"], "name": "Female", "gender": "female"},
                        {"id": lang_voices["male"], "name": "Male", "gender": "male"},
                    ]
                })

        return voices

    async def list_all_voices(self) -> list:
        """List all available Edge TTS voices."""
        try:
            voices = await edge_tts.list_voices()
            return [
                {
                    "id": v["ShortName"],
                    "name": v["FriendlyName"],
                    "language": v["Locale"],
                    "gender": v["Gender"],
                }
                for v in voices
            ]
        except Exception as e:
            print(f"[Edge TTS] Error listing voices: {e}")
            return []
