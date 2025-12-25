"""Voice AI API endpoints (provider-agnostic)."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import os

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.communication import Communication
from app.models.case import Case
from app.services.voice_ai import (
    get_voice_ai_provider,
    VoiceAIProvider,
    AgentConfig,
    BorrowerContext,
    CallStatus,
    CallDisposition
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
            # Create communication record
            comm = Communication(
                case_id=request.case_id,
                channel="call",
                direction="outbound",
                status="initiated",
                external_id=result.call_id,
                metadata={
                    "provider": provider.provider_name,
                    "agent_type": "ai",
                    "borrower_name": request.borrower_name,
                    "outstanding_amount": request.outstanding_amount
                },
                created_by_id=current_user.id
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
            select(Communication).where(Communication.external_id == call_id)
        )
        comm = result.scalar_one_or_none()

        updated = False
        if comm:
            comm.status = _map_call_status(details.status)
            if details.duration:
                comm.duration = details.duration
            if details.recording_url:
                comm.recording_url = details.recording_url
            if details.transcript:
                comm.transcript = details.transcript
            if details.disposition:
                comm.disposition = details.disposition.value
            if details.summary:
                if not comm.metadata:
                    comm.metadata = {}
                comm.metadata["ai_summary"] = details.summary

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
            select(Communication).where(Communication.external_id == call_details.call_id)
        )
        comm = result.scalar_one_or_none()

        if comm:
            # Update communication record
            comm.status = _map_call_status(call_details.status)
            comm.duration = call_details.duration
            comm.recording_url = call_details.recording_url
            comm.transcript = call_details.transcript

            if call_details.summary:
                if not comm.metadata:
                    comm.metadata = {}
                comm.metadata["ai_summary"] = call_details.summary

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
