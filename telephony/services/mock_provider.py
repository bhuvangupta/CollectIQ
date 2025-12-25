"""Mock telephony provider for development and testing."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import random


class MockTelephonyProvider:
    """Mock implementation of telephony provider (Exotel-like interface)."""

    def __init__(self):
        self.calls: Dict[str, Dict[str, Any]] = {}
        self.sms_messages: Dict[str, Dict[str, Any]] = {}
        self.whatsapp_messages: Dict[str, Dict[str, Any]] = {}

        # Simulated response delays
        self.min_delay = 0.1
        self.max_delay = 0.5

    async def initiate_call(
        self,
        from_number: str,
        to_number: str,
        callback_url: Optional[str] = None,
        custom_field: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate an outbound call."""
        await self._simulate_delay()

        call_id = f"call_{uuid.uuid4().hex[:12]}"

        call_data = {
            "call_id": call_id,
            "sid": call_id,
            "from": from_number,
            "to": to_number,
            "direction": "outbound",
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "callback_url": callback_url,
            "custom_field": custom_field,
            "price": 0.0,
            "duration": 0,
            "recording_url": None
        }

        self.calls[call_id] = call_data

        # Simulate call progression asynchronously
        asyncio.create_task(self._simulate_call_progression(call_id))

        return call_data

    async def _simulate_call_progression(self, call_id: str):
        """Simulate call state changes."""
        if call_id not in self.calls:
            return

        call = self.calls[call_id]

        # Queued -> Ringing
        await asyncio.sleep(random.uniform(0.5, 1.5))
        if call_id in self.calls:
            self.calls[call_id]["status"] = "ringing"

        # Ringing -> Answered (80% chance) or No Answer
        await asyncio.sleep(random.uniform(1.0, 3.0))
        if call_id in self.calls:
            if random.random() < 0.8:
                self.calls[call_id]["status"] = "in-progress"
                self.calls[call_id]["answered_at"] = datetime.utcnow().isoformat()

                # Simulate call duration
                duration = random.randint(30, 180)  # 30 seconds to 3 minutes
                await asyncio.sleep(min(duration / 10, 5))  # Speed up simulation

                if call_id in self.calls:
                    self.calls[call_id]["status"] = "completed"
                    self.calls[call_id]["duration"] = duration
                    self.calls[call_id]["ended_at"] = datetime.utcnow().isoformat()
                    self.calls[call_id]["recording_url"] = f"/mock/recordings/{call_id}.wav"
                    self.calls[call_id]["price"] = round(duration * 0.02, 2)  # Mock pricing
            else:
                self.calls[call_id]["status"] = "no-answer"
                self.calls[call_id]["ended_at"] = datetime.utcnow().isoformat()

    async def get_call_status(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a call."""
        return self.calls.get(call_id)

    async def end_call(self, call_id: str) -> Dict[str, Any]:
        """End an active call."""
        if call_id not in self.calls:
            raise ValueError(f"Call {call_id} not found")

        call = self.calls[call_id]
        if call["status"] in ["completed", "failed", "no-answer", "busy"]:
            raise ValueError(f"Call {call_id} already ended")

        # Calculate duration
        if call.get("answered_at"):
            started = datetime.fromisoformat(call["answered_at"])
            duration = int((datetime.utcnow() - started).total_seconds())
        else:
            duration = 0

        self.calls[call_id].update({
            "status": "completed",
            "ended_at": datetime.utcnow().isoformat(),
            "duration": duration,
            "recording_url": f"/mock/recordings/{call_id}.wav" if duration > 0 else None
        })

        return self.calls[call_id]

    async def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_id: str = "LNCOLL"
    ) -> str:
        """Send an SMS message."""
        await self._simulate_delay()

        message_id = f"sms_{uuid.uuid4().hex[:12]}"

        sms_data = {
            "message_id": message_id,
            "to": phone_number,
            "from": sender_id,
            "body": message,
            "status": "sent",
            "created_at": datetime.utcnow().isoformat(),
            "delivered_at": None,
            "price": 0.25  # Mock price per SMS
        }

        self.sms_messages[message_id] = sms_data

        # Simulate delivery
        asyncio.create_task(self._simulate_sms_delivery(message_id))

        return message_id

    async def _simulate_sms_delivery(self, message_id: str):
        """Simulate SMS delivery."""
        await asyncio.sleep(random.uniform(1.0, 5.0))

        if message_id in self.sms_messages:
            # 95% delivery success rate
            if random.random() < 0.95:
                self.sms_messages[message_id]["status"] = "delivered"
                self.sms_messages[message_id]["delivered_at"] = datetime.utcnow().isoformat()
            else:
                self.sms_messages[message_id]["status"] = "failed"

    async def get_sms_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get SMS delivery status."""
        return self.sms_messages.get(message_id)

    async def send_whatsapp(
        self,
        phone_number: str,
        message: str,
        template_name: Optional[str] = None,
        template_params: Optional[Dict[str, str]] = None
    ) -> str:
        """Send a WhatsApp message."""
        await self._simulate_delay()

        message_id = f"wa_{uuid.uuid4().hex[:12]}"

        wa_data = {
            "message_id": message_id,
            "to": phone_number,
            "body": message,
            "template_name": template_name,
            "template_params": template_params,
            "status": "sent",
            "created_at": datetime.utcnow().isoformat(),
            "delivered_at": None,
            "read_at": None,
            "price": 0.50  # Mock price per WhatsApp message
        }

        self.whatsapp_messages[message_id] = wa_data

        # Simulate delivery and read
        asyncio.create_task(self._simulate_whatsapp_delivery(message_id))

        return message_id

    async def _simulate_whatsapp_delivery(self, message_id: str):
        """Simulate WhatsApp delivery and read status."""
        # Delivery
        await asyncio.sleep(random.uniform(0.5, 2.0))
        if message_id in self.whatsapp_messages:
            if random.random() < 0.98:  # 98% delivery rate
                self.whatsapp_messages[message_id]["status"] = "delivered"
                self.whatsapp_messages[message_id]["delivered_at"] = datetime.utcnow().isoformat()

                # Read status (70% read rate)
                await asyncio.sleep(random.uniform(2.0, 10.0))
                if message_id in self.whatsapp_messages and random.random() < 0.7:
                    self.whatsapp_messages[message_id]["status"] = "read"
                    self.whatsapp_messages[message_id]["read_at"] = datetime.utcnow().isoformat()
            else:
                self.whatsapp_messages[message_id]["status"] = "failed"

    async def get_whatsapp_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get WhatsApp message status."""
        return self.whatsapp_messages.get(message_id)

    async def get_account_balance(self) -> Dict[str, Any]:
        """Get mock account balance."""
        return {
            "balance": 10000.00,
            "currency": "INR",
            "credit_limit": 50000.00
        }

    async def get_call_recording(self, call_id: str) -> Optional[bytes]:
        """Get call recording (mock returns empty audio)."""
        if call_id not in self.calls:
            return None

        call = self.calls[call_id]
        if not call.get("recording_url"):
            return None

        # Return mock WAV file
        return self._generate_mock_audio()

    def _generate_mock_audio(self) -> bytes:
        """Generate mock WAV audio data."""
        import struct

        sample_rate = 8000
        duration = 1
        num_samples = sample_rate * duration

        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + num_samples * 2,
            b'WAVE',
            b'fmt ',
            16,
            1,
            1,
            sample_rate,
            sample_rate * 2,
            2,
            16,
            b'data',
            num_samples * 2
        )

        return wav_header + b'\x00' * (num_samples * 2)

    async def _simulate_delay(self):
        """Simulate network delay."""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

    def get_statistics(self) -> Dict[str, Any]:
        """Get mock provider statistics."""
        total_calls = len(self.calls)
        completed_calls = sum(1 for c in self.calls.values() if c["status"] == "completed")
        total_duration = sum(c.get("duration", 0) for c in self.calls.values())

        total_sms = len(self.sms_messages)
        delivered_sms = sum(1 for s in self.sms_messages.values() if s["status"] == "delivered")

        total_wa = len(self.whatsapp_messages)
        delivered_wa = sum(1 for w in self.whatsapp_messages.values() if w["status"] in ["delivered", "read"])

        return {
            "calls": {
                "total": total_calls,
                "completed": completed_calls,
                "total_duration_seconds": total_duration,
                "average_duration": total_duration / completed_calls if completed_calls > 0 else 0
            },
            "sms": {
                "total": total_sms,
                "delivered": delivered_sms,
                "delivery_rate": delivered_sms / total_sms if total_sms > 0 else 0
            },
            "whatsapp": {
                "total": total_wa,
                "delivered": delivered_wa,
                "delivery_rate": delivered_wa / total_wa if total_wa > 0 else 0
            }
        }
