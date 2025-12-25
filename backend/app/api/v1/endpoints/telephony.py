from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.communication import Communication, CallRecording
from app.models.case import Case

router = APIRouter()


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
