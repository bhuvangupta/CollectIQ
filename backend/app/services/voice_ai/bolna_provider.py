"""Bolna AI Voice Provider implementation."""

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


class BolnaProvider(VoiceAIProvider):
    """Bolna AI Voice Provider implementation.

    Bolna is an Indian voice AI platform optimized for:
    - Hindi, Hinglish, and regional languages
    - Low latency (<300ms)
    - Integration with Exotel, Twilio, Plivo
    - Natural conversation with interruption handling

    API Docs: https://www.bolna.ai/docs
    """

    BASE_URL = "https://api.bolna.ai"

    def __init__(self):
        self.api_key = os.getenv("BOLNA_API_KEY")
        if not self.api_key:
            raise ValueError("BOLNA_API_KEY environment variable is required")

        self.default_agent_id = os.getenv("BOLNA_AGENT_ID")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @property
    def provider_name(self) -> str:
        return "bolna"

    async def create_agent(self, config: AgentConfig) -> Dict[str, Any]:
        """Create a Bolna voice agent."""
        payload = {
            "agent_config": {
                "agent_name": config.name,
                "agent_type": "collection",
                "agent_welcome_message": config.welcome_message,
                "webhook_url": config.webhook_url,
                "tasks": [
                    {
                        "task_type": "conversation",
                        "toolchain": {
                            "execution": "parallel",
                            "pipelines": [["transcriber", "llm", "synthesizer"]]
                        },
                        "tools_config": {
                            "llm_agent": {
                                "agent_type": "simple_llm_agent",
                                "llm_config": {
                                    "provider": "openai",
                                    "model": "gpt-4o-mini",
                                    "temperature": 0.7,
                                    "max_tokens": 150
                                }
                            },
                            "synthesizer": {
                                "provider": "cartesia",
                                "voice": config.voice_name or "Indian Female",
                                "language": config.language,
                                "stream": True
                            },
                            "transcriber": {
                                "provider": "deepgram",
                                "language": config.language,
                                "stream": True
                            },
                            "input": {"provider": "exotel", "format": "wav"},
                            "output": {"provider": "exotel", "format": "wav"}
                        },
                        "task_config": {
                            "hangup_after_silence": config.silence_timeout,
                            "interruption_threshold": config.interruption_threshold,
                            "optimize_latency": True
                        }
                    }
                ]
            },
            "agent_prompts": {
                "task_1": {"system_prompt": config.system_prompt}
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/v2/agent",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get Bolna agent details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/v2/agent/{agent_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update Bolna agent."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.BASE_URL}/v2/agent/{agent_id}",
                headers=self.headers,
                json=updates,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete Bolna agent."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/v2/agent/{agent_id}",
                headers=self.headers,
                timeout=30.0
            )
            return response.status_code == 200

    async def make_call(
        self,
        agent_id: str,
        borrower: BorrowerContext,
        from_phone: Optional[str] = None
    ) -> CallResult:
        """Make an outbound call via Bolna."""
        agent_id = agent_id or self.default_agent_id
        if not agent_id:
            return CallResult(
                success=False,
                message="No agent_id provided and BOLNA_AGENT_ID not set"
            )

        payload = {
            "agent_id": agent_id,
            "recipient_phone_number": borrower.phone_number,
            "user_data": {
                "borrower_name": borrower.name,
                "outstanding_amount": str(borrower.outstanding_amount),
                "emi_amount": str(borrower.emi_amount),
                "dpd": str(borrower.dpd),
                "loan_type": borrower.loan_type,
                "case_id": borrower.case_id or "",
                **borrower.metadata
            }
        }

        if from_phone:
            payload["from_phone_number"] = from_phone

        try:
            print(f"[Bolna] Making call with payload: {payload}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/call",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                # Log response for debugging
                print(f"[Bolna] Response status: {response.status_code}")
                print(f"[Bolna] Response body: {response.text}")

                if response.status_code >= 400:
                    # Try to get error details from response
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail") or error_data.get("message") or str(error_data)
                    except Exception:
                        error_msg = response.text or f"HTTP {response.status_code}"
                    return CallResult(
                        success=False,
                        message=f"Bolna API error: {error_msg}"
                    )

                response.raise_for_status()
                data = response.json()

                return CallResult(
                    success=True,
                    call_id=data.get("execution_id"),
                    execution_id=data.get("execution_id"),
                    metadata=data
                )
        except httpx.HTTPStatusError as e:
            error_body = e.response.text if e.response else str(e)
            print(f"[Bolna] HTTP error: {error_body}")
            return CallResult(
                success=False,
                message=f"Bolna API error: {error_body}"
            )
        except Exception as e:
            print(f"[Bolna] Exception: {str(e)}")
            return CallResult(
                success=False,
                message=str(e)
            )

    async def stop_call(self, call_id: str) -> bool:
        """Stop a Bolna call."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/call/{call_id}/stop",
                    headers=self.headers,
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception:
            return False

    async def get_call_details(self, call_id: str) -> CallDetails:
        """Get Bolna call details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/call/{call_id}",
                headers=self.headers,
                timeout=30.0
            )
            print(f"[Bolna] Get call details response: {response.text[:1000]}")
            response.raise_for_status()
            data = response.json()
            return self._parse_call_data(data)

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all Bolna agents."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/v2/agent",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    def parse_webhook(self, payload: Dict[str, Any]) -> CallDetails:
        """Parse Bolna webhook payload."""
        return self._parse_call_data(payload)

    def _parse_call_data(self, data: Dict[str, Any]) -> CallDetails:
        """Parse Bolna call data into CallDetails."""
        status = self._map_status(data.get("status", ""))
        transcript_segments = data.get("transcript", [])

        return CallDetails(
            call_id=data.get("execution_id", ""),
            status=status,
            duration=data.get("duration"),
            recording_url=data.get("recording_url"),
            transcript=self._format_transcript(transcript_segments),
            transcript_segments=transcript_segments,
            summary=data.get("summary"),
            disposition=self._determine_disposition(transcript_segments, data.get("disposition")),
            user_data=data.get("user_data"),
            metadata={
                "agent_id": data.get("agent_id"),
                "call_start_time": data.get("call_start_time"),
                "call_end_time": data.get("call_end_time")
            }
        )

    def _map_status(self, bolna_status: str) -> CallStatus:
        """Map Bolna status to standard CallStatus."""
        status_map = {
            "queued": CallStatus.QUEUED,
            "ringing": CallStatus.RINGING,
            "in-progress": CallStatus.IN_PROGRESS,
            "completed": CallStatus.COMPLETED,
            "failed": CallStatus.FAILED,
            "no-answer": CallStatus.NO_ANSWER,
            "busy": CallStatus.BUSY,
            "cancelled": CallStatus.CANCELLED
        }
        return status_map.get(bolna_status, CallStatus.FAILED)

    def _format_transcript(self, segments: List[Dict]) -> str:
        """Format transcript segments to readable text."""
        if not segments:
            return ""

        lines = []
        for entry in segments:
            role = entry.get("role", "unknown")
            text = entry.get("text", "")
            speaker = "Agent" if role == "assistant" else "Customer"
            lines.append(f"{speaker}: {text}")
        return "\n".join(lines)

    def _determine_disposition(
        self,
        segments: List[Dict],
        bolna_disposition: Optional[str]
    ) -> Optional[CallDisposition]:
        """Determine call disposition from transcript."""
        if bolna_disposition:
            disposition_map = {
                "promise_to_pay": CallDisposition.PROMISE_TO_PAY,
                "callback": CallDisposition.CALLBACK_REQUESTED,
                "paid": CallDisposition.PAYMENT_MADE,
                "dispute": CallDisposition.DISPUTE,
                "wrong_number": CallDisposition.WRONG_NUMBER,
                "not_interested": CallDisposition.NOT_INTERESTED
            }
            return disposition_map.get(bolna_disposition, CallDisposition.CONTACTED)

        if not segments:
            return None

        full_text = " ".join([s.get("text", "").lower() for s in segments])

        if any(w in full_text for w in ["kar dunga", "kar denge", "pay", "bhej dunga"]):
            return CallDisposition.PROMISE_TO_PAY
        elif any(w in full_text for w in ["baad mein", "callback", "kal"]):
            return CallDisposition.CALLBACK_REQUESTED
        elif any(w in full_text for w in ["galat number", "wrong number"]):
            return CallDisposition.WRONG_NUMBER
        elif any(w in full_text for w in ["pay kar diya", "already paid"]):
            return CallDisposition.PAYMENT_MADE

        return CallDisposition.CONTACTED

    async def health_check(self) -> bool:
        """Check Bolna API health."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/health",
                    headers=self.headers,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False
