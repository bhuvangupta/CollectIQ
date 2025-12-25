"""Exotel telephony provider for production calls in India."""

import os
import base64
import httpx
from datetime import datetime
from typing import Dict, Any, Optional


class ExotelProvider:
    """Direct Exotel API integration for telephony.

    Exotel is India's leading cloud telephony platform.

    API Reference: https://developer.exotel.com/api/

    Features:
    - Outbound and inbound calls
    - SMS messaging
    - Call recording
    - Webhooks for call status

    Authentication: Basic auth with API Key + Token
    """

    def __init__(self):
        self.api_key = os.getenv("EXOTEL_API_KEY")
        self.api_token = os.getenv("EXOTEL_API_TOKEN")
        self.sid = os.getenv("EXOTEL_SID")
        self.subdomain = os.getenv("EXOTEL_SUBDOMAIN", "api")

        if not all([self.api_key, self.api_token, self.sid]):
            raise ValueError(
                "EXOTEL_API_KEY, EXOTEL_API_TOKEN, and EXOTEL_SID are required"
            )

        # Build base URL
        self.base_url = f"https://{self.subdomain}.exotel.com/v1/Accounts/{self.sid}"

        # Build auth header
        credentials = f"{self.api_key}:{self.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Default caller ID (must be verified in Exotel dashboard)
        self.default_caller_id = os.getenv("EXOTEL_CALLER_ID")

        # Webhook URL for status callbacks
        self.webhook_url = os.getenv("EXOTEL_WEBHOOK_URL")

        # Track calls locally
        self.calls: Dict[str, Dict[str, Any]] = {}

    async def initiate_call(
        self,
        from_number: str,
        to_number: str,
        caller_id: Optional[str] = None,
        callback_url: Optional[str] = None,
        custom_field: Optional[str] = None,
        time_limit: int = 300,
        record: bool = True,
    ) -> Dict[str, Any]:
        """Initiate an outbound call via Exotel Connect API.

        Args:
            from_number: Agent phone number (or virtual number)
            to_number: Customer phone number to call
            caller_id: CLI/Caller ID shown to customer
            callback_url: Webhook URL for call status updates
            custom_field: Custom data (case_id, campaign_id, etc.)
            time_limit: Max call duration in seconds
            record: Whether to record the call

        Returns:
            Call data with call_id, status, etc.
        """
        caller_id = caller_id or self.default_caller_id
        callback_url = callback_url or self.webhook_url

        if not caller_id:
            raise ValueError("caller_id is required (set EXOTEL_CALLER_ID)")

        # Prepare form data for Exotel API
        data = {
            "From": from_number,
            "To": to_number,
            "CallerId": caller_id,
            "TimeLimit": str(time_limit),
            "Record": "true" if record else "false",
        }

        if callback_url:
            data["StatusCallback"] = callback_url

        if custom_field:
            data["CustomField"] = custom_field

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/Calls/connect.json",
                    headers=self.headers,
                    data=data,
                    timeout=30.0
                )

                if response.status_code not in [200, 201]:
                    print(f"[Exotel] Error {response.status_code}: {response.text}")
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code
                    }

                result = response.json()
                call_data = result.get("Call", {})

                # Store locally
                call_id = call_data.get("Sid")
                self.calls[call_id] = {
                    "call_id": call_id,
                    "sid": call_id,
                    "from": from_number,
                    "to": to_number,
                    "direction": "outbound",
                    "status": call_data.get("Status", "queued"),
                    "created_at": datetime.utcnow().isoformat(),
                    "callback_url": callback_url,
                    "custom_field": custom_field,
                    "price": 0.0,
                    "duration": 0,
                    "recording_url": None,
                }

                return {
                    "success": True,
                    "call_id": call_id,
                    "sid": call_id,
                    "status": call_data.get("Status", "queued"),
                    "from": from_number,
                    "to": to_number,
                }

        except Exception as e:
            print(f"[Exotel] Call initiation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_call_status(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a call from Exotel.

        Args:
            call_id: Exotel call SID

        Returns:
            Call details or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/Calls/{call_id}.json",
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code == 404:
                    return None

                if response.status_code != 200:
                    print(f"[Exotel] Error getting call {call_id}: {response.text}")
                    return self.calls.get(call_id)

                result = response.json()
                call_data = result.get("Call", {})

                return {
                    "call_id": call_id,
                    "sid": call_id,
                    "status": call_data.get("Status"),
                    "direction": call_data.get("Direction"),
                    "from": call_data.get("From"),
                    "to": call_data.get("To"),
                    "duration": call_data.get("Duration"),
                    "recording_url": call_data.get("RecordingUrl"),
                    "price": call_data.get("Price"),
                    "start_time": call_data.get("StartTime"),
                    "end_time": call_data.get("EndTime"),
                }

        except Exception as e:
            print(f"[Exotel] Error getting call status: {e}")
            return self.calls.get(call_id)

    async def end_call(self, call_id: str) -> Dict[str, Any]:
        """Hangup an active call.

        Args:
            call_id: Exotel call SID

        Returns:
            Updated call status
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/Calls/{call_id}.json",
                    headers=self.headers,
                    data={"Status": "completed"},
                    timeout=30.0
                )

                if response.status_code != 200:
                    print(f"[Exotel] Error ending call: {response.text}")
                    raise ValueError(f"Failed to end call: {response.text}")

                result = response.json()
                return result.get("Call", {})

        except Exception as e:
            print(f"[Exotel] Error ending call: {e}")
            raise

    async def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_id: str = None,
    ) -> str:
        """Send an SMS via Exotel.

        Args:
            phone_number: Recipient phone number
            message: SMS message body
            sender_id: Sender ID (must be approved in Exotel)

        Returns:
            Message SID
        """
        sender_id = sender_id or os.getenv("EXOTEL_SMS_SENDER_ID", "LNCOLL")

        data = {
            "From": sender_id,
            "To": phone_number,
            "Body": message,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/Sms/send.json",
                    headers=self.headers,
                    data=data,
                    timeout=30.0
                )

                if response.status_code not in [200, 201]:
                    print(f"[Exotel] SMS error: {response.text}")
                    raise ValueError(f"SMS failed: {response.text}")

                result = response.json()
                return result.get("SMSMessage", {}).get("Sid", "")

        except Exception as e:
            print(f"[Exotel] SMS error: {e}")
            raise

    async def get_sms_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get SMS delivery status.

        Args:
            message_id: SMS SID

        Returns:
            SMS status details
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/SMS/Messages/{message_id}.json",
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code != 200:
                    return None

                result = response.json()
                return result.get("SMSMessage", {})

        except Exception as e:
            print(f"[Exotel] Error getting SMS status: {e}")
            return None

    async def get_call_recording(self, call_id: str) -> Optional[bytes]:
        """Download call recording.

        Args:
            call_id: Call SID

        Returns:
            Recording audio bytes or None
        """
        try:
            # First get the recording URL
            call_status = await self.get_call_status(call_id)
            if not call_status:
                return None

            recording_url = call_status.get("recording_url")
            if not recording_url:
                return None

            # Download the recording
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    recording_url,
                    headers=self.headers,
                    timeout=60.0
                )

                if response.status_code == 200:
                    return response.content

                return None

        except Exception as e:
            print(f"[Exotel] Error downloading recording: {e}")
            return None

    async def get_account_balance(self) -> Dict[str, Any]:
        """Get Exotel account balance.

        Returns:
            Balance info
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}.json",
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    account = result.get("Account", {})
                    return {
                        "balance": float(account.get("Balance", 0)),
                        "currency": "INR",
                        "status": account.get("Status"),
                    }

                return {"balance": 0, "currency": "INR", "error": response.text}

        except Exception as e:
            print(f"[Exotel] Error getting balance: {e}")
            return {"balance": 0, "currency": "INR", "error": str(e)}

    def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Exotel webhook payload to standard format.

        Exotel sends webhooks for call status changes.

        Args:
            payload: Raw webhook payload

        Returns:
            Standardized call status dict
        """
        return {
            "call_id": payload.get("CallSid"),
            "status": self._normalize_status(payload.get("Status")),
            "direction": payload.get("Direction"),
            "from": payload.get("From"),
            "to": payload.get("To"),
            "duration": int(payload.get("Duration", 0)),
            "recording_url": payload.get("RecordingUrl"),
            "digits": payload.get("Digits"),  # DTMF input
            "custom_field": payload.get("CustomField"),
            "start_time": payload.get("StartTime"),
            "end_time": payload.get("EndTime"),
        }

    def _normalize_status(self, exotel_status: str) -> str:
        """Normalize Exotel status to internal status.

        Args:
            exotel_status: Exotel's status string

        Returns:
            Normalized status
        """
        status_map = {
            "queued": "queued",
            "ringing": "ringing",
            "in-progress": "in_progress",
            "completed": "completed",
            "busy": "busy",
            "failed": "failed",
            "no-answer": "no_answer",
            "canceled": "cancelled",
        }
        return status_map.get(exotel_status.lower(), exotel_status.lower())

    def get_statistics(self) -> Dict[str, Any]:
        """Get local call statistics.

        Returns:
            Statistics dict
        """
        total_calls = len(self.calls)
        completed = sum(1 for c in self.calls.values() if c.get("status") == "completed")
        total_duration = sum(c.get("duration", 0) for c in self.calls.values())

        return {
            "calls": {
                "total": total_calls,
                "completed": completed,
                "total_duration_seconds": total_duration,
            }
        }
