"""Call handling and state management."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import os
import httpx

from .mock_provider import MockTelephonyProvider


class CallHandler:
    """Handle call lifecycle and state management."""

    def __init__(self, provider: MockTelephonyProvider):
        self.provider = provider
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        self.call_history: List[Dict[str, Any]] = []

        # AI Engine integration
        self.ai_engine_url = os.getenv("AI_ENGINE_URL", "http://ai-engine:8001")
        self.backend_url = os.getenv("BACKEND_URL", "http://backend:8000")

    async def initiate_call(
        self,
        phone_number: str,
        caller_id: str,
        borrower_id: str,
        case_id: str,
        campaign_id: Optional[str] = None,
        language: str = "hi",
        callback_url: Optional[str] = None
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
            "entities_extracted": {}
        }

        self.active_calls[call_id] = call_data

        # Initiate call via provider
        try:
            provider_response = await self.provider.initiate_call(
                from_number=caller_id,
                to_number=phone_number,
                callback_url=callback_url,
                custom_field=call_id
            )

            self.active_calls[call_id]["provider_call_id"] = provider_response["call_id"]
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

            if call["status"] in ["completed", "failed", "no-answer", "busy"]:
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
                    if new_status != call["status"]:
                        self.active_calls[call_id]["status"] = new_status

                        if new_status == "in-progress" and not call.get("answered_at"):
                            self.active_calls[call_id]["answered_at"] = datetime.utcnow().isoformat()
                            # Start AI conversation
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
            # Get borrower context from backend
            context = await self._get_borrower_context(call["borrower_id"], call["case_id"])

            # Get initial greeting from AI
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

                    # Add to conversation history
                    self.active_calls[call_id]["conversation_history"].append({
                        "role": "assistant",
                        "content": greeting,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    # TTS would be triggered here to speak the greeting
                    print(f"[Call {call_id}] AI: {greeting}")

        except Exception as e:
            print(f"Error starting AI conversation for call {call_id}: {e}")

    async def _get_borrower_context(self, borrower_id: str, case_id: str) -> Dict[str, Any]:
        """Get borrower context from backend."""
        # In production, this would fetch from backend API
        # For mock, return sample context
        return {
            "borrower_name": "Test Customer",
            "outstanding_amount": 50000,
            "dpd": 30,
            "emi_amount": 5000,
            "loan_type": "Personal Loan",
            "previous_promises": [],
            "payment_history": []
        }

    async def process_borrower_speech(
        self,
        call_id: str,
        audio_data: bytes
    ) -> Optional[Dict[str, Any]]:
        """Process borrower speech and get AI response."""
        call = self.active_calls.get(call_id)
        if not call or call["status"] != "in-progress":
            return None

        try:
            async with httpx.AsyncClient() as client:
                # Speech to text
                stt_response = await client.post(
                    f"{self.ai_engine_url}/stt/transcribe",
                    files={"file": ("audio.wav", audio_data, "audio/wav")},
                    data={"language": call["language"]},
                    timeout=30.0
                )

                if stt_response.status_code != 200:
                    return None

                transcript_data = stt_response.json()
                borrower_text = transcript_data.get("text", "")

                if not borrower_text.strip():
                    return None

                # Add to conversation history
                self.active_calls[call_id]["conversation_history"].append({
                    "role": "user",
                    "content": borrower_text,
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Get AI response
                context = await self._get_borrower_context(call["borrower_id"], call["case_id"])

                dialog_response = await client.post(
                    f"{self.ai_engine_url}/dialog/respond",
                    json={
                        "conversation_history": call["conversation_history"],
                        "context": context,
                        "language": call["language"]
                    },
                    timeout=30.0
                )

                if dialog_response.status_code != 200:
                    return None

                ai_data = dialog_response.json()
                ai_text = ai_data.get("response", "")

                # Add AI response to history
                self.active_calls[call_id]["conversation_history"].append({
                    "role": "assistant",
                    "content": ai_text,
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Update extracted entities
                if ai_data.get("entities"):
                    self.active_calls[call_id]["entities_extracted"].update(ai_data["entities"])

                # Check if should end call
                if ai_data.get("should_end"):
                    asyncio.create_task(self._schedule_call_end(call_id, delay=5))

                # Get TTS audio
                tts_response = await client.post(
                    f"{self.ai_engine_url}/tts/synthesize",
                    json={
                        "text": ai_text,
                        "language": call["language"]
                    },
                    timeout=30.0
                )

                audio_response = None
                if tts_response.status_code == 200:
                    audio_response = tts_response.content

                return {
                    "borrower_said": borrower_text,
                    "ai_response": ai_text,
                    "action": ai_data.get("action"),
                    "should_end": ai_data.get("should_end", False),
                    "audio": audio_response
                }

        except Exception as e:
            print(f"Error processing speech for call {call_id}: {e}")
            return None

    async def _schedule_call_end(self, call_id: str, delay: int = 5):
        """Schedule call end after a delay."""
        await asyncio.sleep(delay)
        if call_id in self.active_calls:
            await self.end_call(call_id)

    async def _finalize_call(self, call_id: str):
        """Finalize call and send data to backend."""
        call = self.active_calls.get(call_id)
        if not call:
            return

        try:
            # Get call summary from AI
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

            # Send to backend
            await self._notify_backend_call_complete(call_id)

        except Exception as e:
            print(f"Error finalizing call {call_id}: {e}")

    def _determine_outcome(self, call: Dict[str, Any]) -> str:
        """Determine call outcome based on conversation."""
        if call["status"] == "no-answer":
            return "no_answer"
        elif call["status"] == "busy":
            return "busy"
        elif call["duration"] < 10:
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

    async def _notify_backend_call_complete(self, call_id: str):
        """Notify backend that call is complete."""
        call = self.active_calls.get(call_id)
        if not call:
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.backend_url}/api/v1/telephony/webhook/call-status",
                    json={
                        "type": "call_complete",
                        "call_sid": call_id,
                        "CallSid": call_id,
                        "status": call["status"],
                        "Status": call["status"],
                        "duration": call["duration"],
                        "recording_url": call.get("recording_url"),
                        "borrower_id": call["borrower_id"],
                        "case_id": call["case_id"],
                        "campaign_id": call.get("campaign_id"),
                        "outcome": call["outcome"],
                        "transcript": call.get("conversation_history"),
                        "summary": call.get("summary"),
                        "entities": call.get("entities_extracted")
                    },
                    timeout=10.0
                )
        except Exception as e:
            print(f"Failed to notify backend for call {call_id}: {e}")

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
            await self.provider.end_call(provider_call_id)

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
