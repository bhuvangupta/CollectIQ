import os
import tempfile
from typing import Dict, Any, Optional
import httpx


class STTService:
    """Speech-to-Text service using Whisper."""

    def __init__(self):
        self.model = None
        self.model_name = os.getenv("WHISPER_MODEL", "large-v3")
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

    async def transcribe(self, audio_url: str, language: str = "hi") -> Dict[str, Any]:
        """Transcribe audio from URL."""
        # Download audio file
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url)
            response.raise_for_status()
            audio_data = response.content

        return await self.transcribe_bytes(audio_data, language)

    async def transcribe_bytes(self, audio_data: bytes, language: str = "hi") -> Dict[str, Any]:
        """Transcribe audio from bytes."""
        if self.model is None:
            # Return mock response if model not loaded
            return self._mock_transcription(language)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
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
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                    "confidence": seg.get("avg_logprob", 0)
                })

            return {
                "text": result["text"],
                "segments": segments,
                "language": result.get("language", language),
                "confidence": self._calculate_confidence(result)
            }

        finally:
            # Cleanup
            os.unlink(temp_path)

    def _calculate_confidence(self, result: Dict) -> float:
        """Calculate overall confidence score."""
        segments = result.get("segments", [])
        if not segments:
            return 0.0

        avg_logprob = sum(s.get("avg_logprob", 0) for s in segments) / len(segments)
        # Convert log prob to 0-1 scale (rough approximation)
        confidence = min(1.0, max(0.0, (avg_logprob + 1) / 1))
        return round(confidence, 2)

    def _mock_transcription(self, language: str) -> Dict[str, Any]:
        """Return mock transcription for testing."""
        if language == "hi":
            text = "नमस्ते, मैं आपकी EMI के बारे में बात करना चाहता हूं।"
        else:
            text = "Hello, I would like to discuss your EMI payment."

        return {
            "text": text,
            "segments": [
                {"start": 0.0, "end": 3.0, "text": text, "confidence": 0.95}
            ],
            "language": language,
            "confidence": 0.95
        }


# Real-time streaming transcription (for future implementation)
class StreamingSTT:
    """Real-time streaming speech recognition."""

    def __init__(self, stt_service: STTService):
        self.stt = stt_service
        self.buffer = b""
        self.sample_rate = 16000

    async def process_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """Process audio chunk and return transcription if available."""
        self.buffer += audio_chunk

        # Process every 2 seconds of audio
        chunk_duration = len(self.buffer) / (self.sample_rate * 2)  # 16-bit audio
        if chunk_duration >= 2.0:
            result = await self.stt.transcribe_bytes(self.buffer, "hi")
            self.buffer = b""
            return result["text"]

        return None

    def reset(self):
        """Reset the buffer."""
        self.buffer = b""
