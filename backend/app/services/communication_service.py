from typing import Optional
from uuid import UUID
from datetime import datetime
import httpx

from app.core.config import settings


class TelephonyClient:
    """Client for telephony service."""

    def __init__(self):
        self.base_url = settings.telephony_url
        self.timeout = 30.0

    async def initiate_call(
        self,
        from_number: str,
        to_number: str,
        callback_url: str,
        use_ai: bool = False,
        ai_config: Optional[dict] = None
    ) -> dict:
        """Initiate an outbound call."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/calls/initiate",
                json={
                    "from_number": from_number,
                    "to_number": to_number,
                    "callback_url": callback_url,
                    "use_ai": use_ai,
                    "ai_config": ai_config
                }
            )
            response.raise_for_status()
            return response.json()

    async def send_sms(
        self,
        to_number: str,
        message: str,
        sender_id: Optional[str] = None
    ) -> dict:
        """Send an SMS."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/sms/send",
                json={
                    "to_number": to_number,
                    "message": message,
                    "sender_id": sender_id
                }
            )
            response.raise_for_status()
            return response.json()

    async def send_whatsapp(
        self,
        to_number: str,
        template_id: str,
        template_params: dict
    ) -> dict:
        """Send a WhatsApp message."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/whatsapp/send",
                json={
                    "to_number": to_number,
                    "template_id": template_id,
                    "template_params": template_params
                }
            )
            response.raise_for_status()
            return response.json()

    async def hangup_call(self, call_sid: str) -> dict:
        """Hangup an active call."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/calls/{call_sid}/hangup"
            )
            response.raise_for_status()
            return response.json()

    async def get_call_status(self, call_sid: str) -> dict:
        """Get call status."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/calls/{call_sid}/status"
            )
            response.raise_for_status()
            return response.json()


class AIEngineClient:
    """Client for AI engine service."""

    def __init__(self):
        self.base_url = settings.ai_engine_url
        self.timeout = 60.0

    async def transcribe_audio(
        self,
        audio_url: str,
        language: str = "hi"
    ) -> dict:
        """Transcribe audio file."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/stt/transcribe",
                json={
                    "audio_url": audio_url,
                    "language": language
                }
            )
            response.raise_for_status()
            return response.json()

    async def synthesize_speech(
        self,
        text: str,
        voice: str = "default",
        language: str = "hi"
    ) -> bytes:
        """Convert text to speech."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/tts/synthesize",
                json={
                    "text": text,
                    "voice": voice,
                    "language": language
                }
            )
            response.raise_for_status()
            return response.content

    async def generate_response(
        self,
        conversation_history: list,
        context: dict,
        language: str = "hi"
    ) -> dict:
        """Generate AI response for collection dialog."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/dialog/respond",
                json={
                    "conversation_history": conversation_history,
                    "context": context,
                    "language": language
                }
            )
            response.raise_for_status()
            return response.json()

    async def analyze_sentiment(self, text: str) -> dict:
        """Analyze sentiment of text."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/analyze/sentiment",
                json={"text": text}
            )
            response.raise_for_status()
            return response.json()

    async def summarize_call(
        self,
        transcript: str,
        language: str = "en"
    ) -> dict:
        """Summarize a call transcript."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/analyze/summarize",
                json={
                    "transcript": transcript,
                    "language": language
                }
            )
            response.raise_for_status()
            return response.json()


# Singleton instances
telephony_client = TelephonyClient()
ai_engine_client = AIEngineClient()
