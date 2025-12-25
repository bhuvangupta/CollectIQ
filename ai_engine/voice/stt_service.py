import os
from typing import Dict, Any, Optional
import httpx

from stt import get_stt_provider, STTProvider


class STTService:
    """Speech-to-Text service using configurable provider."""

    def __init__(self):
        self.provider: STTProvider = get_stt_provider()

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
        result = await self.provider.transcribe(audio_data, language)
        return result.to_dict()


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
