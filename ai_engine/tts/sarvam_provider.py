"""Sarvam AI TTS provider using Bulbul model."""

import os
import re
import base64
import httpx
from typing import AsyncGenerator, Optional, List, Dict, Any

from .base import TTSProvider


class SarvamTTSProvider(TTSProvider):
    """TTS provider using Sarvam AI Bulbul model.

    Features:
    - 10 Indian languages + English
    - Multiple voice options (male/female)
    - Code-mixing support (Hinglish)
    - Adjustable pitch, pace, loudness

    API Docs: https://docs.sarvam.ai/api-reference-docs/text-to-speech/convert
    """

    BASE_URL = "https://api.sarvam.ai"

    LANGUAGE_MAP = {
        "hi": "hi-IN",
        "en": "en-IN",
        "hinglish": "hi-IN",
        "bn": "bn-IN",
        "ta": "ta-IN",
        "te": "te-IN",
        "mr": "mr-IN",
        "gu": "gu-IN",
        "kn": "kn-IN",
        "ml": "ml-IN",
        "pa": "pa-IN",
        "od": "od-IN",
    }

    VOICES = {
        "female": ["Anushka", "Manisha", "Vidya", "Arya"],
        "male": ["Abhilash", "Karun", "Hitesh"],
    }

    VOICE_MAP = {
        "hi": {"female": "Anushka", "male": "Abhilash", "default": "Anushka"},
        "en": {"female": "Anushka", "male": "Abhilash", "default": "Anushka"},
        "ta": {"female": "Vidya", "male": "Karun", "default": "Vidya"},
        "te": {"female": "Manisha", "male": "Hitesh", "default": "Manisha"},
        "bn": {"female": "Arya", "male": "Abhilash", "default": "Arya"},
        "default": {"female": "Anushka", "male": "Abhilash", "default": "Anushka"},
    }

    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY environment variable is required")

        self.model = os.getenv("SARVAM_TTS_MODEL", "bulbul:v2")
        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        self.default_pace = float(os.getenv("SARVAM_TTS_PACE", "1.0"))
        self.default_pitch = float(os.getenv("SARVAM_TTS_PITCH", "0.0"))
        self.default_loudness = float(os.getenv("SARVAM_TTS_LOUDNESS", "1.0"))

    @property
    def provider_name(self) -> str:
        return "Sarvam TTS"

    def _get_voice(self, language: str, voice: str = "default") -> str:
        """Get the voice name for a language and voice type."""
        lang_key = language if language in self.VOICE_MAP else "default"
        lang_voices = self.VOICE_MAP[lang_key]

        if voice in ["male", "female"]:
            return lang_voices.get(voice, lang_voices["default"])
        elif voice == "default":
            return lang_voices["default"]
        elif voice in self.VOICES["female"] + self.VOICES["male"]:
            return voice
        else:
            return lang_voices["default"]

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        language: str = "hi",
        pace: Optional[float] = None,
        pitch: Optional[float] = None,
        loudness: Optional[float] = None,
        sample_rate: int = 16000,
        output_format: str = "mp3",
        **kwargs
    ) -> bytes:
        """Convert text to speech.

        Args:
            text: Text to convert (max 1500 chars)
            voice: Voice type or specific voice name
            language: Language code
            pace: Speech speed (0.5 to 2.0)
            pitch: Voice pitch (-0.75 to 0.75)
            loudness: Volume (0.3 to 3.0)
            sample_rate: Audio sample rate
            output_format: Output format (wav, mp3)

        Returns:
            Audio data as bytes
        """
        if not text or not text.strip():
            return self._empty_audio()

        if len(text) > 1500:
            text = text[:1500]

        lang_code = self.LANGUAGE_MAP.get(language, "hi-IN")
        speaker = self._get_voice(language, voice)

        pace = pace or self.default_pace
        pitch = pitch or self.default_pitch
        loudness = loudness or self.default_loudness

        codec_map = {"wav": "wav", "mp3": "mp3", "pcm": "linear16"}
        output_codec = codec_map.get(output_format, "mp3")

        payload = {
            "inputs": [text],
            "target_language_code": lang_code,
            "speaker": speaker,
            "model": self.model,
            "pitch": pitch,
            "pace": pace,
            "loudness": loudness,
            "speech_sample_rate": sample_rate,
            "enable_preprocessing": True,
            "output_audio_codec": output_codec,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/text-to-speech",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code != 200:
                    print(f"[Sarvam TTS] Error {response.status_code}: {response.text}")
                    return self._empty_audio()

                result = response.json()
                audios = result.get("audios", [])
                if audios:
                    return base64.b64decode(audios[0])

                return self._empty_audio()

        except Exception as e:
            print(f"[Sarvam TTS] Error: {e}")
            return self._empty_audio()

    async def synthesize_stream(
        self,
        text: str,
        voice: str = "default",
        language: str = "hi",
        pace: Optional[float] = None,
        **kwargs
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio generation.

        Uses chunked synthesis for lower latency.
        """
        async for chunk in self.synthesize_chunked(text, voice, language):
            yield chunk

    async def synthesize_chunked(
        self,
        text: str,
        voice: str = "default",
        language: str = "hi",
        chunk_size: int = 200,
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize text in chunks for lower latency.

        Splits text at sentence boundaries and synthesizes each chunk.
        """
        sentences = re.split(r'(?<=[।.!?])\s+', text)

        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += " " + sentence
            else:
                if current_chunk.strip():
                    audio = await self.synthesize(
                        text=current_chunk.strip(),
                        voice=voice,
                        language=language,
                        output_format="mp3",
                    )
                    if audio and len(audio) > 50:  # Skip empty audio
                        yield audio
                current_chunk = sentence

        if current_chunk.strip():
            audio = await self.synthesize(
                text=current_chunk.strip(),
                voice=voice,
                language=language,
                output_format="mp3",
            )
            if audio and len(audio) > 50:
                yield audio

    def _empty_audio(self) -> bytes:
        """Return minimal valid MP3 (silence)."""
        return bytes([
            0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        ])

    def get_available_voices(self, language: str = None) -> List[Dict[str, Any]]:
        """Get available Sarvam voices."""
        return [
            {"name": v, "gender": "female", "languages": ["hi", "en", "ta", "te", "bn"]}
            for v in self.VOICES["female"]
        ] + [
            {"name": v, "gender": "male", "languages": ["hi", "en", "ta", "te", "bn"]}
            for v in self.VOICES["male"]
        ]
