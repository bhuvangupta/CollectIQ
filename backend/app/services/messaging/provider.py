"""Messaging provider for SMS and WhatsApp.

Supports:
- Gupshup for both SMS and WhatsApp (recommended - single provider)
- Exotel for SMS (fallback)
"""

import os
import base64
import httpx
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MessageResult:
    """Result of sending a message."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    status: str = "queued"


class MessagingProvider:
    """Unified messaging provider for SMS and WhatsApp via Gupshup."""

    def __init__(self):
        # Gupshup config (for SMS and WhatsApp)
        self.gupshup_api_key = os.getenv("GUPSHUP_API_KEY")
        self.gupshup_app_name = os.getenv("GUPSHUP_APP_NAME")
        self.gupshup_source_number = os.getenv("GUPSHUP_SOURCE_NUMBER")

        # SMS provider preference: gupshup or exotel
        self.sms_provider = os.getenv("SMS_PROVIDER", "gupshup").lower()

        # Exotel config (fallback for SMS)
        self.exotel_api_key = os.getenv("EXOTEL_API_KEY")
        self.exotel_api_token = os.getenv("EXOTEL_API_TOKEN")
        self.exotel_sid = os.getenv("EXOTEL_SID")
        self.exotel_subdomain = os.getenv("EXOTEL_SUBDOMAIN", "api")
        self.exotel_sender_id = os.getenv("EXOTEL_SMS_SENDER_ID", "LNCOLL")

        # Build Exotel auth
        if self.exotel_api_key and self.exotel_api_token:
            credentials = f"{self.exotel_api_key}:{self.exotel_api_token}"
            self.exotel_auth = base64.b64encode(credentials.encode()).decode()
        else:
            self.exotel_auth = None

    @property
    def gupshup_available(self) -> bool:
        """Check if Gupshup is configured."""
        return all([self.gupshup_api_key, self.gupshup_app_name])

    @property
    def sms_available(self) -> bool:
        """Check if SMS is configured (Gupshup or Exotel)."""
        if self.sms_provider == "gupshup":
            return self.gupshup_available
        return all([self.exotel_api_key, self.exotel_api_token, self.exotel_sid])

    @property
    def whatsapp_available(self) -> bool:
        """Check if WhatsApp is configured."""
        return all([self.gupshup_api_key, self.gupshup_app_name, self.gupshup_source_number])

    async def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_id: Optional[str] = None
    ) -> MessageResult:
        """Send SMS via Gupshup (default) or Exotel.

        Args:
            phone_number: Recipient phone (with country code)
            message: SMS text
            sender_id: Sender ID (for Exotel)

        Returns:
            MessageResult with status
        """
        if not self.sms_available:
            return MessageResult(
                success=False,
                error="SMS not configured. Set GUPSHUP_API_KEY or EXOTEL credentials"
            )

        # Use Gupshup for SMS (default)
        if self.sms_provider == "gupshup" and self.gupshup_available:
            return await self._send_sms_gupshup(phone_number, message)
        else:
            return await self._send_sms_exotel(phone_number, message, sender_id)

    async def _send_sms_gupshup(self, phone_number: str, message: str) -> MessageResult:
        """Send SMS via Gupshup."""
        phone = self._format_phone(phone_number).replace("+", "")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://enterprise.smsgupshup.com/GatewayAPI/rest",
                    data={
                        "method": "SendMessage",
                        "send_to": phone,
                        "msg": message,
                        "msg_type": "TEXT",
                        "userid": self.gupshup_app_name,
                        "auth_scheme": "plain",
                        "password": self.gupshup_api_key,
                        "v": "1.1",
                        "format": "json"
                    },
                    timeout=30.0
                )

                if response.status_code not in [200, 201]:
                    print(f"[SMS] Gupshup error: {response.text}")
                    return MessageResult(
                        success=False,
                        error=f"Gupshup error: {response.text}"
                    )

                result = response.json()

                if result.get("response", {}).get("status") == "success":
                    return MessageResult(
                        success=True,
                        message_id=result.get("response", {}).get("id"),
                        status="sent"
                    )
                else:
                    return MessageResult(
                        success=False,
                        error=result.get("response", {}).get("details", "Unknown error")
                    )

        except Exception as e:
            print(f"[SMS] Gupshup error: {e}")
            return MessageResult(success=False, error=str(e))

    async def _send_sms_exotel(
        self,
        phone_number: str,
        message: str,
        sender_id: Optional[str] = None
    ) -> MessageResult:
        """Send SMS via Exotel (fallback)."""
        sender_id = sender_id or self.exotel_sender_id
        phone = self._format_phone(phone_number)

        data = {
            "From": sender_id,
            "To": phone,
            "Body": message,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{self.exotel_subdomain}.exotel.com/v1/Accounts/{self.exotel_sid}/Sms/send.json",
                    headers={
                        "Authorization": f"Basic {self.exotel_auth}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data=data,
                    timeout=30.0
                )

                if response.status_code not in [200, 201]:
                    print(f"[SMS] Exotel error: {response.text}")
                    return MessageResult(
                        success=False,
                        error=f"Exotel error: {response.text}"
                    )

                result = response.json()
                sms_data = result.get("SMSMessage", {})

                return MessageResult(
                    success=True,
                    message_id=sms_data.get("Sid"),
                    status=sms_data.get("Status", "queued")
                )

        except Exception as e:
            print(f"[SMS] Exotel error: {e}")
            return MessageResult(success=False, error=str(e))

    async def send_whatsapp(
        self,
        phone_number: str,
        message: str,
        template_id: Optional[str] = None,
        template_params: Optional[Dict[str, str]] = None
    ) -> MessageResult:
        """Send WhatsApp message via Gupshup.

        Args:
            phone_number: Recipient phone (with country code)
            message: Message text (for session messages)
            template_id: WhatsApp template ID (for template messages)
            template_params: Template parameters

        Returns:
            MessageResult with status
        """
        if not self.whatsapp_available:
            return MessageResult(
                success=False,
                error="Gupshup WhatsApp not configured. Set GUPSHUP_API_KEY, GUPSHUP_APP_NAME, GUPSHUP_SOURCE_NUMBER"
            )

        phone = self._format_phone(phone_number)

        try:
            async with httpx.AsyncClient() as client:
                if template_id:
                    # Template message (for business-initiated conversations)
                    payload = {
                        "channel": "whatsapp",
                        "source": self.gupshup_source_number,
                        "destination": phone,
                        "template": {
                            "id": template_id,
                            "params": list(template_params.values()) if template_params else []
                        }
                    }
                    endpoint = "https://api.gupshup.io/wa/api/v1/template/msg"
                else:
                    # Session message (within 24-hour window)
                    payload = {
                        "channel": "whatsapp",
                        "source": self.gupshup_source_number,
                        "destination": phone,
                        "message": {
                            "type": "text",
                            "text": message
                        }
                    }
                    endpoint = "https://api.gupshup.io/wa/api/v1/msg"

                response = await client.post(
                    endpoint,
                    headers={
                        "apikey": self.gupshup_api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30.0
                )

                if response.status_code not in [200, 201, 202]:
                    print(f"[WhatsApp] Gupshup error: {response.text}")
                    return MessageResult(
                        success=False,
                        error=f"Gupshup error: {response.text}"
                    )

                result = response.json()

                return MessageResult(
                    success=True,
                    message_id=result.get("messageId"),
                    status="sent"
                )

        except Exception as e:
            print(f"[WhatsApp] Error: {e}")
            return MessageResult(success=False, error=str(e))

    async def get_sms_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get SMS delivery status from Exotel."""
        if not self.sms_available:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{self.exotel_subdomain}.exotel.com/v1/Accounts/{self.exotel_sid}/SMS/Messages/{message_id}.json",
                    headers={"Authorization": f"Basic {self.exotel_auth}"},
                    timeout=30.0
                )

                if response.status_code != 200:
                    return None

                result = response.json()
                return result.get("SMSMessage", {})

        except Exception as e:
            print(f"[SMS] Status check error: {e}")
            return None

    def _format_phone(self, phone: str) -> str:
        """Format phone number to E.164 format."""
        phone = "".join(c for c in phone if c.isdigit() or c == "+")

        if not phone.startswith("+"):
            if phone.startswith("91") and len(phone) == 12:
                phone = "+" + phone
            elif len(phone) == 10:
                phone = "+91" + phone
            else:
                phone = "+" + phone

        return phone


# Singleton instance
_provider_instance: Optional[MessagingProvider] = None


def get_messaging_provider() -> MessagingProvider:
    """Get singleton messaging provider instance."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = MessagingProvider()
    return _provider_instance
