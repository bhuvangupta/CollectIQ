from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.communication import Communication, CallRecording
from app.models.case import Case
from app.models.borrower import Borrower
from app.services.telephony import get_telephony_provider, CallHandler, get_ws_manager

router = APIRouter()

# Initialize services lazily
_call_handler = None


def get_call_handler() -> CallHandler:
    """Get or create the call handler singleton."""
    global _call_handler
    if _call_handler is None:
        provider = get_telephony_provider()
        _call_handler = CallHandler(provider)
    return _call_handler


# Request/Response Models
class InitiateCallRequest(BaseModel):
    """Request to initiate an outbound call."""
    phone_number: Optional[str] = None
    to_number: Optional[str] = None  # Alias for phone_number
    caller_id: str = Field(default="+911234567890")
    borrower_id: Optional[str] = None
    case_id: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_borrower_id: Optional[str] = None
    language: str = "hi"
    use_ai: bool = False

    # Borrower context for AI
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
    borrower_id: Optional[str] = None
    case_id: Optional[str] = None
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
    borrower_id: Optional[str] = None
    case_id: Optional[str] = None
    template_name: Optional[str] = None
    template_params: Optional[Dict[str, str]] = None


class WhatsAppResponse(BaseModel):
    """WhatsApp send response."""
    message_id: str
    status: str
    message: str


# =============================================================================
# Call Initiation Endpoints
# =============================================================================

@router.post("/calls/initiate", response_model=CallResponse)
async def initiate_call(
    request: InitiateCallRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiate an outbound call.

    This endpoint directly initiates a call using the configured telephony provider
    (mock for development, Exotel for production).
    """
    phone = request.target_phone
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_number or to_number required"
        )

    call_handler = get_call_handler()
    ws_manager = get_ws_manager()

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

        # Create Communication record in database
        comm = Communication(
            organization_id=current_user.organization_id,
            borrower_id=UUID(request.borrower_id) if request.borrower_id else None,
            case_id=UUID(request.case_id) if request.case_id else None,
            campaign_id=UUID(request.campaign_id) if request.campaign_id else None,
            agent_id=current_user.id,
            channel="voice",
            direction="outbound",
            phone_number=phone,
            status="initiating",
            is_ai_handled=request.use_ai
        )
        db.add(comm)
        await db.flush()

        # Initiate call
        call_id = await call_handler.initiate_call(
            phone_number=phone,
            caller_id=request.caller_id,
            borrower_id=request.borrower_id or "",
            case_id=request.case_id or "",
            campaign_id=request.campaign_id,
            campaign_borrower_id=request.campaign_borrower_id,
            language=request.language,
            use_ai=request.use_ai,
            ai_context=ai_context
        )

        # Update communication with call_sid
        comm.call_sid = call_id
        comm.status = "ringing"
        await db.commit()

        # Notify connected WebSocket clients
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/calls/active")
async def get_active_calls(
    current_user: User = Depends(get_current_user)
):
    """Get all active calls."""
    call_handler = get_call_handler()
    return {
        "active_calls": call_handler.get_active_calls(),
        "stats": call_handler.get_call_stats()
    }


@router.get("/calls/{call_id}")
async def get_call_by_id(
    call_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get call details by ID."""
    call_handler = get_call_handler()
    call = call_handler.get_call(call_id)

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    return call


@router.post("/calls/{call_id}/end")
async def end_call_by_id(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """End an active call."""
    call_handler = get_call_handler()
    ws_manager = get_ws_manager()

    try:
        result = await call_handler.end_call(call_id)

        # Update database
        db_result = await db.execute(
            select(Communication).where(Communication.call_sid == call_id)
        )
        comm = db_result.scalar_one_or_none()
        if comm:
            comm.status = "completed"
            comm.ended_at = datetime.utcnow()
            comm.duration_seconds = result.get("duration", 0)
            await db.commit()

        # Notify WebSocket clients
        await ws_manager.broadcast({
            "type": "call_ended",
            "call_id": call_id,
            **result
        })

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/sms/send", response_model=SMSResponse)
async def send_sms(
    request: SendSMSRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send an SMS message."""
    provider = get_telephony_provider()

    try:
        message_id = await provider.send_sms(
            phone_number=request.phone_number,
            message=request.message,
            sender_id=request.sender_id
        )

        # Create Communication record
        comm = Communication(
            organization_id=current_user.organization_id,
            borrower_id=UUID(request.borrower_id) if request.borrower_id else None,
            case_id=UUID(request.case_id) if request.case_id else None,
            agent_id=current_user.id,
            channel="sms",
            direction="outbound",
            phone_number=request.phone_number,
            content=request.message,
            status="sent",
            call_sid=message_id  # Store message_id in call_sid for tracking
        )
        db.add(comm)
        await db.commit()

        return SMSResponse(
            message_id=message_id,
            status="sent",
            message="SMS sent successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/whatsapp/send", response_model=WhatsAppResponse)
async def send_whatsapp(
    request: SendWhatsAppRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a WhatsApp message."""
    provider = get_telephony_provider()

    try:
        message_id = await provider.send_whatsapp(
            phone_number=request.phone_number,
            message=request.message,
            template_name=request.template_name,
            template_params=request.template_params
        )

        # Create Communication record
        comm = Communication(
            organization_id=current_user.organization_id,
            borrower_id=UUID(request.borrower_id) if request.borrower_id else None,
            case_id=UUID(request.case_id) if request.case_id else None,
            agent_id=current_user.id,
            channel="whatsapp",
            direction="outbound",
            phone_number=request.phone_number,
            content=request.message,
            status="sent",
            call_sid=message_id
        )
        db.add(comm)
        await db.commit()

        return WhatsAppResponse(
            message_id=message_id,
            status="sent",
            message="WhatsApp message sent successfully"
        )

    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/provider/stats")
async def get_provider_stats(
    current_user: User = Depends(get_current_user)
):
    """Get telephony provider statistics."""
    provider = get_telephony_provider()
    return provider.get_statistics()


@router.get("/provider/balance")
async def get_provider_balance(
    current_user: User = Depends(get_current_user)
):
    """Get telephony provider account balance."""
    provider = get_telephony_provider()
    return await provider.get_account_balance()


# =============================================================================
# Exotel Webhooks (for direct integration)
# =============================================================================

@router.post("/webhook/exotel/status")
async def exotel_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
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

    call_handler = get_call_handler()
    ws_manager = get_ws_manager()
    provider = get_telephony_provider()

    # Parse using provider if available
    if hasattr(provider, 'parse_webhook'):
        normalized = provider.parse_webhook(data)
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
        # Update call handler
        call = call_handler.get_call(call_id)
        if call:
            call_handler.update_call_status(
                call_id=call_id,
                status=normalized.get("status"),
                duration=normalized.get("duration"),
                recording_url=normalized.get("recording_url")
            )

        # Update database
        result = await db.execute(
            select(Communication).where(Communication.call_sid == call_id)
        )
        comm = result.scalar_one_or_none()
        if comm:
            status_val = normalized.get("status", "")
            status_map = {
                "ringing": "ringing",
                "in-progress": "in_progress",
                "in_progress": "in_progress",
                "completed": "completed",
                "busy": "busy",
                "no-answer": "no_answer",
                "no_answer": "no_answer",
                "failed": "failed",
            }
            comm.status = status_map.get(status_val, status_val)

            if normalized.get("duration"):
                comm.duration_seconds = normalized["duration"]
            if normalized.get("recording_url"):
                comm.recording_url = normalized["recording_url"]

            if status_val in ["completed", "busy", "no-answer", "failed", "no_answer"]:
                comm.ended_at = datetime.utcnow()

            await db.commit()

        # Notify WebSocket clients
        await ws_manager.broadcast({
            "type": "call_status_update",
            **normalized
        })

    return {"status": "received"}


@router.post("/webhook/exotel/passthru")
async def exotel_passthru_webhook(request: Request):
    """Handle Exotel passthru webhooks for real-time call control.

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

    ws_manager = get_ws_manager()

    call_id = data.get("CallSid")
    digits = data.get("Digits")

    # Handle DTMF input
    if digits:
        await ws_manager.broadcast({
            "type": "dtmf_received",
            "call_id": call_id,
            "digits": digits
        })

    # Return empty response (call continues)
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml"
    )


# =============================================================================
# Original Webhooks (for backward compatibility)
# =============================================================================

@router.post("/webhook/call-status")
async def call_status_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle call status webhook from telephony provider.

    Accepts data from both telephony service and AI voice pipeline.
    Stores transcripts, summaries, entities, and creates call recordings.
    """
    data = await request.json()

    call_sid = data.get("CallSid") or data.get("call_sid")
    call_status = data.get("Status") or data.get("status")
    event_type = data.get("type", "call_status")

    if not call_sid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing call_sid"
        )

    # Find communication
    result = await db.execute(
        select(Communication).where(Communication.call_sid == call_sid)
    )
    comm = result.scalar_one_or_none()

    if not comm:
        # Log but don't error - might be a call from outside the system
        return {"status": "ignored", "reason": "call_sid not found"}

    # Update status
    if call_status:
        status_map = {
            "ringing": "ringing",
            "in-progress": "in_progress",
            "completed": "completed",
            "busy": "busy",
            "no-answer": "no_answer",
            "failed": "failed",
            "canceled": "failed"
        }
        comm.status = status_map.get(call_status.lower(), call_status)

    # Update timing
    if call_status and call_status.lower() == "in-progress":
        comm.connected_at = datetime.utcnow()
    elif call_status and call_status.lower() in ["completed", "busy", "no-answer", "failed"]:
        comm.ended_at = datetime.utcnow()
        if comm.connected_at:
            comm.duration_seconds = int((comm.ended_at - comm.connected_at).total_seconds())

    # Handle duration from webhook
    duration = data.get("duration")
    if duration:
        comm.duration_seconds = int(duration)

    # Handle recording URL if provided
    recording_url = data.get("RecordingUrl") or data.get("recording_url")
    if recording_url:
        comm.recording_url = recording_url

    # Handle transcript if provided (from AI voice pipeline)
    transcript = data.get("transcript")
    if transcript:
        # Convert list of conversation turns to text
        if isinstance(transcript, list):
            transcript_text = "\n".join([
                f"{turn.get('role', 'Unknown')}: {turn.get('content', '')}"
                for turn in transcript
            ])
            transcript_segments = transcript
        else:
            transcript_text = str(transcript)
            transcript_segments = None
        comm.transcript = transcript_text

        # Create or update CallRecording with transcript data
        if transcript_segments:
            await _save_call_recording(
                db, comm, transcript_segments, data.get("summary"),
                data.get("entities"), data.get("key_points")
            )

    # Handle AI-specific data
    summary = data.get("summary")
    if summary:
        comm.summary = summary

    entities = data.get("entities")
    if entities:
        # Store in provider_metadata for now
        metadata = comm.provider_metadata or {}
        metadata["entities"] = entities
        comm.provider_metadata = metadata

    # Handle outcome if provided
    outcome = data.get("outcome")
    if outcome:
        comm.outcome = outcome

    # Mark as AI-handled if this was an AI call
    if data.get("is_ai_handled") or event_type == "call_complete":
        comm.is_ai_handled = True

    # Handle campaign info
    campaign_id = data.get("campaign_id")
    if campaign_id and not comm.campaign_id:
        try:
            comm.campaign_id = UUID(campaign_id)
        except ValueError:
            pass

    await db.commit()

    # Update case if linked
    if comm.case_id:
        result = await db.execute(
            select(Case).where(Case.id == comm.case_id)
        )
        case = result.scalar_one_or_none()
        if case:
            case.total_attempts += 1
            case.last_contact_date = datetime.utcnow()
            if comm.status == "completed" and comm.duration_seconds > 0:
                case.successful_contacts += 1
            await db.commit()

    return {"status": "processed", "call_sid": call_sid}


@router.post("/webhook/sms-status")
async def sms_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle SMS delivery status webhook."""
    data = await request.json()

    message_sid = data.get("MessageSid") or data.get("message_sid")
    message_status = data.get("Status") or data.get("status")

    if not message_sid:
        return {"status": "ignored"}

    # Find communication by some identifier (would need to store message_sid)
    # For now, just acknowledge
    return {"status": "processed"}


@router.post("/webhook/whatsapp-status")
async def whatsapp_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle WhatsApp message status webhook."""
    data = await request.json()

    # Process WhatsApp delivery/read receipts
    return {"status": "processed"}


@router.get("/status")
async def get_telephony_status(
    current_user: User = Depends(get_current_user)
):
    """Get telephony service status."""
    # Check if telephony service is configured and available
    is_configured = bool(settings.exotel_api_key and settings.exotel_api_key != "mock")

    return {
        "configured": is_configured,
        "mode": "live" if is_configured else "mock",
        "provider": "exotel",
        "features": {
            "voice": True,
            "sms": True,
            "whatsapp": is_configured,  # WhatsApp needs real credentials
            "recording": True,
            "ai_voice": True
        }
    }


@router.get("/call/{call_sid}/status")
async def get_call_status(
    call_sid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get real-time call status."""
    result = await db.execute(
        select(Communication).where(
            Communication.call_sid == call_sid,
            Communication.organization_id == current_user.organization_id
        )
    )
    comm = result.scalar_one_or_none()

    if not comm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    return {
        "call_sid": call_sid,
        "status": comm.status,
        "duration_seconds": comm.duration_seconds,
        "connected_at": comm.connected_at.isoformat() if comm.connected_at else None,
        "ended_at": comm.ended_at.isoformat() if comm.ended_at else None,
        "is_ai_handled": comm.is_ai_handled
    }


@router.get("/call/{call_sid}/transcript")
async def get_call_transcript(
    call_sid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get call transcript and AI analysis."""
    result = await db.execute(
        select(Communication).where(
            Communication.call_sid == call_sid,
            Communication.organization_id == current_user.organization_id
        )
    )
    comm = result.scalar_one_or_none()

    if not comm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    # Get associated recording if exists
    recording_result = await db.execute(
        select(CallRecording).where(CallRecording.communication_id == comm.id)
    )
    recording = recording_result.scalar_one_or_none()

    response = {
        "call_sid": call_sid,
        "transcript": comm.transcript,
        "summary": comm.summary,
        "outcome": comm.outcome,
        "is_ai_handled": comm.is_ai_handled,
        "duration_seconds": comm.duration_seconds
    }

    if recording:
        response.update({
            "segments": recording.transcription_segments,
            "ai_summary": recording.ai_summary,
            "key_points": recording.key_points,
            "entities": recording.entities_mentioned,
            "compliance_flags": recording.compliance_flags
        })

    return response


@router.post("/call/{call_sid}/hangup")
async def hangup_call(
    call_sid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Hangup an active call."""
    result = await db.execute(
        select(Communication).where(
            Communication.call_sid == call_sid,
            Communication.organization_id == current_user.organization_id
        )
    )
    comm = result.scalar_one_or_none()

    if not comm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    if comm.status not in ["ringing", "in_progress"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call is not active"
        )

    # TODO: Actually hangup via telephony provider
    comm.status = "completed"
    comm.ended_at = datetime.utcnow()
    if comm.connected_at:
        comm.duration_seconds = int((comm.ended_at - comm.connected_at).total_seconds())

    await db.commit()

    return {"status": "hung_up", "call_sid": call_sid}


@router.post("/call/{call_sid}/transfer")
async def transfer_call(
    call_sid: str,
    to_agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Transfer a call to another agent."""
    result = await db.execute(
        select(Communication).where(
            Communication.call_sid == call_sid,
            Communication.organization_id == current_user.organization_id
        )
    )
    comm = result.scalar_one_or_none()

    if not comm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    if comm.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call is not in progress"
        )

    # Verify target agent exists
    result = await db.execute(
        select(User).where(
            User.id == to_agent_id,
            User.organization_id == current_user.organization_id,
            User.is_active == True
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target agent not found"
        )

    # TODO: Actually transfer via telephony provider
    # For now, just update the agent
    comm.agent_id = to_agent_id
    await db.commit()

    return {"status": "transferred", "call_sid": call_sid, "to_agent_id": str(to_agent_id)}


@router.get("/templates/sms")
async def get_sms_templates(
    current_user: User = Depends(get_current_user)
):
    """Get available SMS templates."""
    # TODO: Fetch from database or configuration
    templates = [
        {
            "id": "payment_reminder",
            "name": "Payment Reminder",
            "content": "Dear {name}, your EMI of Rs {amount} for loan {loan_id} is due on {due_date}. Please pay to avoid late fees.",
            "variables": ["name", "amount", "loan_id", "due_date"]
        },
        {
            "id": "payment_overdue",
            "name": "Payment Overdue",
            "content": "Dear {name}, your EMI of Rs {amount} is overdue by {days} days. Please pay immediately to avoid further action.",
            "variables": ["name", "amount", "days"]
        },
        {
            "id": "payment_received",
            "name": "Payment Received",
            "content": "Thank you {name}! We received your payment of Rs {amount}. Receipt: {receipt_no}",
            "variables": ["name", "amount", "receipt_no"]
        }
    ]
    return {"templates": templates}


@router.get("/templates/whatsapp")
async def get_whatsapp_templates(
    current_user: User = Depends(get_current_user)
):
    """Get available WhatsApp templates."""
    # These would typically be pre-approved templates from WhatsApp Business API
    templates = [
        {
            "id": "payment_reminder_wa",
            "name": "Payment Reminder",
            "content": "Hi {{1}}, your payment of Rs {{2}} is due on {{3}}. Click here to pay: {{4}}",
            "variables": 4,
            "category": "UTILITY"
        },
        {
            "id": "payment_confirmation_wa",
            "name": "Payment Confirmation",
            "content": "Thank you {{1}}! Your payment of Rs {{2}} has been received. Receipt: {{3}}",
            "variables": 3,
            "category": "UTILITY"
        }
    ]
    return {"templates": templates}


async def _save_call_recording(
    db: AsyncSession,
    comm: Communication,
    transcript_segments: list,
    summary: str = None,
    entities: dict = None,
    key_points: list = None
):
    """Save or update call recording with transcript data.

    Args:
        db: Database session
        comm: Communication record
        transcript_segments: List of conversation turns
        summary: AI-generated summary
        entities: Extracted entities (amounts, dates, promises)
        key_points: Key points from conversation
    """
    # Check if recording already exists
    result = await db.execute(
        select(CallRecording).where(CallRecording.communication_id == comm.id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        # Create new recording
        recording = CallRecording(
            communication_id=comm.id,
            file_path=comm.recording_url or f"transcripts/{comm.id}.json",
            duration_seconds=comm.duration_seconds or 0,
            format="json",
            transcription_status="completed"
        )
        db.add(recording)

    # Update transcription data
    recording.transcription_text = comm.transcript
    recording.transcription_segments = transcript_segments
    recording.transcription_language = "hi"  # Default to Hindi/Hinglish

    # Update AI analysis
    if summary:
        recording.ai_summary = summary
    if key_points:
        recording.key_points = key_points
    if entities:
        recording.entities_mentioned = entities

    await db.flush()
