"""Sarvam AI TTS service using Bulbul model."""

import os
import base64
import httpx
from typing import Optional, AsyncGenerator


class SarvamTTSService:
    """Sarvam AI TTS service using Bulbul model.

    Sarvam's Bulbul model provides:
    - 10 Indian languages + English
    - Multiple voice options (male/female)
    - Code-mixing support (Hinglish, etc.)
    - Adjustable pitch, pace, loudness

    API Docs: https://docs.sarvam.ai/api-reference-docs/text-to-speech/convert
    """

    BASE_URL = "https://api.sarvam.ai"

    # Language code mapping
    LANGUAGE_MAP = {
        "hi": "hi-IN",
        "en": "en-IN",
        "hinglish": "hi-IN",  # Handles code-mixing
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

    # Available voices
    VOICES = {
        "female": ["Anushka", "Manisha", "Vidya", "Arya"],
        "male": ["Abhilash", "Karun", "Hitesh"],
    }

    # Voice mapping by language and gender
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

        # Default settings
        self.default_pace = float(os.getenv("SARVAM_TTS_PACE", "1.0"))
        self.default_pitch = float(os.getenv("SARVAM_TTS_PITCH", "0.0"))
        self.default_loudness = float(os.getenv("SARVAM_TTS_LOUDNESS", "1.0"))

    def _get_voice(self, language: str, voice: str = "default") -> str:
        """Get the voice name for a language and voice type."""
        lang_key = language if language in self.VOICE_MAP else "default"
        lang_voices = self.VOICE_MAP[lang_key]

        if voice in ["male", "female"]:
            return lang_voices.get(voice, lang_voices["default"])
        elif voice == "default":
            return lang_voices["default"]
        elif voice in self.VOICES["female"] + self.VOICES["male"]:
            # Custom voice name provided
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
        output_format: str = "wav",
    ) -> bytes:
        """Convert text to speech.

        Args:
            text: Text to convert (max 1500 chars)
            voice: Voice type ('male', 'female', 'default') or specific voice name
            language: Language code (hi, en, ta, te, bn, mr, gu, kn, ml, pa, od)
            pace: Speech speed (0.5 to 2.0, default 1.0)
            pitch: Voice pitch (-0.75 to 0.75, default 0.0)
            loudness: Volume (0.3 to 3.0, default 1.0)
            sample_rate: Audio sample rate (8000, 16000, 22050, 24000)
            output_format: Output format (wav, mp3, etc.)

        Returns:
            Audio data as bytes
        """
        if not text or not text.strip():
            return self._empty_audio()

        # Truncate if too long
        if len(text) > 1500:
            text = text[:1500]

        # Map language and get voice
        lang_code = self.LANGUAGE_MAP.get(language, "hi-IN")
        speaker = self._get_voice(language, voice)

        # Use defaults if not specified
        pace = pace or self.default_pace
        pitch = pitch or self.default_pitch
        loudness = loudness or self.default_loudness

        # Map output format
        codec_map = {
            "wav": "wav",
            "mp3": "mp3",
            "pcm": "linear16",
            "mulaw": "mulaw",
            "alaw": "alaw",
        }
        output_codec = codec_map.get(output_format, "wav")

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

                # Decode base64 audio
                audios = result.get("audios", [])
                if audios:
                    audio_b64 = audios[0]
                    return base64.b64decode(audio_b64)

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
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio generation.

        Note: Sarvam TTS doesn't support true streaming yet,
        so we synthesize and yield the full audio.
        For real-time applications, use shorter text chunks.
        """
        audio = await self.synthesize(
            text=text,
            voice=voice,
            language=language,
            pace=pace,
            output_format="mp3",
        )

        if audio:
            yield audio

    async def synthesize_chunked(
        self,
        text: str,
        voice: str = "default",
        language: str = "hi",
        chunk_size: int = 200,
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize text in chunks for lower latency.

        Splits text at sentence boundaries and synthesizes each chunk.
        Yields audio as each chunk is ready.
        """
        import re

        # Split by sentence boundaries
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
                    if audio:
                        yield audio
                current_chunk = sentence

        # Yield remaining text
        if current_chunk.strip():
            audio = await self.synthesize(
                text=current_chunk.strip(),
                voice=voice,
                language=language,
                output_format="mp3",
            )
            if audio:
                yield audio

    def _empty_audio(self) -> bytes:
        """Return empty/silent audio for error cases."""
        # Minimal valid WAV header with silence
        return bytes([
            0x52, 0x49, 0x46, 0x46,  # RIFF
            0x24, 0x00, 0x00, 0x00,  # File size
            0x57, 0x41, 0x56, 0x45,  # WAVE
            0x66, 0x6D, 0x74, 0x20,  # fmt
            0x10, 0x00, 0x00, 0x00,  # Subchunk1Size
            0x01, 0x00,              # AudioFormat (PCM)
            0x01, 0x00,              # NumChannels (1)
            0x80, 0x3E, 0x00, 0x00,  # SampleRate (16000)
            0x00, 0x7D, 0x00, 0x00,  # ByteRate
            0x02, 0x00,              # BlockAlign
            0x10, 0x00,              # BitsPerSample (16)
            0x64, 0x61, 0x74, 0x61,  # data
            0x00, 0x00, 0x00, 0x00,  # Subchunk2Size (0)
        ])

    def get_available_voices(self, language: str = None) -> list:
        """Get available voices, optionally filtered by language."""
        return {
            "female": self.VOICES["female"],
            "male": self.VOICES["male"],
        }
