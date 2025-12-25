"""Sarvam AI STT provider implementation using Saarika model."""

import os
import httpx
import tempfile
import base64

from .base import STTProvider, TranscriptionResult, TranscriptionSegment


class SarvamSTTProvider(STTProvider):
    """Sarvam AI STT provider using Saarika model.

    Sarvam's Saarika model is optimized for Indian languages with:
    - 11 Indian languages + English support
    - Auto language detection
    - Code-mixing support (Hinglish, etc.)
    - Word-level timestamps

    API Docs: https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe
    """

    BASE_URL = "https://api.sarvam.ai"

    # Language code mapping
    LANGUAGE_MAP = {
        "hi": "hi-IN",
        "en": "en-IN",
        "hinglish": "hi-IN",  # Sarvam handles code-mixing automatically
        "bn": "bn-IN",
        "ta": "ta-IN",
        "te": "te-IN",
        "mr": "mr-IN",
        "gu": "gu-IN",
        "kn": "kn-IN",
        "ml": "ml-IN",
        "pa": "pa-IN",
        "od": "od-IN",
        "auto": "unknown",  # Auto-detect
    }

    # Supported audio formats
    SUPPORTED_FORMATS = {"wav", "mp3", "aac", "ogg", "opus", "flac", "m4a", "webm", "amr", "wma"}

    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY environment variable is required")

        self.model = os.getenv("SARVAM_STT_MODEL", "saarika:v2")

        self.headers = {
            "api-subscription-key": self.api_key,
        }

    @property
    def provider_name(self) -> str:
        return f"sarvam ({self.model})"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hi",
        audio_format: str = "wav"
    ) -> TranscriptionResult:
        """Transcribe audio using Sarvam's Saarika model."""

        # Map language code
        lang_code = self.LANGUAGE_MAP.get(language, "unknown")

        # Ensure format is supported
        if audio_format not in self.SUPPORTED_FORMATS:
            audio_format = "wav"

        # Save to temp file (Sarvam requires file upload)
        suffix = f".{audio_format}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            async with httpx.AsyncClient() as client:
                with open(temp_path, "rb") as audio_file:
                    files = {
                        "file": (f"audio{suffix}", audio_file, f"audio/{audio_format}")
                    }
                    data = {
                        "model": self.model,
                        "language_code": lang_code,
                    }

                    response = await client.post(
                        f"{self.BASE_URL}/speech-to-text",
                        headers=self.headers,
                        files=files,
                        data=data,
                        timeout=30.0
                    )

                    if response.status_code != 200:
                        print(f"[Sarvam STT] Error {response.status_code}: {response.text}")
                        raise Exception(f"Sarvam STT error: {response.text}")

                    result = response.json()

                    # Parse response
                    text = result.get("transcript", "")
                    detected_lang = result.get("language_code", language)

                    # Parse timestamps if available
                    segments = []
                    timestamps = result.get("timestamps", {})
                    words = timestamps.get("words", [])
                    starts = timestamps.get("start_time_seconds", [])
                    ends = timestamps.get("end_time_seconds", [])

                    for i, word in enumerate(words):
                        if i < len(starts) and i < len(ends):
                            segments.append(TranscriptionSegment(
                                start=starts[i],
                                end=ends[i],
                                text=word,
                                confidence=0.95  # Sarvam doesn't provide per-word confidence
                            ))

                    return TranscriptionResult(
                        text=text,
                        segments=segments,
                        language=detected_lang,
                        confidence=0.95
                    )

        except Exception as e:
            print(f"[Sarvam STT] Error: {e}")
            raise

        finally:
            # Cleanup temp file
            os.unlink(temp_path)

    async def transcribe_with_translation(
        self,
        audio_data: bytes,
        source_language: str = "hi",
        target_language: str = "en",
        audio_format: str = "wav"
    ) -> TranscriptionResult:
        """Transcribe and translate audio in one call.

        Useful for getting English translation of Hindi speech.
        """
        lang_code = self.LANGUAGE_MAP.get(source_language, "unknown")
        target_code = self.LANGUAGE_MAP.get(target_language, "en-IN")

        suffix = f".{audio_format}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            async with httpx.AsyncClient() as client:
                with open(temp_path, "rb") as audio_file:
                    files = {
                        "file": (f"audio{suffix}", audio_file, f"audio/{audio_format}")
                    }
                    data = {
                        "model": self.model,
                        "language_code": lang_code,
                        "target_language_code": target_code,
                    }

                    response = await client.post(
                        f"{self.BASE_URL}/speech-to-text-translate",
                        headers=self.headers,
                        files=files,
                        data=data,
                        timeout=30.0
                    )

                    response.raise_for_status()
                    result = response.json()

                    return TranscriptionResult(
                        text=result.get("transcript", ""),
                        segments=[],
                        language=target_language,
                        confidence=0.95
                    )

        finally:
            os.unlink(temp_path)
