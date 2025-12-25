"""Local Whisper STT provider implementation."""

import os
import tempfile
from typing import Optional

from .base import STTProvider, TranscriptionResult, TranscriptionSegment


class WhisperLocalProvider(STTProvider):
    """Local Whisper STT provider using OpenAI Whisper."""

    def __init__(self):
        self.model = None
        self.model_name = os.getenv("WHISPER_MODEL", "base")
        self._load_model()

    def _load_model(self):
        """Load Whisper model."""
        try:
            import whisper
            print(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            print("Whisper model loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load Whisper model: {e}")
            print("STT will use mock responses")

    @property
    def provider_name(self) -> str:
        return f"whisper-local ({self.model_name})"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hi",
        audio_format: str = "wav"
    ) -> TranscriptionResult:
        """Transcribe audio using local Whisper model."""
        if self.model is None:
            return self._mock_transcription(language)

        # Save to temp file
        suffix = f".{audio_format}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            # Transcribe
            result = self.model.transcribe(
                temp_path,
                language=language if language != "auto" else None,
                task="transcribe"
            )

            # Format segments
            segments = []
            for seg in result.get("segments", []):
                segments.append(TranscriptionSegment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"],
                    confidence=seg.get("avg_logprob", 0)
                ))

            return TranscriptionResult(
                text=result["text"],
                segments=segments,
                language=result.get("language", language),
                confidence=self._calculate_confidence(result)
            )

        finally:
            # Cleanup
            os.unlink(temp_path)

    def _calculate_confidence(self, result: dict) -> float:
        """Calculate overall confidence score."""
        segments = result.get("segments", [])
        if not segments:
            return 0.0

        avg_logprob = sum(s.get("avg_logprob", 0) for s in segments) / len(segments)
        # Convert log prob to 0-1 scale (rough approximation)
        confidence = min(1.0, max(0.0, (avg_logprob + 1) / 1))
        return round(confidence, 2)

    def _mock_transcription(self, language: str) -> TranscriptionResult:
        """Return mock transcription for testing."""
        if language == "hi":
            text = "नमस्ते, मैं आपकी EMI के बारे में बात करना चाहता हूं।"
        else:
            text = "Hello, I would like to discuss your EMI payment."

        return TranscriptionResult(
            text=text,
            segments=[
                TranscriptionSegment(start=0.0, end=3.0, text=text, confidence=0.95)
            ],
            language=language,
            confidence=0.95
        )
