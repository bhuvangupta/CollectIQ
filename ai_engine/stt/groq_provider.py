"""Groq STT provider implementation using Whisper API."""

import os
import tempfile
from groq import AsyncGroq

from .base import STTProvider, TranscriptionResult, TranscriptionSegment


class GroqSTTProvider(STTProvider):
    """Groq STT provider using Groq's Whisper API."""

    # Supported audio formats by Groq
    SUPPORTED_FORMATS = {"flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"}

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required for Groq STT provider")

        self.client = AsyncGroq(api_key=api_key)
        self.model = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")

    @property
    def provider_name(self) -> str:
        return f"groq ({self.model})"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hi",
        audio_format: str = "wav"
    ) -> TranscriptionResult:
        """Transcribe audio using Groq's Whisper API."""
        # Ensure format is supported
        if audio_format not in self.SUPPORTED_FORMATS:
            audio_format = "wav"

        # Save to temp file (Groq SDK requires file path)
        suffix = f".{audio_format}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            with open(temp_path, "rb") as audio_file:
                # Use verbose_json for segments
                transcription = await self.client.audio.transcriptions.create(
                    file=(f"audio{suffix}", audio_file),
                    model=self.model,
                    language=language if language != "auto" else None,
                    response_format="verbose_json",
                )

            # Parse response
            text = transcription.text or ""
            segments = []

            # Extract segments if available
            if hasattr(transcription, 'segments') and transcription.segments:
                for seg in transcription.segments:
                    segments.append(TranscriptionSegment(
                        start=getattr(seg, 'start', 0.0),
                        end=getattr(seg, 'end', 0.0),
                        text=getattr(seg, 'text', ''),
                        confidence=getattr(seg, 'avg_logprob', 0.0)
                    ))

            # Calculate confidence
            confidence = 0.95  # Default high confidence for Groq
            if segments:
                avg_logprob = sum(s.confidence for s in segments) / len(segments)
                confidence = min(1.0, max(0.0, (avg_logprob + 1) / 1))

            return TranscriptionResult(
                text=text,
                segments=segments,
                language=getattr(transcription, 'language', language),
                confidence=round(confidence, 2)
            )

        except Exception as e:
            print(f"Groq STT error: {e}")
            raise

        finally:
            # Cleanup
            os.unlink(temp_path)
