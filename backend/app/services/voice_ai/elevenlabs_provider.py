"""ElevenLabs Voice AI Provider implementation."""

import os
import httpx
from typing import Dict, Any, Optional, List

from .base import (
    VoiceAIProvider,
    AgentConfig,
    CallResult,
    CallDetails,
    CallStatus,
    CallDisposition,
    BorrowerContext
)


class ElevenLabsProvider(VoiceAIProvider):
    """ElevenLabs Conversational AI Provider implementation.

    ElevenLabs offers industry-leading voice quality with:
    - 160+ Indian accent variations
    - Hindi, Tamil, Bengali, Marathi, Hinglish support
    - Low latency conversational AI
    - Twilio/SIP trunk integration for phone calls

    API Docs: https://elevenlabs.io/docs/agents-platform/overview
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    # Hindi voice IDs (can be customized)
    DEFAULT_VOICES = {
        "hi": {
            "female": "pMsXgVXv3BLzUgSXRplE",  # Riya - Indian female
            "male": "TX3LPaxmHKxFdv7VOQHJ",    # Indian male voice
        },
        "en": {
            "female": "pMsXgVXv3BLzUgSXRplE",  # Riya
            "male": "TX3LPaxmHKxFdv7VOQHJ",
        }
    }

    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")

        self.default_agent_id = os.getenv("ELEVENLABS_AGENT_ID")
        self.phone_number_id = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")

        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    async def create_agent(self, config: AgentConfig) -> Dict[str, Any]:
        """Create an ElevenLabs voice agent."""
        # Get appropriate voice
        lang_voices = self.DEFAULT_VOICES.get(config.language, self.DEFAULT_VOICES["en"])
        voice_id = config.voice_name or lang_voices.get(config.voice, lang_voices["female"])

        payload = {
            "name": config.name,
            "conversation_config": {
                "agent": {
                    "prompt": {
                        "prompt": config.system_prompt,
                    },
                    "first_message": config.welcome_message,
                    "language": self._map_language(config.language),
                },
                "tts": {
                    "voice_id": voice_id,
                },
            },
            "platform_settings": {
                "call_limits": {
                    "max_duration_seconds": config.max_call_duration,
                }
            }
        }

        if config.webhook_url:
            payload["platform_settings"]["webhooks"] = {
                "post_call_transcription": config.webhook_url
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/convai/agents/create",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get ElevenLabs agent details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/convai/agents/{agent_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update ElevenLabs agent."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.BASE_URL}/convai/agents/{agent_id}",
                headers=self.headers,
                json=updates,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete ElevenLabs agent."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/convai/agents/{agent_id}",
                headers=self.headers,
                timeout=30.0
            )
            return response.status_code in [200, 204]

    async def make_call(
        self,
        agent_id: str,
        borrower: BorrowerContext,
        from_phone: Optional[str] = None
    ) -> CallResult:
        """Make an outbound call via ElevenLabs (through Twilio)."""
        agent_id = agent_id or self.default_agent_id
        if not agent_id:
            return CallResult(
                success=False,
                message="No agent_id provided and ELEVENLABS_AGENT_ID not set"
            )

        phone_number_id = from_phone or self.phone_number_id
        if not phone_number_id:
            return CallResult(
                success=False,
                message="No phone_number_id provided and ELEVENLABS_PHONE_NUMBER_ID not set"
            )

        # Format phone number to E.164
        to_number = self._format_phone_number(borrower.phone_number)

        # Build conversation context to pass to agent
        conversation_data = {
            "borrower_name": borrower.name,
            "outstanding_amount": str(borrower.outstanding_amount),
            "emi_amount": str(borrower.emi_amount),
            "dpd": str(borrower.dpd),
            "loan_type": borrower.loan_type,
            "case_id": borrower.case_id or "",
        }

        # Add any additional metadata
        if borrower.metadata:
            conversation_data.update(borrower.metadata)

        payload = {
            "agent_id": agent_id,
            "agent_phone_number_id": phone_number_id,
            "to_number": to_number,
            "conversation_initiation_client_data": {
                "dynamic_variables": conversation_data
            }
        }

        try:
            print(f"[ElevenLabs] Making call with payload: {payload}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/convai/twilio/outbound-call",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                print(f"[ElevenLabs] Response status: {response.status_code}")
                print(f"[ElevenLabs] Response body: {response.text}")

                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail") or error_data.get("message") or str(error_data)
                    except Exception:
                        error_msg = response.text or f"HTTP {response.status_code}"
                    return CallResult(
                        success=False,
                        message=f"ElevenLabs API error: {error_msg}"
                    )

                response.raise_for_status()
                data = response.json()

                return CallResult(
                    success=data.get("success", True),
                    call_id=data.get("conversation_id"),
                    execution_id=data.get("callSid"),
                    message=data.get("message"),
                    metadata={
                        "callSid": data.get("callSid"),
                        "conversation_id": data.get("conversation_id")
                    }
                )
        except httpx.HTTPStatusError as e:
            error_body = e.response.text if e.response else str(e)
            print(f"[ElevenLabs] HTTP error: {error_body}")
            return CallResult(
                success=False,
                message=f"ElevenLabs API error: {error_body}"
            )
        except Exception as e:
            print(f"[ElevenLabs] Exception: {str(e)}")
            return CallResult(
                success=False,
                message=str(e)
            )

    async def make_call_sip(
        self,
        agent_id: str,
        borrower: BorrowerContext,
        from_phone: Optional[str] = None
    ) -> CallResult:
        """Make an outbound call via ElevenLabs SIP trunk (alternative to Twilio)."""
        agent_id = agent_id or self.default_agent_id
        phone_number_id = from_phone or self.phone_number_id

        if not agent_id or not phone_number_id:
            return CallResult(
                success=False,
                message="agent_id and phone_number_id are required for SIP calls"
            )

        to_number = self._format_phone_number(borrower.phone_number)

        payload = {
            "agent_id": agent_id,
            "agent_phone_number_id": phone_number_id,
            "to_number": to_number,
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "borrower_name": borrower.name,
                    "outstanding_amount": str(borrower.outstanding_amount),
                    "emi_amount": str(borrower.emi_amount),
                    "dpd": str(borrower.dpd),
                    "loan_type": borrower.loan_type,
                    "case_id": borrower.case_id or "",
                }
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/convai/sip-trunk/outbound-call",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                return CallResult(
                    success=data.get("success", True),
                    call_id=data.get("conversation_id"),
                    execution_id=data.get("callSid"),
                    metadata=data
                )
        except Exception as e:
            return CallResult(success=False, message=str(e))

    async def stop_call(self, call_id: str) -> bool:
        """Stop an ElevenLabs call."""
        # ElevenLabs doesn't have a direct stop call endpoint
        # Calls are managed through Twilio if using Twilio integration
        print(f"[ElevenLabs] Stop call not directly supported, call_id: {call_id}")
        return False

    async def get_call_details(self, call_id: str) -> CallDetails:
        """Get ElevenLabs conversation details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/convai/conversations/{call_id}",
                headers=self.headers,
                timeout=30.0
            )
            print(f"[ElevenLabs] Get conversation response: {response.text[:1000]}")
            response.raise_for_status()
            data = response.json()
            return self._parse_conversation_data(data)

    async def get_conversation_audio(self, call_id: str) -> Optional[bytes]:
        """Get the audio recording of a conversation."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/convai/conversations/{call_id}/audio",
                    headers=self.headers,
                    timeout=60.0
                )
                response.raise_for_status()
                return response.content
        except Exception as e:
            print(f"[ElevenLabs] Error getting audio: {e}")
            return None

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all ElevenLabs agents."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/convai/agents",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("agents", [])

    async def list_conversations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List conversations for an agent."""
        params = {"page_size": limit}
        if agent_id:
            params["agent_id"] = agent_id

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/convai/conversations",
                headers=self.headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("conversations", [])

    def parse_webhook(self, payload: Dict[str, Any]) -> CallDetails:
        """Parse ElevenLabs webhook payload."""
        return self._parse_conversation_data(payload)

    def _parse_conversation_data(self, data: Dict[str, Any]) -> CallDetails:
        """Parse ElevenLabs conversation data into CallDetails."""
        status = self._map_status(data.get("status", ""))

        # Extract transcript
        transcript_segments = data.get("transcript", [])
        transcript_text = self._format_transcript(transcript_segments)

        # Get analysis/summary if available
        analysis = data.get("analysis", {})
        summary = analysis.get("summary") or analysis.get("call_summary")

        # Duration from metadata
        metadata = data.get("metadata", {})
        duration = metadata.get("call_duration_secs")

        return CallDetails(
            call_id=data.get("conversation_id", ""),
            status=status,
            duration=int(duration) if duration else None,
            recording_url=None,  # Audio fetched separately
            transcript=transcript_text,
            transcript_segments=transcript_segments,
            summary=summary,
            disposition=self._determine_disposition(transcript_segments, analysis),
            user_data=data.get("conversation_initiation_client_data", {}).get("dynamic_variables"),
            metadata={
                "agent_id": data.get("agent_id"),
                "has_audio": data.get("has_audio", False),
                "has_user_audio": data.get("has_user_audio", False),
                "analysis": analysis
            }
        )

    def _map_status(self, elevenlabs_status: str) -> CallStatus:
        """Map ElevenLabs status to standard CallStatus."""
        status_map = {
            "initiated": CallStatus.QUEUED,
            "in-progress": CallStatus.IN_PROGRESS,
            "processing": CallStatus.IN_PROGRESS,
            "done": CallStatus.COMPLETED,
            "failed": CallStatus.FAILED,
        }
        return status_map.get(elevenlabs_status, CallStatus.FAILED)

    def _format_transcript(self, segments: List[Dict]) -> str:
        """Format transcript segments to readable text."""
        if not segments:
            return ""

        lines = []
        for entry in segments:
            role = entry.get("role", "unknown")
            message = entry.get("message", "")
            speaker = "Agent" if role == "agent" else "Customer"
            lines.append(f"{speaker}: {message}")
        return "\n".join(lines)

    def _determine_disposition(
        self,
        segments: List[Dict],
        analysis: Dict[str, Any]
    ) -> Optional[CallDisposition]:
        """Determine call disposition from transcript and analysis."""
        # Check if analysis provides disposition
        eval_result = analysis.get("evaluation_criteria_results", {})
        if eval_result:
            # Check for specific criteria
            if eval_result.get("payment_commitment"):
                return CallDisposition.PROMISE_TO_PAY
            if eval_result.get("callback_scheduled"):
                return CallDisposition.CALLBACK_REQUESTED

        if not segments:
            return None

        # Analyze transcript for disposition
        full_text = " ".join([s.get("message", "").lower() for s in segments])

        if any(w in full_text for w in ["kar dunga", "kar denge", "pay", "bhej dunga", "payment"]):
            return CallDisposition.PROMISE_TO_PAY
        elif any(w in full_text for w in ["baad mein", "callback", "kal", "later"]):
            return CallDisposition.CALLBACK_REQUESTED
        elif any(w in full_text for w in ["galat number", "wrong number"]):
            return CallDisposition.WRONG_NUMBER
        elif any(w in full_text for w in ["pay kar diya", "already paid", "paid"]):
            return CallDisposition.PAYMENT_MADE

        return CallDisposition.CONTACTED

    def _format_phone_number(self, phone: str) -> str:
        """Format phone number to E.164 format."""
        # Remove spaces, dashes, etc.
        phone = "".join(c for c in phone if c.isdigit() or c == "+")

        # Add India country code if not present
        if not phone.startswith("+"):
            if phone.startswith("91") and len(phone) == 12:
                phone = "+" + phone
            elif len(phone) == 10:
                phone = "+91" + phone
            else:
                phone = "+" + phone

        return phone

    def _map_language(self, language: str) -> str:
        """Map language code to ElevenLabs language."""
        language_map = {
            "hi": "hi",
            "hinglish": "hi",
            "en": "en",
            "ta": "ta",
            "te": "te",
            "bn": "bn",
            "mr": "mr",
            "gu": "gu",
            "kn": "kn",
            "ml": "ml",
        }
        return language_map.get(language, "en")

    async def health_check(self) -> bool:
        """Check ElevenLabs API health."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/user",
                    headers=self.headers,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False
