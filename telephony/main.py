"""Mock Telephony Service for AI-Powered Loan Collection Platform."""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from services.factory import get_telephony_provider
from services.call_handler import CallHandler
from services.websocket_manager import ConnectionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    provider_name = os.getenv("TELEPHONY_PROVIDER", "mock")
    print(f"Starting Telephony Service ({provider_name})...")
    yield
    print("Shutting down Telephony Service...")


app = FastAPI(
    title="Mock Telephony Service",
    description="Mock telephony layer for development and testing",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services - uses TELEPHONY_PROVIDER env var (mock/exotel)
telephony_provider = get_telephony_provider()
call_handler = CallHandler(telephony_provider)
ws_manager = ConnectionManager()


# Request/Response Models
class InitiateCallRequest(BaseModel):
    """Request to initiate an outbound call."""
    phone_number: Optional[str] = None
    to_number: Optional[str] = None  # Alias for phone_number (from campaign tasks)
    caller_id: str = "+911234567890"
    borrower_id: Optional[str] = None
    case_id: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_borrower_id: Optional[str] = None
    language: str = "hi"
    callback_url: Optional[str] = None
    use_ai: bool = False  # Whether to use AI voice pipeline

    # Borrower context for AI (optional, fetched from backend if not provided)
    borrower_name: Optional[str] = None
    outstanding_amount: Optional[float] = None
    emi_amount: Optional[float] = None
    dpd: Optional[int] = None
    loan_type: Optional[str] = None

    @property
    def target_phone(self) -> str:
        """Get the target phone number from either field."""
        return self.phone_number or self.to_number or ""


class CallResponse(BaseModel):
    """Call initiation response."""
    call_id: str
    status: str
    message: str


class SendSMSRequest(BaseModel):
    """Request to send SMS."""
    phone_number: str
    message: str
    sender_id: str = "LNCOLL"
    borrower_id: str
    case_id: str
    template_id: Optional[str] = None


class SMSResponse(BaseModel):
    """SMS send response."""
    message_id: str
    status: str
    message: str


class SendWhatsAppRequest(BaseModel):
    """Request to send WhatsApp message."""
    phone_number: str
    message: str
    borrower_id: str
    case_id: str
    template_name: Optional[str] = None
    template_params: Optional[Dict[str, str]] = None


class WhatsAppResponse(BaseModel):
    """WhatsApp send response."""
    message_id: str
    status: str
    message: str


class CallStatusUpdate(BaseModel):
    """Call status update from webhook."""
    call_id: str
    status: str
    duration: Optional[int] = None
    recording_url: Optional[str] = None
    digits: Optional[str] = None
    transcript: Optional[str] = None


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "telephony"}


@app.post("/calls/initiate", response_model=CallResponse)
async def initiate_call(request: InitiateCallRequest):
    """Initiate an outbound call."""
    phone = request.target_phone
    if not phone:
        raise HTTPException(status_code=400, detail="phone_number or to_number required")

    try:
        # Build AI context if use_ai is enabled
        ai_context = None
        if request.use_ai:
            ai_context = {
                "borrower_name": request.borrower_name or "Customer",
                "outstanding_amount": request.outstanding_amount or 0,
                "emi_amount": request.emi_amount or 0,
                "dpd": request.dpd or 0,
                "loan_type": request.loan_type or "Loan",
                "language": request.language
            }

        call_id = await call_handler.initiate_call(
            phone_number=phone,
            caller_id=request.caller_id,
            borrower_id=request.borrower_id or "",
            case_id=request.case_id or "",
            campaign_id=request.campaign_id,
            campaign_borrower_id=request.campaign_borrower_id,
            language=request.language,
            callback_url=request.callback_url,
            use_ai=request.use_ai,
            ai_context=ai_context
        )

        # Notify connected clients
        await ws_manager.broadcast({
            "type": "call_initiated",
            "call_id": call_id,
            "phone_number": phone,
            "borrower_id": request.borrower_id,
            "case_id": request.case_id,
            "use_ai": request.use_ai
        })

        return CallResponse(
            call_id=call_id,
            status="initiated",
            message="Call initiated successfully" + (" with AI" if request.use_ai else "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calls/{call_id}")
async def get_call_status(call_id: str):
    """Get current call status."""
    call = call_handler.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@app.post("/calls/{call_id}/end")
async def end_call(call_id: str):
    """End an active call."""
    try:
        result = await call_handler.end_call(call_id)

        # Notify connected clients
        await ws_manager.broadcast({
            "type": "call_ended",
            "call_id": call_id,
            **result
        })

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/calls/{call_id}/dtmf")
async def send_dtmf(call_id: str, digits: str):
    """Send DTMF tones to a call."""
    try:
        result = await call_handler.send_dtmf(call_id, digits)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/sms/send", response_model=SMSResponse)
async def send_sms(request: SendSMSRequest):
    """Send an SMS message."""
    try:
        message_id = await telephony_provider.send_sms(
            phone_number=request.phone_number,
            message=request.message,
            sender_id=request.sender_id
        )

        # Notify backend about SMS
        await _notify_backend({
            "type": "sms",
            "message_id": message_id,
            "phone_number": request.phone_number,
            "borrower_id": request.borrower_id,
            "case_id": request.case_id,
            "status": "sent"
        })

        return SMSResponse(
            message_id=message_id,
            status="sent",
            message="SMS sent successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/whatsapp/send", response_model=WhatsAppResponse)
async def send_whatsapp(request: SendWhatsAppRequest):
    """Send a WhatsApp message."""
    try:
        message_id = await telephony_provider.send_whatsapp(
            phone_number=request.phone_number,
            message=request.message,
            template_name=request.template_name,
            template_params=request.template_params
        )

        # Notify backend
        await _notify_backend({
            "type": "whatsapp",
            "message_id": message_id,
            "phone_number": request.phone_number,
            "borrower_id": request.borrower_id,
            "case_id": request.case_id,
            "status": "sent"
        })

        return WhatsAppResponse(
            message_id=message_id,
            status="sent",
            message="WhatsApp message sent successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/call-status")
async def call_status_webhook(update: CallStatusUpdate):
    """Handle call status updates (from Exotel in production)."""
    call = call_handler.get_call(update.call_id)
    if call:
        call_handler.update_call_status(
            call_id=update.call_id,
            status=update.status,
            duration=update.duration,
            recording_url=update.recording_url
        )

        # Notify connected clients
        await ws_manager.broadcast({
            "type": "call_status_update",
            **update.model_dump()
        })

        # Notify backend
        await _notify_backend({
            "type": "call_status",
            **update.model_dump(),
            "borrower_id": call.get("borrower_id"),
            "case_id": call.get("case_id")
        })

    return {"status": "received"}


@app.post("/webhooks/sms-status")
async def sms_status_webhook(data: Dict[str, Any]):
    """Handle SMS delivery status updates."""
    await ws_manager.broadcast({
        "type": "sms_status_update",
        **data
    })
    return {"status": "received"}


@app.post("/webhooks/exotel/status")
async def exotel_status_webhook(request: Request):
    """Handle Exotel call status webhooks.

    Exotel sends these parameters:
    - CallSid: Unique call identifier
    - Status: queued, ringing, in-progress, completed, busy, failed, no-answer
    - From: Caller number
    - To: Called number
    - Direction: inbound/outbound
    - Duration: Call duration in seconds
    - RecordingUrl: URL to call recording
    - CustomField: Custom data we sent
    """
    # Parse form data (Exotel sends as form-urlencoded)
    form_data = await request.form()
    data = dict(form_data)

    # Also try JSON body
    if not data:
        try:
            data = await request.json()
        except Exception:
            pass

    print(f"[Exotel Webhook] Received: {data}")

    # Parse using provider if available
    if hasattr(telephony_provider, 'parse_webhook'):
        normalized = telephony_provider.parse_webhook(data)
    else:
        normalized = {
            "call_id": data.get("CallSid"),
            "status": data.get("Status", "").lower(),
            "duration": int(data.get("Duration", 0)),
            "recording_url": data.get("RecordingUrl"),
            "custom_field": data.get("CustomField"),
        }

    call_id = normalized.get("call_id")
    if call_id:
        call = call_handler.get_call(call_id)
        if call:
            call_handler.update_call_status(
                call_id=call_id,
                status=normalized.get("status"),
                duration=normalized.get("duration"),
                recording_url=normalized.get("recording_url")
            )

        # Notify connected clients
        await ws_manager.broadcast({
            "type": "call_status_update",
            **normalized
        })

        # Notify backend
        await _notify_backend({
            "type": "call_status",
            "call_id": call_id,
            "call_sid": call_id,
            "CallSid": call_id,
            "status": normalized.get("status"),
            "Status": normalized.get("status"),
            "duration": normalized.get("duration"),
            "Duration": normalized.get("duration"),
            "recording_url": normalized.get("recording_url"),
            "RecordingUrl": normalized.get("recording_url"),
            "custom_field": normalized.get("custom_field"),
        })

    return {"status": "received"}


@app.post("/webhooks/exotel/passthru")
async def exotel_passthru_webhook(request: Request):
    """Handle Exotel passthru webhooks for real-time call control.

    Exotel Passthru sends these for IVR/real-time events:
    - CallSid: Call identifier
    - Direction: inbound/outbound
    - Digits: DTMF input from caller
    - RecordingUrl: Partial recording
    - CallStatus: Current status

    Returns TwiML-like response to control call flow.
    """
    form_data = await request.form()
    data = dict(form_data)

    if not data:
        try:
            data = await request.json()
        except Exception:
            pass

    print(f"[Exotel Passthru] Received: {data}")

    call_id = data.get("CallSid")
    digits = data.get("Digits")
    status = data.get("CallStatus")

    # Handle DTMF input
    if digits:
        await ws_manager.broadcast({
            "type": "dtmf_received",
            "call_id": call_id,
            "digits": digits
        })

    # For now, return empty response (call continues)
    # In future: return TwiML for IVR flows
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            # Handle incoming messages from clients
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "subscribe":
                # Client wants to subscribe to specific call updates
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.websocket("/ws/call/{call_id}")
async def call_websocket(websocket: WebSocket, call_id: str):
    """WebSocket endpoint for a specific call's audio stream."""
    await ws_manager.connect(websocket, call_id)
    try:
        while True:
            # Receive audio data from client (for live call scenarios)
            data = await websocket.receive_bytes()

            # In production, this would:
            # 1. Send audio to STT service
            # 2. Get AI response
            # 3. Send TTS audio back

            # For mock, just acknowledge
            await websocket.send_json({"type": "audio_received", "bytes": len(data)})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


async def _notify_backend(data: Dict[str, Any]):
    """Notify backend service about events."""
    backend_url = os.getenv("BACKEND_URL", "http://backend:8000")

    # Route to correct webhook based on event type
    event_type = data.get("type", "")
    if event_type in ["call_status", "call_complete", "call_initiated"]:
        endpoint = "/api/v1/telephony/webhook/call-status"
        # Add call_sid alias for backend compatibility
        if "call_id" in data:
            data["call_sid"] = data["call_id"]
            data["CallSid"] = data["call_id"]
        if "status" in data:
            data["Status"] = data["status"]
    elif event_type == "sms":
        endpoint = "/api/v1/telephony/webhook/sms-status"
    elif event_type == "whatsapp":
        endpoint = "/api/v1/telephony/webhook/whatsapp-status"
    else:
        endpoint = "/api/v1/telephony/webhook/call-status"

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{backend_url}{endpoint}",
                json=data,
                timeout=10.0
            )
    except Exception as e:
        print(f"Failed to notify backend: {e}")


# Simulation endpoints for testing
@app.post("/simulate/incoming-call")
async def simulate_incoming_call(
    phone_number: str,
    caller_id: str = "+919876543210"
):
    """Simulate an incoming call for testing."""
    call_id = str(uuid.uuid4())

    # Create mock incoming call
    call_handler.active_calls[call_id] = {
        "call_id": call_id,
        "direction": "inbound",
        "phone_number": phone_number,
        "caller_id": caller_id,
        "status": "ringing",
        "started_at": datetime.utcnow().isoformat(),
        "answered_at": None,
        "ended_at": None,
        "duration": 0
    }

    # Notify
    await ws_manager.broadcast({
        "type": "incoming_call",
        "call_id": call_id,
        "phone_number": phone_number,
        "caller_id": caller_id
    })

    return {"call_id": call_id, "status": "ringing"}


@app.post("/simulate/call-answered/{call_id}")
async def simulate_call_answered(call_id: str):
    """Simulate call being answered."""
    if call_id not in call_handler.active_calls:
        raise HTTPException(status_code=404, detail="Call not found")

    call_handler.active_calls[call_id]["status"] = "answered"
    call_handler.active_calls[call_id]["answered_at"] = datetime.utcnow().isoformat()

    await ws_manager.broadcast({
        "type": "call_answered",
        "call_id": call_id
    })

    return {"call_id": call_id, "status": "answered"}


@app.post("/simulate/borrower-response/{call_id}")
async def simulate_borrower_response(call_id: str, response_text: str):
    """Simulate borrower speaking during a call."""
    if call_id not in call_handler.active_calls:
        raise HTTPException(status_code=404, detail="Call not found")

    # This would trigger the AI dialog flow
    ai_engine_url = os.getenv("AI_ENGINE_URL", "http://ai-engine:8001")

    try:
        async with httpx.AsyncClient() as client:
            # Get AI response
            response = await client.post(
                f"{ai_engine_url}/dialog/respond",
                json={
                    "conversation_history": [
                        {"role": "user", "content": response_text}
                    ],
                    "context": {
                        "borrower_name": "Test Borrower",
                        "outstanding_amount": 50000,
                        "dpd": 30,
                        "emi_amount": 5000,
                        "loan_type": "Personal Loan"
                    },
                    "language": "hi"
                },
                timeout=30.0
            )
            ai_response = response.json()

            await ws_manager.broadcast({
                "type": "dialog_exchange",
                "call_id": call_id,
                "borrower_said": response_text,
                "ai_response": ai_response
            })

            return ai_response

    except Exception as e:
        return {"error": str(e), "borrower_said": response_text}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
