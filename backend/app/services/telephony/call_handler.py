"""Call handling and state management."""

import asyncio
import uuid
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import httpx

from .mock_provider import MockTelephonyProvider
from .exotel_provider import ExotelProvider


class CallHandler:
    """Handle call lifecycle and state management."""

    def __init__(self, provider: Union[MockTelephonyProvider, ExotelProvider]):
        self.provider = provider
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        self.call_history: List[Dict[str, Any]] = []

        # AI Engine integration
        self.ai_engine_url = os.getenv("AI_ENGINE_URL", "http://localhost:8001")

    async def initiate_call(
        self,
        phone_number: str,
        caller_id: str,
        borrower_id: str,
        case_id: str,
        campaign_id: Optional[str] = None,
        campaign_borrower_id: Optional[str] = None,
        language: str = "hi",
        callback_url: Optional[str] = None,
        use_ai: bool = False,
        ai_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Initiate an outbound collection call."""
        # Generate internal call ID
        call_id = str(uuid.uuid4())

        # Create call record
        call_data = {
            "call_id": call_id,
            "phone_number": phone_number,
            "caller_id": caller_id,
            "borrower_id": borrower_id,
            "case_id": case_id,
            "campaign_id": campaign_id,
            "campaign_borrower_id": campaign_borrower_id,
            "language": language,
            "direction": "outbound",
            "status": "initiating",
            "created_at": datetime.utcnow().isoformat(),
            "answered_at": None,
            "ended_at": None,
            "duration": 0,
            "recording_url": None,
            "transcript": None,
            "outcome": None,
            "notes": [],
            "conversation_history": [],
            "entities_extracted": {},
            "use_ai": use_ai,
            "ai_context": ai_context or {}
        }

        self.active_calls[call_id] = call_data

        # Initiate call via provider
        try:
            provider_response = await self.provider.initiate_call(
                from_number=caller_id,
                to_number=phone_number,
                caller_id=caller_id,
                callback_url=callback_url,
                custom_field=call_id
            )

            if not provider_response.get("success", True):
                raise ValueError(provider_response.get("error", "Call initiation failed"))

            self.active_calls[call_id]["provider_call_id"] = provider_response.get("call_id")
            self.active_calls[call_id]["status"] = "ringing"

            # Start monitoring call status
            asyncio.create_task(self._monitor_call(call_id))

            return call_id

        except Exception as e:
            self.active_calls[call_id]["status"] = "failed"
            self.active_calls[call_id]["error"] = str(e)
            raise

    async def _monitor_call(self, call_id: str):
        """Monitor call status and handle state transitions."""
        while call_id in self.active_calls:
            call = self.active_calls[call_id]

            if call["status"] in ["completed", "failed", "no-answer", "busy", "no_answer"]:
                # Call ended, move to history
                self.call_history.append(call)
                # Keep in active for a bit for querying
                await asyncio.sleep(60)
                if call_id in self.active_calls:
                    del self.active_calls[call_id]
                break

            # Check provider status
            provider_call_id = call.get("provider_call_id")
            if provider_call_id:
                provider_status = await self.provider.get_call_status(provider_call_id)
                if provider_status:
                    new_status = provider_status.get("status")
                    if new_status and new_status != call["status"]:
                        self.active_calls[call_id]["status"] = new_status

                        if new_status == "in-progress" and not call.get("answered_at"):
                            self.active_calls[call_id]["answered_at"] = datetime.utcnow().isoformat()
                            # Start AI conversation if enabled
                            if call.get("use_ai"):
                                asyncio.create_task(self._start_ai_conversation(call_id))

                        elif new_status in ["completed", "no-answer", "busy", "failed"]:
                            self.active_calls[call_id]["ended_at"] = datetime.utcnow().isoformat()
                            self.active_calls[call_id]["duration"] = provider_status.get("duration", 0)
                            self.active_calls[call_id]["recording_url"] = provider_status.get("recording_url")

                            # Finalize call
                            await self._finalize_call(call_id)

            await asyncio.sleep(1)  # Poll every second

    async def _start_ai_conversation(self, call_id: str):
        """Start AI-driven conversation for the call."""
        call = self.active_calls.get(call_id)
        if not call:
            return

        try:
            # Use stored context
            context = call.get("ai_context") or {}
            context["language"] = call["language"]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ai_engine_url}/dialog/respond",
                    json={
                        "conversation_history": [],
                        "context": context,
                        "language": call["language"]
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    ai_response = response.json()
                    greeting = ai_response.get("response", "")

                    self.active_calls[call_id]["conversation_history"].append({
                        "role": "assistant",
                        "content": greeting,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    print(f"[Call {call_id}] AI: {greeting}")

        except Exception as e:
            print(f"Error starting AI conversation for call {call_id}: {e}")

    async def _finalize_call(self, call_id: str):
        """Finalize call and prepare summary."""
        call = self.active_calls.get(call_id)
        if not call:
            return

        try:
            # Get call summary from AI if there's conversation history
            if call["conversation_history"]:
                transcript = "\n".join([
                    f"{msg['role']}: {msg['content']}"
                    for msg in call["conversation_history"]
                ])

                async with httpx.AsyncClient() as client:
                    summary_response = await client.post(
                        f"{self.ai_engine_url}/analyze/summarize",
                        json={"transcript": transcript},
                        timeout=30.0
                    )

                    if summary_response.status_code == 200:
                        summary_data = summary_response.json()
                        self.active_calls[call_id]["summary"] = summary_data.get("summary")
                        self.active_calls[call_id]["key_points"] = summary_data.get("key_points", [])

            # Determine outcome based on conversation
            outcome = self._determine_outcome(call)
            self.active_calls[call_id]["outcome"] = outcome

        except Exception as e:
            print(f"Error finalizing call {call_id}: {e}")

    def _determine_outcome(self, call: Dict[str, Any]) -> str:
        """Determine call outcome based on conversation."""
        status = call.get("status", "")

        if status in ["no-answer", "no_answer"]:
            return "no_answer"
        elif status == "busy":
            return "busy"
        elif call.get("duration", 0) < 10:
            return "short_call"

        # Check entities for promises
        entities = call.get("entities_extracted", {})
        if entities.get("amounts") or entities.get("dates"):
            return "promise_to_pay"

        # Check conversation for indicators
        history = call.get("conversation_history", [])
        for msg in history:
            content = msg.get("content", "").lower()
            if any(word in content for word in ["pay", "भुगतान", "दूंगा", "करूंगा"]):
                return "promise_to_pay"
            elif any(word in content for word in ["dispute", "विवाद", "गलत"]):
                return "disputed"
            elif any(word in content for word in ["hardship", "मुश्किल", "problem"]):
                return "hardship"

        return "contacted"

    def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get call data by ID."""
        return self.active_calls.get(call_id)

    def update_call_status(
        self,
        call_id: str,
        status: str,
        duration: Optional[int] = None,
        recording_url: Optional[str] = None
    ):
        """Update call status from external webhook."""
        if call_id in self.active_calls:
            self.active_calls[call_id]["status"] = status
            if duration is not None:
                self.active_calls[call_id]["duration"] = duration
            if recording_url:
                self.active_calls[call_id]["recording_url"] = recording_url

    async def end_call(self, call_id: str) -> Dict[str, Any]:
        """End an active call."""
        if call_id not in self.active_calls:
            raise ValueError(f"Call {call_id} not found")

        call = self.active_calls[call_id]

        # End via provider
        provider_call_id = call.get("provider_call_id")
        if provider_call_id:
            try:
                await self.provider.end_call(provider_call_id)
            except Exception as e:
                print(f"Error ending call via provider: {e}")

        # Update local state
        self.active_calls[call_id]["status"] = "completed"
        self.active_calls[call_id]["ended_at"] = datetime.utcnow().isoformat()

        if call.get("answered_at"):
            started = datetime.fromisoformat(call["answered_at"])
            duration = int((datetime.utcnow() - started).total_seconds())
            self.active_calls[call_id]["duration"] = duration

        await self._finalize_call(call_id)

        return self.active_calls[call_id]

    async def send_dtmf(self, call_id: str, digits: str) -> Dict[str, Any]:
        """Send DTMF tones to a call."""
        if call_id not in self.active_calls:
            raise ValueError(f"Call {call_id} not found")

        # In production, this would send DTMF via provider
        return {"call_id": call_id, "digits": digits, "status": "sent"}

    def get_active_calls(self) -> List[Dict[str, Any]]:
        """Get all active calls."""
        return list(self.active_calls.values())

    def get_call_stats(self) -> Dict[str, Any]:
        """Get call statistics."""
        active = len(self.active_calls)
        total = len(self.call_history) + active

        outcomes = {}
        for call in self.call_history:
            outcome = call.get("outcome", "unknown")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

        return {
            "active_calls": active,
            "total_calls": total,
            "outcomes": outcomes
        }
