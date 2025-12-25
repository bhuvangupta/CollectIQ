"""Sarvam AI Service for STT, TTS, and LLM.

Sarvam AI provides:
- Speech-to-Text (Saarika): Hinglish/Hindi transcription
- Text-to-Speech (Bulbul): Natural Hinglish voices
- LLM (Sarvam-M): Hinglish-optimized language model

API Docs: https://docs.sarvam.ai
"""

import os
import base64
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class STTResult:
    """Speech-to-Text result."""
    text: str
    language: str
    confidence: float = 0.0
    words: Optional[List[Dict[str, Any]]] = None


@dataclass
class TTSResult:
    """Text-to-Speech result."""
    audio_base64: str
    audio_format: str = "wav"
    duration_seconds: float = 0.0


@dataclass
class LLMResponse:
    """LLM response."""
    text: str
    usage: Optional[Dict[str, int]] = None


class SarvamAI:
    """Sarvam AI Service for Indian language AI.

    Provides STT (Saarika), TTS (Bulbul), and LLM (Sarvam-M) capabilities
    optimized for Hindi and Hinglish.
    """

    BASE_URL = "https://api.sarvam.ai"

    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY environment variable is required")

        self.stt_model = os.getenv("SARVAM_STT_MODEL", "saarika:v2")
        self.tts_model = os.getenv("SARVAM_TTS_MODEL", "bulbul:v2")
        self.tts_voice = os.getenv("SARVAM_TTS_VOICE", "Anushka")
        self.llm_model = os.getenv("SARVAM_LLM_MODEL", "sarvam-m")
        self.stt_language = os.getenv("SARVAM_STT_LANGUAGE", "hi-IN")
        self.tts_language = os.getenv("SARVAM_TTS_LANGUAGE", "hi-IN-HINGLISH")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def speech_to_text(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        language: str = None,
        sample_rate: int = 16000
    ) -> STTResult:
        """Convert speech to text using Sarvam Saarika.

        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format (wav, mp3, etc.)
            language: Language code (hi-IN, en-IN, etc.)
            sample_rate: Audio sample rate in Hz

        Returns:
            STTResult with transcribed text
        """
        language = language or self.stt_language

        # Encode audio to base64
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        payload = {
            "audio": audio_base64,
            "audio_format": audio_format,
            "language": language,
            "model": self.stt_model,
            "sample_rate": sample_rate
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/speech-to-text",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            return STTResult(
                text=data.get("transcript", ""),
                language=data.get("language", language),
                confidence=data.get("confidence", 0.0),
                words=data.get("words")
            )

    async def speech_to_text_stream(
        self,
        audio_chunk: bytes,
        language: str = None,
        sample_rate: int = 16000
    ) -> Optional[str]:
        """Stream speech to text for real-time transcription.

        Args:
            audio_chunk: Audio chunk bytes
            language: Language code
            sample_rate: Audio sample rate

        Returns:
            Partial transcript or None if still processing
        """
        # For streaming, we use the streaming endpoint
        language = language or self.stt_language
        audio_base64 = base64.b64encode(audio_chunk).decode("utf-8")

        payload = {
            "audio": audio_base64,
            "language": language,
            "model": self.stt_model,
            "sample_rate": sample_rate,
            "streaming": True
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/speech-to-text",
                headers=self.headers,
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("transcript")
            return None

    async def text_to_speech(
        self,
        text: str,
        voice: str = None,
        language: str = None,
        speed: float = 1.0
    ) -> TTSResult:
        """Convert text to speech using Sarvam Bulbul.

        Args:
            text: Text to convert to speech
            voice: Voice name (e.g., Anushka, Arvind)
            language: Language/accent (hi-IN-HINGLISH, hi-IN, en-IN)
            speed: Speech speed multiplier

        Returns:
            TTSResult with audio data
        """
        voice = voice or self.tts_voice
        language = language or self.tts_language

        payload = {
            "text": text,
            "model": self.tts_model,
            "voice": voice,
            "language": language,
            "speed": speed,
            "audio_format": "wav",
            "sample_rate": 16000
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/text-to-speech",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            return TTSResult(
                audio_base64=data.get("audio", ""),
                audio_format=data.get("audio_format", "wav"),
                duration_seconds=data.get("duration", 0.0)
            )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Chat with Sarvam LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System prompt to set context
            max_tokens: Maximum tokens in response
            temperature: Creativity (0-1)

        Returns:
            LLMResponse with generated text
        """
        # Prepare messages with system prompt
        full_messages = []
        if system_prompt:
            full_messages.append({
                "role": "system",
                "content": system_prompt
            })
        full_messages.extend(messages)

        payload = {
            "model": self.llm_model,
            "messages": full_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()

            # Extract response text
            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "")
            else:
                text = ""

            return LLMResponse(
                text=text,
                usage=data.get("usage")
            )

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "hi"
    ) -> str:
        """Translate text between languages.

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated text
        """
        payload = {
            "text": text,
            "source_language": source_lang,
            "target_language": target_lang
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/translate",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("translated_text", text)

    async def health_check(self) -> bool:
        """Check if Sarvam API is accessible."""
        try:
            async with httpx.AsyncClient() as client:
                # Try a simple STT call with minimal audio
                response = await client.get(
                    f"{self.BASE_URL}/health",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
_sarvam_instance: Optional[SarvamAI] = None


def get_sarvam_ai() -> SarvamAI:
    """Get singleton Sarvam AI instance."""
    global _sarvam_instance
    if _sarvam_instance is None:
        _sarvam_instance = SarvamAI()
    return _sarvam_instance
