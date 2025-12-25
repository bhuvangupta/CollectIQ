from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.message_template import MessageTemplate

router = APIRouter()


# Schemas
class TemplateCreate(BaseModel):
    name: str
    channel: str  # sms, whatsapp
    language: str = "en"
    content: str
    category: str = "payment_reminder"
    whatsapp_template_id: Optional[str] = None
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    whatsapp_template_id: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    channel: str
    language: str
    content: str
    category: str
    whatsapp_template_id: Optional[str]
    is_active: bool
    is_default: bool

    class Config:
        from_attributes = True


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    channel: Optional[str] = None,
    language: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List message templates for the organization."""
    query = select(MessageTemplate).where(
        MessageTemplate.organization_id == current_user.organization_id
    )

    if channel:
        query = query.where(MessageTemplate.channel == channel)
    if language:
        query = query.where(MessageTemplate.language == language)
    if category:
        query = query.where(MessageTemplate.category == category)
    if active_only:
        query = query.where(MessageTemplate.is_active == True)

    query = query.order_by(MessageTemplate.channel, MessageTemplate.category, MessageTemplate.name)

    result = await db.execute(query)
    templates = result.scalars().all()

    return templates


@router.post("", response_model=TemplateResponse)
async def create_template(
    template: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new message template."""
    # If setting as default, unset other defaults for same channel/category/language
    if template.is_default:
        existing = await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.organization_id == current_user.organization_id,
                MessageTemplate.channel == template.channel,
                MessageTemplate.category == template.category,
                MessageTemplate.language == template.language,
                MessageTemplate.is_default == True
            )
        )
        for t in existing.scalars().all():
            t.is_default = False

    new_template = MessageTemplate(
        organization_id=current_user.organization_id,
        name=template.name,
        channel=template.channel,
        language=template.language,
        content=template.content,
        category=template.category,
        whatsapp_template_id=template.whatsapp_template_id,
        is_default=template.is_default
    )
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)

    return new_template


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific template."""
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.organization_id == current_user.organization_id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    update: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a template."""
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.organization_id == current_user.organization_id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # If setting as default, unset other defaults
    if update.is_default:
        existing = await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.organization_id == current_user.organization_id,
                MessageTemplate.channel == template.channel,
                MessageTemplate.category == template.category,
                MessageTemplate.language == template.language,
                MessageTemplate.is_default == True,
                MessageTemplate.id != template_id
            )
        )
        for t in existing.scalars().all():
            t.is_default = False

    # Update fields
    if update.name is not None:
        template.name = update.name
    if update.content is not None:
        template.content = update.content
    if update.category is not None:
        template.category = update.category
    if update.whatsapp_template_id is not None:
        template.whatsapp_template_id = update.whatsapp_template_id
    if update.is_active is not None:
        template.is_active = update.is_active
    if update.is_default is not None:
        template.is_default = update.is_default

    await db.commit()
    await db.refresh(template)

    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a template."""
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.organization_id == current_user.organization_id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()

    return {"status": "deleted"}


@router.post("/seed-defaults")
async def seed_default_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Seed default templates for the organization."""
    # Check if templates already exist
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.organization_id == current_user.organization_id
        ).limit(1)
    )
    if result.scalar_one_or_none():
        return {"status": "templates already exist"}

    # Default templates
    defaults = [
        # SMS English
        {"name": "Payment Reminder - EN", "channel": "sms", "language": "en", "category": "payment_reminder",
         "content": "Hi {name}, EMI Rs.{emi} is due. Please pay soon.", "is_default": True},
        {"name": "Overdue Notice - EN", "channel": "sms", "language": "en", "category": "overdue_notice",
         "content": "Hi {name}, Rs.{amount} overdue by {dpd} days. Pay immediately.", "is_default": True},
        {"name": "Follow Up - EN", "channel": "sms", "language": "en", "category": "follow_up",
         "content": "Hi {name}, did you pay Rs.{amount}? Please respond.", "is_default": True},

        # SMS Hinglish
        {"name": "Payment Reminder - Hinglish", "channel": "sms", "language": "hinglish", "category": "payment_reminder",
         "content": "Hi {name} ji, EMI Rs.{emi} due hai. Please jaldi pay karein.", "is_default": True},
        {"name": "Overdue Notice - Hinglish", "channel": "sms", "language": "hinglish", "category": "overdue_notice",
         "content": "{name} ji, Rs.{amount} {dpd} din se pending hai. Turant pay karein.", "is_default": True},
        {"name": "Follow Up - Hinglish", "channel": "sms", "language": "hinglish", "category": "follow_up",
         "content": "{name} ji, Rs.{amount} payment hua? Please reply karein.", "is_default": True},

        # SMS Hindi
        {"name": "Payment Reminder - HI", "channel": "sms", "language": "hi", "category": "payment_reminder",
         "content": "{name} जी, EMI Rs.{emi} बकाया है। कृपया भुगतान करें।", "is_default": True},
        {"name": "Overdue Notice - HI", "channel": "sms", "language": "hi", "category": "overdue_notice",
         "content": "{name} जी, Rs.{amount} {dpd} दिनों से बकाया। तुरंत भुगतान करें।", "is_default": True},
        {"name": "Follow Up - HI", "channel": "sms", "language": "hi", "category": "follow_up",
         "content": "{name} जी, Rs.{amount} भुगतान हुआ? कृपया संपर्क करें।", "is_default": True},

        # WhatsApp English
        {"name": "Payment Reminder - EN", "channel": "whatsapp", "language": "en", "category": "payment_reminder",
         "content": "Hi {name}, your EMI of Rs.{emi} is due. Please pay at your earliest.", "is_default": True},
        {"name": "Overdue Notice - EN", "channel": "whatsapp", "language": "en", "category": "overdue_notice",
         "content": "Hi {name}, Rs.{amount} is overdue by {dpd} days. Please pay immediately.", "is_default": True},
        {"name": "Follow Up - EN", "channel": "whatsapp", "language": "en", "category": "follow_up",
         "content": "Hi {name}, were you able to pay Rs.{amount}? Let us know if you need help.", "is_default": True},

        # WhatsApp Hinglish
        {"name": "Payment Reminder - Hinglish", "channel": "whatsapp", "language": "hinglish", "category": "payment_reminder",
         "content": "Hi {name} ji, aapki EMI Rs.{emi} due hai. Please jaldi pay kar dijiye.", "is_default": True},
        {"name": "Overdue Notice - Hinglish", "channel": "whatsapp", "language": "hinglish", "category": "overdue_notice",
         "content": "{name} ji, Rs.{amount} {dpd} din se pending hai. Please turant payment karein.", "is_default": True},
        {"name": "Follow Up - Hinglish", "channel": "whatsapp", "language": "hinglish", "category": "follow_up",
         "content": "{name} ji, Rs.{amount} ka payment ho gaya? Koi problem ho toh batayein.", "is_default": True},

        # WhatsApp Hindi
        {"name": "Payment Reminder - HI", "channel": "whatsapp", "language": "hi", "category": "payment_reminder",
         "content": "{name} जी, आपकी EMI Rs.{emi} बकाया है। कृपया जल्द भुगतान करें।", "is_default": True},
        {"name": "Overdue Notice - HI", "channel": "whatsapp", "language": "hi", "category": "overdue_notice",
         "content": "{name} जी, Rs.{amount} {dpd} दिनों से बकाया है। कृपया तुरंत भुगतान करें।", "is_default": True},
        {"name": "Follow Up - HI", "channel": "whatsapp", "language": "hi", "category": "follow_up",
         "content": "{name} जी, Rs.{amount} का भुगतान हुआ? कोई समस्या हो तो बताएं।", "is_default": True},
    ]

    for t in defaults:
        template = MessageTemplate(
            organization_id=current_user.organization_id,
            **t
        )
        db.add(template)

    await db.commit()

    return {"status": "seeded", "count": len(defaults)}
