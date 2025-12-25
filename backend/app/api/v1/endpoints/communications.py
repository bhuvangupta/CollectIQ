from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_agent_case_ids
from app.models.user import User
from app.models.communication import Communication, CallRecording
from app.models.borrower import Borrower
from app.models.case import Case
from app.schemas.communication import (
    CommunicationCreate,
    CommunicationUpdate,
    CommunicationResponse,
    CommunicationListResponse,
    InitiateCallRequest,
    InitiateCallResponse,
    SendSMSRequest,
    SendWhatsAppRequest,
    CallRecordingResponse,
    DispositionOption,
    CommunicationStatsResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


# Disposition options
DISPOSITION_OPTIONS = [
    DispositionOption(
        code="connected",
        label="Connected",
        sub_dispositions=[
            {"code": "promise_to_pay", "label": "Promise to Pay"},
            {"code": "payment_done", "label": "Payment Already Done"},
            {"code": "partial_payment", "label": "Will Pay Partial"},
            {"code": "callback_requested", "label": "Callback Requested"},
            {"code": "dispute", "label": "Dispute/Query"},
            {"code": "financial_difficulty", "label": "Financial Difficulty"},
        ]
    ),
    DispositionOption(
        code="not_connected",
        label="Not Connected",
        sub_dispositions=[
            {"code": "busy", "label": "Busy"},
            {"code": "no_answer", "label": "No Answer"},
            {"code": "switched_off", "label": "Switched Off"},
            {"code": "not_reachable", "label": "Not Reachable"},
            {"code": "wrong_number", "label": "Wrong Number"},
        ]
    ),
    DispositionOption(
        code="refused",
        label="Refused",
        sub_dispositions=[
            {"code": "refused_to_pay", "label": "Refused to Pay"},
            {"code": "abusive", "label": "Abusive"},
            {"code": "do_not_call", "label": "Do Not Call Request"},
        ]
    ),
]


@router.get("", response_model=PaginatedResponse[CommunicationListResponse])
async def list_communications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    borrower_id: Optional[UUID] = None,
    case_id: Optional[UUID] = None,
    channel: Optional[str] = None,
    direction: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    outcome: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List communications. Agents only see communications for their assigned cases."""
    from sqlalchemy.orm import selectinload
    from sqlalchemy import or_

    query = select(Communication).where(
        Communication.organization_id == current_user.organization_id
    )

    # Agent role: filter to only communications from assigned cases or by this agent
    agent_case_ids = await get_agent_case_ids(current_user, db)
    if agent_case_ids is not None:  # None means admin/manager, can see all
        if not agent_case_ids:  # Empty list means no assigned cases
            # Agent can still see their own communications
            query = query.where(Communication.agent_id == current_user.id)
        else:
            # Agent can see communications for assigned cases or made by them
            query = query.where(
                or_(
                    Communication.case_id.in_(agent_case_ids),
                    Communication.agent_id == current_user.id
                )
            )

    if borrower_id:
        query = query.where(Communication.borrower_id == borrower_id)
    if case_id:
        query = query.where(Communication.case_id == case_id)
    if channel:
        query = query.where(Communication.channel == channel)
    if direction:
        query = query.where(Communication.direction == direction)
    if status_filter:
        query = query.where(Communication.status == status_filter)
    if outcome:
        query = query.where(Communication.outcome == outcome)
    if date_from:
        query = query.where(Communication.initiated_at >= date_from)
    if date_to:
        query = query.where(Communication.initiated_at <= date_to)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Communication.initiated_at.desc())

    result = await db.execute(query)
    communications = result.scalars().all()

    # Enrich with borrower and case info
    items = []
    for comm in communications:
        comm_dict = {
            "id": comm.id,
            "organization_id": comm.organization_id,
            "borrower_id": comm.borrower_id,
            "loan_id": comm.loan_id,
            "case_id": comm.case_id,
            "agent_id": comm.agent_id,
            "channel": comm.channel,
            "direction": comm.direction,
            "status": comm.status,
            "outcome": comm.outcome,
            "from_number": comm.from_number,
            "to_number": comm.to_number,
            "duration_seconds": comm.duration_seconds,
            "is_ai_handled": comm.is_ai_handled,
            "initiated_at": comm.initiated_at,
            "connected_at": comm.connected_at,
            "ended_at": comm.ended_at,
            "recording_url": comm.recording_url,
            "ai_script": comm.ai_script,
            "transcript": comm.transcript,
        }

        # Get borrower name
        if comm.borrower_id:
            borrower_result = await db.execute(
                select(Borrower).where(Borrower.id == comm.borrower_id)
            )
            borrower = borrower_result.scalar_one_or_none()
            if borrower:
                comm_dict["borrower_name"] = borrower.full_name

        # Get case number
        if comm.case_id:
            case_result = await db.execute(
                select(Case).where(Case.id == comm.case_id)
            )
            case = case_result.scalar_one_or_none()
            if case:
                comm_dict["case_number"] = case.case_number

        items.append(CommunicationListResponse.model_validate(comm_dict))

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/dispositions", response_model=List[DispositionOption])
async def get_disposition_options():
    """Get available disposition options."""
    return DISPOSITION_OPTIONS


@router.get("/stats", response_model=CommunicationStatsResponse)
async def get_communication_stats(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get communication statistics."""
    org_id = current_user.organization_id

    base_query = select(Communication).where(
        Communication.organization_id == org_id
    )
    if date_from:
        base_query = base_query.where(Communication.initiated_at >= date_from)
    if date_to:
        base_query = base_query.where(Communication.initiated_at <= date_to)

    # Total calls
    total_calls = await db.scalar(
        select(func.count(Communication.id))
        .where(Communication.organization_id == org_id)
        .where(Communication.channel == "call")
    )

    # Total duration
    total_duration = await db.scalar(
        select(func.sum(Communication.duration_seconds))
        .where(Communication.organization_id == org_id)
        .where(Communication.channel == "call")
    ) or 0

    # Successful contacts
    successful = await db.scalar(
        select(func.count(Communication.id))
        .where(Communication.organization_id == org_id)
        .where(Communication.channel == "call")
        .where(Communication.status == "completed")
        .where(Communication.duration_seconds > 0)
    )

    # By channel
    channel_result = await db.execute(
        select(Communication.channel, func.count(Communication.id))
        .where(Communication.organization_id == org_id)
        .group_by(Communication.channel)
    )
    by_channel = {row[0]: row[1] for row in channel_result.all()}

    # By outcome
    outcome_result = await db.execute(
        select(Communication.outcome, func.count(Communication.id))
        .where(Communication.organization_id == org_id)
        .where(Communication.outcome.isnot(None))
        .group_by(Communication.outcome)
    )
    by_outcome = {row[0]: row[1] for row in outcome_result.all()}

    contact_rate = (successful / total_calls * 100) if total_calls else 0
    avg_duration = (total_duration / total_calls) if total_calls else 0

    return CommunicationStatsResponse(
        total_calls=total_calls or 0,
        total_duration_minutes=total_duration // 60,
        successful_contacts=successful or 0,
        contact_rate=round(contact_rate, 2),
        avg_call_duration=round(avg_duration, 2),
        total_sms=by_channel.get("sms", 0),
        total_whatsapp=by_channel.get("whatsapp", 0),
        by_outcome=by_outcome,
        by_channel=by_channel
    )


class GenerateScriptRequest(BaseModel):
    case_id: UUID
    language: str = "en"


class GenerateScriptResponse(BaseModel):
    script: str
    context: dict


class GenerateMessageRequest(BaseModel):
    case_id: UUID
    channel: str = "sms"  # sms or whatsapp
    language: str = "en"
    template_type: str = "payment_reminder"  # payment_reminder, overdue_notice, follow_up


class GenerateMessageResponse(BaseModel):
    message: str
    context: dict


@router.post("/generate-script", response_model=GenerateScriptResponse)
async def generate_call_script(
    request: GenerateScriptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI call script based on case context and history."""
    from app.models.loan import Loan
    from app.models.organization import Organization
    import httpx
    from app.core.config import settings

    # Get organization name
    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    org_name = organization.name if organization else "CollectIQ"

    # Get agent name
    agent_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
    if not agent_name:
        agent_name = current_user.email.split('@')[0]

    # Get case
    result = await db.execute(
        select(Case).where(
            Case.id == request.case_id,
            Case.organization_id == current_user.organization_id
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get loan and borrower
    result = await db.execute(select(Loan).where(Loan.id == case.loan_id))
    loan = result.scalar_one_or_none()

    borrower = None
    if loan:
        result = await db.execute(select(Borrower).where(Borrower.id == loan.borrower_id))
        borrower = result.scalar_one_or_none()

    # Get previous communications for this case
    result = await db.execute(
        select(Communication)
        .where(Communication.case_id == request.case_id)
        .order_by(Communication.initiated_at.desc())
        .limit(5)
    )
    previous_comms = result.scalars().all()

    # Build context
    outstanding = 0
    emi = 0
    if loan:
        outstanding = round(float(loan.total_outstanding or 0))  # Round to whole number
        emi = round(float(loan.emi_amount or 0))

    context = {
        "agent_name": agent_name,
        "organization_name": org_name,
        "borrower_name": borrower.full_name if borrower else "Customer",
        "outstanding_amount": outstanding,
        "emi_amount": emi,
        "dpd": loan.dpd if loan else 0,
        "bucket": loan.bucket if loan else None,
        "previous_outcome": case.last_contact_outcome,
        "total_attempts": case.total_attempts or 0,
        "language": request.language,
    }

    # Build previous call summary
    previous_summary = ""
    for comm in previous_comms[:3]:
        if comm.outcome:
            previous_summary += f"- {comm.outcome.replace('_', ' ')}\n"

    # Generate script using AI Engine or fallback
    script = None

    # Build language-specific instruction
    language_instruction = ""
    if request.language == "hinglish":
        language_instruction = "IMPORTANT: Generate the script in Hinglish - use romanized Hindi mixed with English words. Example: 'Namaste ji, main ABC company se bol raha hoon. Aapke loan account mein payment pending hai.' Do NOT use pure English. Do NOT use Devanagari script. Use Roman letters only with Hindi words like 'aapka', 'kya', 'hum', 'hai', 'mein', 'karein', etc."
    elif request.language == "hi":
        language_instruction = "Generate the script in Hindi using Devanagari script."

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ai_engine_url}/dialog/respond",
                json={
                    "conversation_history": [],
                    "context": {
                        **context,
                        "previous_calls": previous_summary,
                        "generate_opening_script": True,
                        "language_instruction": language_instruction,
                    },
                    "language": request.language
                }
            )
            if response.status_code == 200:
                ai_response = response.json()
                script = ai_response.get("response", "")
                # Replace any placeholders the AI might use
                script = script.replace("[Your Name]", agent_name)
                script = script.replace("[Agent Name]", agent_name)
                script = script.replace("[Bank Name]", org_name)
                script = script.replace("[Company Name]", org_name)
                script = script.replace("[Institution Name]", org_name)
                script = script.replace("[Institution]", org_name)
                script = script.replace("[Organization Name]", org_name)
                script = script.replace("[Organization]", org_name)
                script = script.replace("[Lender Name]", org_name)
                script = script.replace("[Lender]", org_name)
                script = script.replace("[Financial Institution]", org_name)
                script = script.replace("[Company]", org_name)
            else:
                raise Exception("AI Engine error")
    except Exception as e:
        # Fallback script generation
        if request.language == "hi":
            script = f"""नमस्ते {context['borrower_name']} जी,

मैं {agent_name}, {org_name} से बोल रहा/रही हूं। आपके लोन खाते में ₹{context['outstanding_amount']:,.0f} की राशि {context['dpd']} दिनों से बकाया है।

क्या आप मुझे बता सकते हैं कि आप यह भुगतान कब तक कर पाएंगे?

हम आपकी सुविधा के लिए कई भुगतान विकल्प प्रदान कर सकते हैं।"""
        elif request.language == "hinglish":
            script = f"""Hello {context['borrower_name']} ji,

Main {agent_name}, {org_name} se bol raha hoon. Aapke loan account mein ₹{context['outstanding_amount']:,.0f} ka amount {context['dpd']} din se pending hai.

Kya aap mujhe bata sakte hain ki aap ye payment kab tak kar payenge?

Hum aapko flexible payment options de sakte hain. Koi bhi problem ho toh please batayein."""
        else:
            script = f"""Hello {context['borrower_name']},

This is {agent_name} calling from {org_name} regarding your loan account. There is an outstanding amount of ₹{context['outstanding_amount']:,.0f} which is overdue by {context['dpd']} days.

Could you please let me know when you would be able to make this payment?

We can offer flexible payment options for your convenience."""

    return GenerateScriptResponse(script=script, context=context)


@router.post("/generate-message", response_model=GenerateMessageResponse)
async def generate_message(
    request: GenerateMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI message for SMS or WhatsApp based on case context."""
    from app.models.loan import Loan
    from app.models.organization import Organization
    import httpx
    from app.core.config import settings

    # Get organization name
    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    org_name = organization.name if organization else "CollectIQ"

    # Get case
    result = await db.execute(
        select(Case).where(
            Case.id == request.case_id,
            Case.organization_id == current_user.organization_id
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get loan and borrower
    result = await db.execute(select(Loan).where(Loan.id == case.loan_id))
    loan = result.scalar_one_or_none()

    borrower = None
    if loan:
        result = await db.execute(select(Borrower).where(Borrower.id == loan.borrower_id))
        borrower = result.scalar_one_or_none()

    # Build context
    outstanding = round(float(loan.total_outstanding or 0)) if loan else 0
    emi = round(float(loan.emi_amount or 0)) if loan else 0
    dpd = loan.dpd if loan else 0

    context = {
        "organization_name": org_name,
        "borrower_name": borrower.full_name if borrower else "Customer",
        "borrower_first_name": (borrower.full_name.split()[0] if borrower and borrower.full_name else "Customer"),
        "outstanding_amount": outstanding,
        "emi_amount": emi,
        "dpd": dpd,
        "channel": request.channel,
        "template_type": request.template_type,
        "language": request.language,
    }

    # Generate message using AI Engine or fallback templates
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ai_engine_url}/dialog/respond",
                json={
                    "conversation_history": [],
                    "context": {
                        **context,
                        "generate_sms_template": request.channel == "sms",
                        "generate_whatsapp_template": request.channel == "whatsapp",
                        "template_type": request.template_type,
                    },
                    "language": request.language
                }
            )
            if response.status_code == 200:
                ai_response = response.json()
                message = ai_response.get("response", "")
                # Replace placeholders
                message = message.replace("[Company Name]", org_name)
                message = message.replace("[Organization]", org_name)
                message = message.replace("[Bank Name]", org_name)
            else:
                raise Exception("AI Engine error")
    except Exception:
        # Fallback templates
        message = _get_fallback_message_template(
            channel=request.channel,
            template_type=request.template_type,
            language=request.language,
            context=context,
            org_name=org_name
        )

    return GenerateMessageResponse(message=message, context=context)


def _get_fallback_message_template(
    channel: str,
    template_type: str,
    language: str,
    context: dict,
    org_name: str
) -> str:
    """Get fallback message template."""
    name = context.get("borrower_first_name", "Customer")
    outstanding = context.get("outstanding_amount", 0)
    dpd = context.get("dpd", 0)
    emi = context.get("emi_amount", 0)

    # SMS templates (very short)
    if channel == "sms":
        if language == "hi":
            templates = {
                "payment_reminder": f"{name} जी, EMI ₹{emi:,} बकाया है। कृपया भुगतान करें।",
                "overdue_notice": f"{name} जी, ₹{outstanding:,} {dpd} दिनों से बकाया। तुरंत भुगतान करें।",
                "follow_up": f"{name} जी, ₹{outstanding:,} भुगतान हुआ? कृपया संपर्क करें।",
            }
        else:
            templates = {
                "payment_reminder": f"Hi {name}, EMI ₹{emi:,} is due. Please pay soon.",
                "overdue_notice": f"Hi {name}, ₹{outstanding:,} overdue by {dpd} days. Pay immediately.",
                "follow_up": f"Hi {name}, did you pay ₹{outstanding:,}? Please respond.",
            }
    # WhatsApp templates (slightly longer but still concise)
    else:
        if language == "hi":
            templates = {
                "payment_reminder": f"{name} जी, आपकी EMI ₹{emi:,} बकाया है। कृपया जल्द भुगतान करें। सहायता के लिए संपर्क करें।",
                "overdue_notice": f"{name} जी, ₹{outstanding:,} {dpd} दिनों से बकाया है। कृपया तुरंत भुगतान करें।",
                "follow_up": f"{name} जी, ₹{outstanding:,} का भुगतान हुआ? कोई समस्या हो तो बताएं।",
            }
        else:
            templates = {
                "payment_reminder": f"Hi {name}, your EMI of ₹{emi:,} is due. Please pay at your earliest. Contact us for help.",
                "overdue_notice": f"Hi {name}, ₹{outstanding:,} is overdue by {dpd} days. Please pay immediately to avoid action.",
                "follow_up": f"Hi {name}, were you able to pay ₹{outstanding:,}? Let us know if you need help.",
            }

    return templates.get(template_type, templates["payment_reminder"])


@router.post("/call", response_model=InitiateCallResponse)
async def initiate_call(
    request: InitiateCallRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiate an outbound call."""
    from app.models.loan import Loan

    borrower = None
    borrower_id = request.borrower_id

    # If case_id is provided but no borrower_id, get borrower from case
    if request.case_id and not request.borrower_id:
        result = await db.execute(
            select(Case).where(
                Case.id == request.case_id,
                Case.organization_id == current_user.organization_id
            )
        )
        case = result.scalar_one_or_none()
        if case:
            # Get loan to find borrower
            result = await db.execute(select(Loan).where(Loan.id == case.loan_id))
            loan = result.scalar_one_or_none()
            if loan:
                borrower_id = loan.borrower_id

    # Verify borrower
    if borrower_id:
        result = await db.execute(
            select(Borrower).where(
                Borrower.id == borrower_id,
                Borrower.organization_id == current_user.organization_id
            )
        )
        borrower = result.scalar_one_or_none()

    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found"
        )

    if borrower.do_not_call:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Borrower has Do Not Call flag set"
        )

    # Update borrower's preferred language if specified
    if request.language and request.language != borrower.preferred_language:
        borrower.preferred_language = request.language

    phone = request.phone_number or borrower.primary_phone

    # Create communication record
    import uuid
    import httpx
    from app.core.config import settings

    call_sid = f"CALL-{uuid.uuid4()}"

    communication = Communication(
        organization_id=current_user.organization_id,
        borrower_id=borrower_id,
        loan_id=request.loan_id,
        case_id=request.case_id,
        agent_id=None if request.use_ai else current_user.id,
        channel="call",
        direction="outbound",
        from_number="+919999999999",  # Mock caller ID
        to_number=phone,
        status="initiating",
        call_sid=call_sid,
        is_ai_handled=request.use_ai,
        ai_script=request.script if request.use_ai else None
    )
    db.add(communication)
    await db.commit()
    await db.refresh(communication)

    # Initiate call via telephony service
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            call_payload = {
                "phone_number": phone,
                "caller_id": "+919999999999",
                "borrower_id": str(borrower_id),
                "case_id": str(request.case_id) if request.case_id else None,
                "language": request.language,
                "use_ai": request.use_ai,
                "callback_url": f"{settings.vite_api_url}/api/v1/telephony/webhook/call-status"
            }
            # Include script for AI calls
            if request.use_ai and request.script:
                call_payload["script"] = request.script

            response = await client.post(
                f"{settings.telephony_url}/calls/initiate",
                json=call_payload
            )
            if response.status_code == 200:
                call_data = response.json()
                communication.call_sid = call_data.get("call_id", call_sid)
                communication.status = "ringing"
                await db.commit()
    except Exception as e:
        # Log error but don't fail - call record is created
        print(f"Telephony service error: {e}")
        communication.status = "failed"
        await db.commit()

    return InitiateCallResponse(
        communication_id=communication.id,
        call_sid=communication.call_sid,
        status=communication.status
    )


@router.post("/sms")
async def send_sms(
    request: SendSMSRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send an SMS."""
    # Verify borrower
    result = await db.execute(
        select(Borrower).where(
            Borrower.id == request.borrower_id,
            Borrower.organization_id == current_user.organization_id
        )
    )
    borrower = result.scalar_one_or_none()

    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found"
        )

    if borrower.do_not_sms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Borrower has Do Not SMS flag set"
        )

    phone = request.phone_number or borrower.primary_phone

    communication = Communication(
        organization_id=current_user.organization_id,
        borrower_id=request.borrower_id,
        loan_id=request.loan_id,
        case_id=request.case_id,
        agent_id=current_user.id,
        channel="sms",
        direction="outbound",
        to_number=phone,
        status="queued",
        message_content=request.message
    )
    db.add(communication)
    await db.commit()

    # TODO: Actually send SMS via telephony service

    return {"message": "SMS queued successfully", "communication_id": str(communication.id)}


@router.post("/whatsapp")
async def send_whatsapp(
    request: SendWhatsAppRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a WhatsApp message."""
    # Verify borrower
    result = await db.execute(
        select(Borrower).where(
            Borrower.id == request.borrower_id,
            Borrower.organization_id == current_user.organization_id
        )
    )
    borrower = result.scalar_one_or_none()

    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found"
        )

    if borrower.do_not_whatsapp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Borrower has Do Not WhatsApp flag set"
        )

    phone = request.phone_number or borrower.primary_phone

    communication = Communication(
        organization_id=current_user.organization_id,
        borrower_id=request.borrower_id,
        loan_id=request.loan_id,
        case_id=request.case_id,
        agent_id=current_user.id,
        channel="whatsapp",
        direction="outbound",
        to_number=phone,
        status="queued",
        template_id=request.template_id
    )
    db.add(communication)
    await db.commit()

    # TODO: Actually send WhatsApp via telephony service

    return {"message": "WhatsApp message queued", "communication_id": str(communication.id)}


@router.get("/{comm_id}", response_model=CommunicationResponse)
async def get_communication(
    comm_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific communication."""
    result = await db.execute(
        select(Communication).where(
            Communication.id == comm_id,
            Communication.organization_id == current_user.organization_id
        )
    )
    comm = result.scalar_one_or_none()

    if not comm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Communication not found"
        )

    return comm


@router.put("/{comm_id}", response_model=CommunicationResponse)
async def update_communication(
    comm_id: UUID,
    update_data: CommunicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a communication (e.g., add disposition)."""
    result = await db.execute(
        select(Communication).where(
            Communication.id == comm_id,
            Communication.organization_id == current_user.organization_id
        )
    )
    comm = result.scalar_one_or_none()

    if not comm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Communication not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(comm, field, value)

    # Update case contact info if linked
    if comm.case_id:
        result = await db.execute(
            select(Case).where(Case.id == comm.case_id)
        )
        case = result.scalar_one_or_none()
        if case:
            case.last_contact_date = datetime.utcnow()
            case.last_contact_outcome = update_dict.get('outcome')
            case.total_attempts += 1
            if comm.status == "completed" and comm.duration_seconds > 0:
                case.successful_contacts += 1

    await db.commit()
    await db.refresh(comm)

    return comm


@router.get("/{comm_id}/recording", response_model=CallRecordingResponse)
async def get_call_recording(
    comm_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get call recording and transcription."""
    result = await db.execute(
        select(Communication).where(
            Communication.id == comm_id,
            Communication.organization_id == current_user.organization_id
        )
    )
    comm = result.scalar_one_or_none()

    if not comm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Communication not found"
        )

    result = await db.execute(
        select(CallRecording).where(CallRecording.communication_id == comm_id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found"
        )

    return recording
