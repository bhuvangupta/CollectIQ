"""Sarvam AI Voice Provider with Exotel Telephony.

This provider combines:
- Exotel for phone calls (dial out/in, audio streaming)
- Sarvam STT (Saarika) for speech recognition
- Sarvam LLM for conversation AI
- Sarvam TTS (Bulbul) for voice synthesis

Architecture:
1. Exotel initiates call and streams audio via WebSocket
2. Audio chunks are sent to Sarvam STT for transcription
3. Transcripts are processed by Sarvam LLM
4. LLM responses are converted to speech via Sarvam TTS
5. Audio is streamed back to Exotel

API Docs:
- Sarvam: https://docs.sarvam.ai
- Exotel: https://developer.exotel.com
"""

import os
import uuid
import base64
import asyncio
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import (
    VoiceAIProvider,
    AgentConfig,
    CallResult,
    CallDetails,
    CallStatus,
    CallDisposition,
    BorrowerContext
)
from app.services.sarvam_ai import get_sarvam_ai, SarvamAI


# Default collection agent system prompt
DEFAULT_COLLECTION_PROMPT = """You are Priya, a polite and professional collections officer calling from the finance company.

IMPORTANT RULES:
1. Speak in natural Hinglish (mix of Hindi and English)
2. Be respectful but firm about payment obligations
3. Keep responses SHORT (1-2 sentences max)
4. Listen carefully and respond appropriately
5. If customer agrees to pay, confirm the amount and timeline
6. If customer disputes, offer to verify details
7. Never be rude or threatening

BORROWER DETAILS:
- Name: {borrower_name}
- Outstanding Amount: ₹{outstanding_amount}
- EMI Amount: ₹{emi_amount}
- Days Past Due: {dpd}
- Loan Type: {loan_type}

Start with a polite greeting and state the purpose of call.
"""


class ConversationManager:
    """Manages conversation state for a call."""

    def __init__(self, borrower: BorrowerContext, system_prompt: str):
        self.borrower = borrower
        self.system_prompt = system_prompt.format(
            borrower_name=borrower.name,
            outstanding_amount=borrower.outstanding_amount,
            emi_amount=borrower.emi_amount,
            dpd=borrower.dpd,
            loan_type=borrower.loan_type
        )
        self.messages: List[Dict[str, str]] = []
        self.transcript: List[Dict[str, Any]] = []
        self.start_time = datetime.utcnow()
        self.disposition: Optional[str] = None

    def add_user_message(self, text: str):
        """Add user (customer) message."""
        self.messages.append({"role": "user", "content": text})
        self.transcript.append({
            "role": "user",
            "content": text,
            "timestamp": datetime.utcnow().isoformat()
        })

    def add_assistant_message(self, text: str):
        """Add assistant (agent) message."""
        self.messages.append({"role": "assistant", "content": text})
        self.transcript.append({
            "role": "assistant",
            "content": text,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_transcript_text(self) -> str:
        """Get formatted transcript."""
        lines = []
        for turn in self.transcript:
            role = "Agent" if turn["role"] == "assistant" else "Customer"
            lines.append(f"{role}: {turn['content']}")
        return "\n".join(lines)

    def determine_disposition(self) -> CallDisposition:
        """Analyze transcript to determine call outcome."""
        full_text = " ".join([t["content"].lower() for t in self.transcript])

        if any(w in full_text for w in ["kar dunga", "kar denge", "pay kar", "bhej dunga", "transfer"]):
            return CallDisposition.PROMISE_TO_PAY
        elif any(w in full_text for w in ["baad mein", "callback", "kal call", "phir call"]):
            return CallDisposition.CALLBACK_REQUESTED
        elif any(w in full_text for w in ["galat number", "wrong number", "koi aur"]):
            return CallDisposition.WRONG_NUMBER
        elif any(w in full_text for w in ["already paid", "pay kar diya", "bhej diya"]):
            return CallDisposition.PAYMENT_MADE
        elif any(w in full_text for w in ["dispute", "galat hai", "nahi liya"]):
            return CallDisposition.DISPUTE

        return CallDisposition.CONTACTED


class SarvamProvider(VoiceAIProvider):
    """Sarvam AI Voice Provider with Exotel telephony.

    Uses Sarvam for AI (STT, LLM, TTS) and Exotel for phone calls.
    """

    def __init__(self):
        # Sarvam AI
        self.sarvam = get_sarvam_ai()

        # Exotel credentials
        self.exotel_api_key = os.getenv("EXOTEL_API_KEY")
        self.exotel_api_token = os.getenv("EXOTEL_API_TOKEN")
        self.exotel_sid = os.getenv("EXOTEL_SID")
        self.exotel_subdomain = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.com")

        # Webhook URL for call events
        self.webhook_url = os.getenv("VOICE_AI_WEBHOOK_URL")

        # Active conversations
        self.conversations: Dict[str, ConversationManager] = {}

        # Stored agents (in-memory for now, could be DB-backed)
        self.agents: Dict[str, AgentConfig] = {}

    @property
    def provider_name(self) -> str:
        return "sarvam"

    async def create_agent(self, config: AgentConfig) -> Dict[str, Any]:
        """Create a voice agent configuration."""
        agent_id = str(uuid.uuid4())
        self.agents[agent_id] = config
        return {
            "agent_id": agent_id,
            "name": config.name,
            "status": "active",
            "provider": "sarvam"
        }

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent details."""
        if agent_id not in self.agents:
            # Return default agent
            return {
                "agent_id": agent_id,
                "name": "Default Collection Agent",
                "status": "active",
                "provider": "sarvam"
            }
        config = self.agents[agent_id]
        return {
            "agent_id": agent_id,
            "name": config.name,
            "status": "active",
            "provider": "sarvam"
        }

    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent configuration."""
        if agent_id in self.agents:
            config = self.agents[agent_id]
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        return await self.get_agent(agent_id)

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    async def make_call(
        self,
        agent_id: str,
        borrower: BorrowerContext,
        from_phone: Optional[str] = None
    ) -> CallResult:
        """Initiate an outbound call via Exotel with Sarvam AI.

        This initiates the call through Exotel. The actual AI conversation
        happens via WebSocket streaming in the handle_audio_stream method.
        """
        call_id = str(uuid.uuid4())

        # Get agent config or use default
        agent_config = self.agents.get(agent_id) if agent_id else None
        system_prompt = agent_config.system_prompt if agent_config else DEFAULT_COLLECTION_PROMPT

        # Create conversation manager
        self.conversations[call_id] = ConversationManager(borrower, system_prompt)

        # Check if Exotel is configured
        if not all([self.exotel_api_key, self.exotel_api_token, self.exotel_sid]):
            # Mock mode - simulate successful call initiation
            print(f"[Sarvam] Mock mode - Call {call_id} to {borrower.phone_number}")
            return CallResult(
                success=True,
                call_id=call_id,
                execution_id=call_id,
                message="Call initiated (mock mode)",
                metadata={
                    "provider": "sarvam",
                    "mode": "mock",
                    "borrower_name": borrower.name
                }
            )

        # Make actual call via Exotel
        try:
            result = await self._initiate_exotel_call(
                call_id=call_id,
                to_phone=borrower.phone_number,
                from_phone=from_phone,
                borrower=borrower
            )
            return result
        except Exception as e:
            print(f"[Sarvam] Error initiating call: {e}")
            return CallResult(
                success=False,
                call_id=call_id,
                message=str(e)
            )

    async def _initiate_exotel_call(
        self,
        call_id: str,
        to_phone: str,
        from_phone: Optional[str],
        borrower: BorrowerContext
    ) -> CallResult:
        """Initiate call via Exotel API."""
        # Exotel API endpoint
        url = f"https://{self.exotel_subdomain}/v1/Accounts/{self.exotel_sid}/Calls/connect"

        # Callback URL for audio streaming
        callback_url = f"{self.webhook_url}/voice/sarvam/stream/{call_id}"
        status_callback = f"{self.webhook_url}/telephony/webhook/call-status"

        payload = {
            "From": to_phone,  # Customer's number
            "CallerId": from_phone or os.getenv("EXOTEL_CALLER_ID"),
            "Url": callback_url,  # For audio streaming
            "StatusCallback": status_callback,
            "CustomField": call_id
        }

        auth = (self.exotel_api_key, self.exotel_api_token)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=auth,
                data=payload,
                timeout=30.0
            )

            if response.status_code >= 400:
                return CallResult(
                    success=False,
                    call_id=call_id,
                    message=f"Exotel error: {response.text}"
                )

            data = response.json()
            exotel_sid = data.get("Call", {}).get("Sid", call_id)

            return CallResult(
                success=True,
                call_id=call_id,
                execution_id=exotel_sid,
                metadata={
                    "provider": "sarvam",
                    "exotel_sid": exotel_sid,
                    "borrower_name": borrower.name
                }
            )

    async def stop_call(self, call_id: str) -> bool:
        """Stop an active call."""
        if call_id in self.conversations:
            del self.conversations[call_id]

        if not all([self.exotel_api_key, self.exotel_api_token, self.exotel_sid]):
            return True  # Mock mode

        # Hangup via Exotel
        try:
            url = f"https://{self.exotel_subdomain}/v1/Accounts/{self.exotel_sid}/Calls/{call_id}"
            auth = (self.exotel_api_key, self.exotel_api_token)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    auth=auth,
                    data={"Status": "completed"},
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False

    async def get_call_details(self, call_id: str) -> CallDetails:
        """Get call details."""
        conversation = self.conversations.get(call_id)

        if conversation:
            duration = int((datetime.utcnow() - conversation.start_time).total_seconds())
            return CallDetails(
                call_id=call_id,
                status=CallStatus.COMPLETED,
                duration=duration,
                transcript=conversation.get_transcript_text(),
                transcript_segments=conversation.transcript,
                disposition=conversation.determine_disposition(),
                user_data={"borrower_name": conversation.borrower.name}
            )

        return CallDetails(
            call_id=call_id,
            status=CallStatus.COMPLETED,
            duration=0
        )

    def parse_webhook(self, payload: Dict[str, Any]) -> CallDetails:
        """Parse Exotel webhook payload."""
        call_sid = payload.get("CallSid", "")
        status = payload.get("Status", "").lower()

        status_map = {
            "ringing": CallStatus.RINGING,
            "in-progress": CallStatus.IN_PROGRESS,
            "completed": CallStatus.COMPLETED,
            "failed": CallStatus.FAILED,
            "busy": CallStatus.BUSY,
            "no-answer": CallStatus.NO_ANSWER
        }

        return CallDetails(
            call_id=call_sid,
            status=status_map.get(status, CallStatus.FAILED),
            duration=payload.get("Duration"),
            recording_url=payload.get("RecordingUrl")
        )

    async def process_audio(
        self,
        call_id: str,
        audio_data: bytes
    ) -> Optional[bytes]:
        """Process incoming audio and generate response.

        This is the core AI loop:
        1. Transcribe audio with Sarvam STT
        2. Generate response with Sarvam LLM
        3. Synthesize speech with Sarvam TTS

        Args:
            call_id: Call identifier
            audio_data: Incoming audio bytes

        Returns:
            Response audio bytes or None
        """
        conversation = self.conversations.get(call_id)
        if not conversation:
            return None

        try:
            # 1. Speech to Text
            stt_result = await self.sarvam.speech_to_text(
                audio_data=audio_data,
                audio_format="wav"
            )

            if not stt_result.text.strip():
                return None

            print(f"[Sarvam STT] Customer: {stt_result.text}")
            conversation.add_user_message(stt_result.text)

            # 2. Generate LLM response
            llm_response = await self.sarvam.chat(
                messages=conversation.messages,
                system_prompt=conversation.system_prompt,
                max_tokens=150,
                temperature=0.7
            )

            if not llm_response.text.strip():
                return None

            print(f"[Sarvam LLM] Agent: {llm_response.text}")
            conversation.add_assistant_message(llm_response.text)

            # 3. Text to Speech
            tts_result = await self.sarvam.text_to_speech(
                text=llm_response.text
            )

            # Decode base64 audio
            audio_bytes = base64.b64decode(tts_result.audio_base64)
            return audio_bytes

        except Exception as e:
            print(f"[Sarvam] Error processing audio: {e}")
            return None

    async def generate_welcome_message(self, call_id: str) -> Optional[bytes]:
        """Generate welcome message audio for call start.

        Args:
            call_id: Call identifier

        Returns:
            Welcome audio bytes
        """
        conversation = self.conversations.get(call_id)
        if not conversation:
            return None

        # Generate initial greeting
        welcome_text = f"नमस्ते, क्या मैं {conversation.borrower.name} जी से बात कर सकती हूं? मैं Priya, ABC Finance से बोल रही हूं।"

        try:
            llm_response = await self.sarvam.chat(
                messages=[],
                system_prompt=conversation.system_prompt,
                max_tokens=100,
                temperature=0.7
            )

            greeting = llm_response.text if llm_response.text else welcome_text
            conversation.add_assistant_message(greeting)

            tts_result = await self.sarvam.text_to_speech(text=greeting)
            return base64.b64decode(tts_result.audio_base64)

        except Exception as e:
            print(f"[Sarvam] Error generating welcome: {e}")
            # Fallback to default greeting
            try:
                tts_result = await self.sarvam.text_to_speech(text=welcome_text)
                conversation.add_assistant_message(welcome_text)
                return base64.b64decode(tts_result.audio_base64)
            except Exception:
                return None

    async def end_call(self, call_id: str) -> Dict[str, Any]:
        """End a call and return summary.

        Args:
            call_id: Call identifier

        Returns:
            Call summary with transcript and disposition
        """
        conversation = self.conversations.get(call_id)
        if not conversation:
            return {"status": "not_found"}

        # Generate summary
        summary = ""
        try:
            summary_prompt = f"""Based on this collection call transcript, provide a brief summary (2-3 sentences) of the outcome:

{conversation.get_transcript_text()}

Summary:"""
            summary_response = await self.sarvam.chat(
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=100,
                temperature=0.3
            )
            summary = summary_response.text
        except Exception as e:
            print(f"[Sarvam] Error generating summary: {e}")

        disposition = conversation.determine_disposition()
        duration = int((datetime.utcnow() - conversation.start_time).total_seconds())

        result = {
            "call_id": call_id,
            "status": "completed",
            "duration": duration,
            "transcript": conversation.transcript,
            "transcript_text": conversation.get_transcript_text(),
            "summary": summary,
            "disposition": disposition.value if disposition else "contacted",
            "borrower_name": conversation.borrower.name
        }

        # Clean up
        del self.conversations[call_id]

        return result

    async def health_check(self) -> bool:
        """Check if Sarvam API is accessible."""
        return await self.sarvam.health_check()

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents."""
        return [
            {
                "agent_id": aid,
                "name": config.name,
                "status": "active"
            }
            for aid, config in self.agents.items()
        ]
