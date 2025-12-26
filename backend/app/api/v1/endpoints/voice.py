"""Voice AI API endpoints (provider-agnostic)."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import os
import base64

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.communication import Communication
from app.models.case import Case
from app.models.loan import Loan
from app.services.voice_ai import (
    get_voice_ai_provider,
    VoiceAIProvider,
    AgentConfig,
    BorrowerContext,
    CallStatus,
    CallDisposition
)
from app.services.voice_ai.livekit_agent import (
    get_livekit_service,
    BorrowerInfo,
    LIVEKIT_AVAILABLE
)

router = APIRouter()


# Priya's default system prompt
PRIYA_SYSTEM_PROMPT = """You are Priya, a friendly female collection agent. You are a woman, so always use feminine Hindi verb forms (e.g., "main bol rahi hoon", "main samjhti hoon", "mujhe lagta hai"). You speak natural Hinglish - the way educated urban Indians actually talk (mixing Hindi and English naturally).

SPEAKING STYLE:
- Talk like a real person, not a robot or script
- Use casual Hinglish: "Haan ji", "Actually", "Basically", "Acha", "Theek hai"
- Keep it SHORT - 1-2 sentences max per response
- Be warm but direct - you're here to help them pay
- Use "aap" respectfully, add "ji" naturally
- Sound like you're having a normal phone chat, not reading a script

EXAMPLES OF NATURAL RESPONSES:
- "Haan ji, {{borrower_name}} ji? Main Priya bol rahi hoon CollectIQ Finance se."
- "Acha, toh payment kab tak ho payegi roughly?"
- "Theek hai, no problem. Toh 15th tak kar denge, right?"
- "Actually aapki EMI overdue hai, bas isliye call kiya"

BORROWER INFO:
- Name: {{borrower_name}}
- Amount Due: Rs {{outstanding_amount}}
- Overdue: {{dpd}} days
- EMI: Rs {{emi_amount}}
- Loan: {{loan_type}}

RULES:
- NEVER threaten or be rude
- If they're struggling, be understanding and offer help
- Keep responses under 20 words ideally
- Sound human, not corporate
- If they agree to pay, confirm the date and thank them
- If they can't pay, ask when they can and offer to note it down

Respond in natural Hinglish only. Be conversational, not formal."""

PRIYA_WELCOME_MESSAGE = "Hello, {{borrower_name}} ji? Main Priya bol rahi hoon CollectIQ Finance se. Kaise hain aap?"


# Request/Response Models
class CreateAgentRequest(BaseModel):
    agent_name: str = "Priya - Collection Agent"
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    language: str = "hi"
    voice: str = "female"
    webhook_url: Optional[str] = None


class MakeCallRequest(BaseModel):
    phone_number: str
    borrower_name: str
    outstanding_amount: float
    emi_amount: float
    dpd: int
    loan_type: str = "Personal Loan"
    case_id: Optional[str] = None
    agent_id: Optional[str] = None


class CallResponse(BaseModel):
    success: bool
    call_id: Optional[str] = None
    message: Optional[str] = None


# Agent Management Endpoints
@router.post("/agent", summary="Create voice AI agent")
async def create_agent(
    request: CreateAgentRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new voice AI collection agent."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        provider = get_voice_ai_provider()

        config = AgentConfig(
            name=request.agent_name,
            system_prompt=request.system_prompt or PRIYA_SYSTEM_PROMPT,
            welcome_message=request.welcome_message or PRIYA_WELCOME_MESSAGE,
            language=request.language,
            voice=request.voice,
            webhook_url=request.webhook_url or os.getenv("VOICE_AI_WEBHOOK_URL")
        )

        result = await provider.create_agent(config)

        return {
            "success": True,
            "provider": provider.provider_name,
            "agent_id": result.get("agent_id"),
            "message": "Agent created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent", summary="List voice AI agents")
async def list_agents(
    current_user: User = Depends(get_current_user)
):
    """List all voice AI agents."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        provider = get_voice_ai_provider()
        agents = await provider.list_agents()
        return {
            "provider": provider.provider_name,
            "agents": agents
        }
    except NotImplementedError:
        return {"provider": provider.provider_name, "agents": [], "message": "List not supported"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/{agent_id}", summary="Get voice AI agent details")
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific voice AI agent."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        provider = get_voice_ai_provider()
        agent = await provider.get_agent(agent_id)
        return {"provider": provider.provider_name, "agent": agent}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Call Management Endpoints
@router.post("/call", response_model=CallResponse, summary="Make AI collection call")
async def make_call(
    request: MakeCallRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiate an AI-powered collection call."""
    try:
        provider = get_voice_ai_provider()

        borrower = BorrowerContext(
            name=request.borrower_name,
            phone_number=request.phone_number,
            outstanding_amount=request.outstanding_amount,
            emi_amount=request.emi_amount,
            dpd=request.dpd,
            loan_type=request.loan_type,
            case_id=str(request.case_id) if request.case_id else None
        )

        agent_id = request.agent_id or os.getenv("BOLNA_AGENT_ID")
        result = await provider.make_call(agent_id=agent_id, borrower=borrower)

        if result.success and request.case_id:
            # Get case and loan to retrieve borrower_id
            case_result = await db.execute(
                select(Case).where(Case.id == request.case_id)
            )
            case = case_result.scalar_one_or_none()

            if case:
                # Get loan to get borrower_id
                loan_result = await db.execute(
                    select(Loan).where(Loan.id == case.loan_id)
                )
                loan = loan_result.scalar_one_or_none()

                if loan:
                    # Create communication record
                    comm = Communication(
                        organization_id=current_user.organization_id,
                        borrower_id=loan.borrower_id,
                        loan_id=case.loan_id,
                        case_id=request.case_id,
                        agent_id=current_user.id,
                        channel="call",
                        direction="outbound",
                        status="initiated",
                        call_sid=result.call_id,
                        to_number=request.phone_number,
                        is_ai_handled=True,
                        provider_metadata={
                            "provider": provider.provider_name,
                            "agent_type": "ai",
                            "borrower_name": request.borrower_name,
                            "outstanding_amount": request.outstanding_amount
                        }
                    )
                    db.add(comm)
                    await db.commit()

        return CallResponse(
            success=result.success,
            call_id=result.call_id,
            message=result.message
        )

    except Exception as e:
        return CallResponse(success=False, message=str(e))


@router.post("/call/{call_id}/stop", summary="Stop active call")
async def stop_call(
    call_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stop an active or queued call."""
    try:
        provider = get_voice_ai_provider()
        success = await provider.stop_call(call_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/call/{call_id}", summary="Get call details")
async def get_call(
    call_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get details of a call."""
    try:
        provider = get_voice_ai_provider()
        details = await provider.get_call_details(call_id)
        return {
            "call_id": details.call_id,
            "status": details.status.value,
            "duration": details.duration,
            "recording_url": details.recording_url,
            "transcript": details.transcript,
            "disposition": details.disposition.value if details.disposition else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/call/{call_id}/sync", summary="Sync call status from provider")
async def sync_call_status(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Poll call status from provider and update local Communication record.

    Use this instead of webhooks for local development.
    """
    try:
        provider = get_voice_ai_provider()
        details = await provider.get_call_details(call_id)

        # Find and update communication record
        result = await db.execute(
            select(Communication).where(Communication.call_sid == call_id)
        )
        comm = result.scalar_one_or_none()

        updated = False
        if comm:
            comm.status = _map_call_status(details.status)
            if details.duration:
                comm.duration_seconds = details.duration
            if details.recording_url:
                comm.recording_url = details.recording_url
            if details.transcript:
                comm.transcript = details.transcript
            if details.disposition:
                comm.disposition = details.disposition.value
            if details.summary:
                if not comm.provider_metadata:
                    comm.provider_metadata = {}
                comm.provider_metadata["ai_summary"] = details.summary

            await db.commit()
            updated = True

        return {
            "call_id": details.call_id,
            "status": details.status.value,
            "duration": details.duration,
            "recording_url": details.recording_url,
            "transcript": details.transcript,
            "disposition": details.disposition.value if details.disposition else None,
            "db_updated": updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Webhook Endpoint
@router.post("/webhook", summary="Voice AI webhook handler")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle incoming webhooks from voice AI provider.

    This endpoint receives call status updates, transcripts, and recordings.
    """
    try:
        payload = await request.json()
        print(f"[Voice AI Webhook] Received: {json.dumps(payload, indent=2)[:500]}...")

        provider = get_voice_ai_provider()
        call_details = provider.parse_webhook(payload)

        # Find the communication record
        result = await db.execute(
            select(Communication).where(Communication.call_sid == call_details.call_id)
        )
        comm = result.scalar_one_or_none()

        if comm:
            # Update communication record
            comm.status = _map_call_status(call_details.status)
            comm.duration_seconds = call_details.duration
            comm.recording_url = call_details.recording_url
            comm.transcript = call_details.transcript

            if call_details.summary:
                if not comm.provider_metadata:
                    comm.provider_metadata = {}
                comm.provider_metadata["ai_summary"] = call_details.summary

            if call_details.disposition:
                comm.disposition = call_details.disposition.value

                # Update case if payment promise detected
                if call_details.disposition == CallDisposition.PROMISE_TO_PAY:
                    case_id = call_details.user_data.get("case_id") if call_details.user_data else None
                    if case_id:
                        background_tasks.add_task(
                            _update_case_status, db, int(case_id), "promise_to_pay"
                        )

            await db.commit()
            print(f"[Voice AI Webhook] Updated communication {comm.id}")

        return {"status": "received", "call_id": call_details.call_id}

    except Exception as e:
        print(f"[Voice AI Webhook] Error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/health", summary="Check voice AI provider health")
async def health_check():
    """Check if voice AI provider is accessible."""
    try:
        provider = get_voice_ai_provider()
        healthy = await provider.health_check()
        return {
            "provider": provider.provider_name,
            "healthy": healthy
        }
    except Exception as e:
        return {
            "provider": "unknown",
            "healthy": False,
            "error": str(e)
        }


def _map_call_status(status: CallStatus) -> str:
    """Map CallStatus to communication status string."""
    status_map = {
        CallStatus.QUEUED: "pending",
        CallStatus.RINGING: "ringing",
        CallStatus.IN_PROGRESS: "in_progress",
        CallStatus.COMPLETED: "completed",
        CallStatus.FAILED: "failed",
        CallStatus.NO_ANSWER: "no_answer",
        CallStatus.BUSY: "busy",
        CallStatus.CANCELLED: "cancelled"
    }
    return status_map.get(status, "unknown")


async def _update_case_status(db: AsyncSession, case_id: int, status: str):
    """Update case status in background."""
    try:
        result = await db.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        if case:
            case.status = status
            case.updated_at = datetime.utcnow()
            await db.commit()
    except Exception as e:
        print(f"Error updating case {case_id}: {e}")


# ============================================================================
# Sarvam AI WebSocket/Streaming Endpoints
# ============================================================================

@router.websocket("/sarvam/stream/{call_id}")
async def sarvam_audio_stream(
    websocket: WebSocket,
    call_id: str
):
    """WebSocket endpoint for real-time audio streaming with Sarvam AI.

    This endpoint handles bidirectional audio streaming:
    - Receives audio from Exotel/caller
    - Processes through Sarvam (STT -> LLM -> TTS)
    - Sends response audio back

    Audio format: PCM 16-bit, 16kHz, mono
    """
    await websocket.accept()
    print(f"[Sarvam WS] Connected: {call_id}")

    provider = get_voice_ai_provider()

    # Check if this is Sarvam provider
    if provider.provider_name != "sarvam":
        await websocket.close(code=4000, reason="Sarvam provider not active")
        return

    try:
        # Import here to avoid circular imports
        from app.services.voice_ai.sarvam_provider import SarvamProvider
        sarvam_provider: SarvamProvider = provider

        # Generate and send welcome message
        welcome_audio = await sarvam_provider.generate_welcome_message(call_id)
        if welcome_audio:
            await websocket.send_bytes(welcome_audio)

        # Audio buffer for accumulating chunks
        audio_buffer = bytearray()
        CHUNK_SIZE = 32000  # ~1 second of 16kHz 16-bit audio

        while True:
            # Receive audio data
            data = await websocket.receive()

            if data.get("type") == "websocket.disconnect":
                break

            if "bytes" in data:
                audio_chunk = data["bytes"]
                audio_buffer.extend(audio_chunk)

                # Process when we have enough audio
                if len(audio_buffer) >= CHUNK_SIZE:
                    # Process audio through Sarvam
                    response_audio = await sarvam_provider.process_audio(
                        call_id=call_id,
                        audio_data=bytes(audio_buffer)
                    )

                    # Clear buffer
                    audio_buffer.clear()

                    # Send response audio if available
                    if response_audio:
                        await websocket.send_bytes(response_audio)

            elif "text" in data:
                # Handle control messages
                msg = json.loads(data["text"])
                if msg.get("type") == "end":
                    break
                elif msg.get("type") == "dtmf":
                    # Handle DTMF tones if needed
                    print(f"[Sarvam WS] DTMF: {msg.get('digit')}")

    except WebSocketDisconnect:
        print(f"[Sarvam WS] Disconnected: {call_id}")
    except Exception as e:
        print(f"[Sarvam WS] Error: {e}")
    finally:
        # End call and get summary
        try:
            from app.services.voice_ai.sarvam_provider import SarvamProvider
            if isinstance(provider, SarvamProvider):
                summary = await provider.end_call(call_id)
                print(f"[Sarvam WS] Call ended: {summary}")
        except Exception as e:
            print(f"[Sarvam WS] Error ending call: {e}")


@router.post("/sarvam/stream/{call_id}", summary="Exotel audio callback for Sarvam")
async def sarvam_exotel_callback(
    request: Request,
    call_id: str
):
    """HTTP callback for Exotel to stream audio chunks.

    Exotel sends audio in chunks via POST requests.
    We process and return TwiML/audio response.
    """
    provider = get_voice_ai_provider()

    if provider.provider_name != "sarvam":
        return Response(
            content="Provider not Sarvam",
            status_code=400
        )

    try:
        from app.services.voice_ai.sarvam_provider import SarvamProvider
        sarvam_provider: SarvamProvider = provider

        content_type = request.headers.get("content-type", "")

        if "audio" in content_type or "octet-stream" in content_type:
            # Raw audio data
            audio_data = await request.body()

            # Process through Sarvam
            response_audio = await sarvam_provider.process_audio(
                call_id=call_id,
                audio_data=audio_data
            )

            if response_audio:
                return Response(
                    content=response_audio,
                    media_type="audio/wav"
                )

            return Response(status_code=204)

        else:
            # JSON payload with base64 audio
            payload = await request.json()
            audio_b64 = payload.get("audio")

            if audio_b64:
                audio_data = base64.b64decode(audio_b64)
                response_audio = await sarvam_provider.process_audio(
                    call_id=call_id,
                    audio_data=audio_data
                )

                if response_audio:
                    return {
                        "audio": base64.b64encode(response_audio).decode("utf-8"),
                        "format": "wav"
                    }

            return {"status": "ok"}

    except Exception as e:
        print(f"[Sarvam HTTP] Error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/sarvam/call/{call_id}/end", summary="End Sarvam call")
async def end_sarvam_call(
    call_id: str,
    db: AsyncSession = Depends(get_db)
):
    """End a Sarvam call and get summary.

    Called when call ends (hangup, timeout, etc).
    Returns transcript and disposition.
    """
    provider = get_voice_ai_provider()

    if provider.provider_name != "sarvam":
        return {"status": "not_sarvam"}

    try:
        from app.services.voice_ai.sarvam_provider import SarvamProvider
        sarvam_provider: SarvamProvider = provider

        result = await sarvam_provider.end_call(call_id)

        # Update communication record if exists
        comm_result = await db.execute(
            select(Communication).where(Communication.call_sid == call_id)
        )
        comm = comm_result.scalar_one_or_none()

        if comm:
            comm.status = "completed"
            comm.duration_seconds = result.get("duration", 0)
            comm.transcript = result.get("transcript_text", "")
            if result.get("summary"):
                if not comm.provider_metadata:
                    comm.provider_metadata = {}
                comm.provider_metadata["ai_summary"] = result.get("summary")
            comm.disposition = result.get("disposition", "contacted")
            await db.commit()

        return result

    except Exception as e:
        print(f"[Sarvam] Error ending call: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# LiveKit Voice AI Endpoints
# ============================================================================

class LiveKitCallRequest(BaseModel):
    """Request to start a LiveKit voice call."""
    borrower_name: str
    phone_number: str
    outstanding_amount: float
    emi_amount: float
    dpd: int
    loan_type: str = "Personal Loan"
    case_id: Optional[str] = None


@router.get("/livekit/status", summary="Check LiveKit availability")
async def livekit_status():
    """Check if LiveKit is available and configured."""
    return {
        "available": LIVEKIT_AVAILABLE,
        "configured": bool(os.getenv("LIVEKIT_API_KEY")),
        "url": os.getenv("LIVEKIT_URL", "not_set")
    }


@router.post("/livekit/call", summary="Start LiveKit voice call")
async def start_livekit_call(
    request: LiveKitCallRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a LiveKit-based voice call with Sarvam AI.

    Returns room info and access tokens for joining the call.
    The frontend should use these tokens to connect to LiveKit.
    """
    if not LIVEKIT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="LiveKit not available. Install: pip install livekit-agents livekit-plugins-sarvam"
        )

    try:
        livekit = get_livekit_service()

        borrower = BorrowerInfo(
            name=request.borrower_name,
            phone_number=request.phone_number,
            outstanding_amount=request.outstanding_amount,
            emi_amount=request.emi_amount,
            dpd=request.dpd,
            loan_type=request.loan_type,
            case_id=request.case_id
        )

        result = await livekit.start_collection_call(borrower=borrower)

        # Create communication record
        if request.case_id:
            # Get case and loan to retrieve borrower_id
            case_result = await db.execute(
                select(Case).where(Case.id == request.case_id)
            )
            case = case_result.scalar_one_or_none()

            if case:
                # Get loan to get borrower_id
                loan_result = await db.execute(
                    select(Loan).where(Loan.id == case.loan_id)
                )
                loan = loan_result.scalar_one_or_none()

                if loan:
                    comm = Communication(
                        organization_id=current_user.organization_id,
                        borrower_id=loan.borrower_id,
                        loan_id=case.loan_id,
                        case_id=request.case_id,
                        agent_id=current_user.id,
                        channel="call",
                        direction="outbound",
                        status="initiated",
                        call_sid=result["room_name"],
                        to_number=request.phone_number,
                        is_ai_handled=True,
                        provider_metadata={
                            "provider": "livekit",
                            "agent_type": "ai",
                            "borrower_name": request.borrower_name,
                            "outstanding_amount": request.outstanding_amount,
                            "room_sid": result["room_sid"]
                        }
                    )
                    db.add(comm)
                    await db.commit()

        return {
            "success": True,
            "room_name": result["room_name"],
            "livekit_url": result["livekit_url"],
            "user_token": result["user_token"],
            "message": "Room created. Connect using the provided token."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/livekit/room/{room_name}/token", summary="Get LiveKit room token")
async def get_room_token(
    room_name: str,
    participant_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get an access token to join an existing LiveKit room."""
    if not LIVEKIT_AVAILABLE:
        raise HTTPException(status_code=503, detail="LiveKit not available")

    try:
        livekit = get_livekit_service()
        token = livekit.create_token(
            room_name=room_name,
            participant_name=participant_name
        )
        return {
            "token": token,
            "livekit_url": livekit.url,
            "room_name": room_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/livekit/room/{room_name}/end", summary="End LiveKit call")
async def end_livekit_call(
    room_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """End a LiveKit call and clean up the room."""
    if not LIVEKIT_AVAILABLE:
        raise HTTPException(status_code=503, detail="LiveKit not available")

    try:
        livekit = get_livekit_service()
        result = await livekit.end_call(room_name)

        # Update communication record
        comm_result = await db.execute(
            select(Communication).where(Communication.call_sid == room_name)
        )
        comm = comm_result.scalar_one_or_none()

        if comm:
            comm.status = "completed"
            comm.ended_at = datetime.utcnow()
            if comm.connected_at:
                comm.duration_seconds = int((comm.ended_at - comm.connected_at).total_seconds())
            await db.commit()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
