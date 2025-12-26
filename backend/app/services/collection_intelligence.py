"""Collection intelligence service for priority scoring and strategy recommendation."""
from datetime import datetime
from typing import Optional
from decimal import Decimal


def calculate_priority_score(
    overdue_amount: Decimal,
    principal_amount: Decimal,
    dpd: int,
    risk_score: Optional[float] = None,
) -> dict:
    """
    Calculate collection priority score (0-10 scale).

    Formula:
    priority = 0.4 * overdue_ratio + 0.3 * normalized_days + 0.2 * risk + 0.1 * 30day_penalty

    Returns dict with score and priority level (1-5).
    """
    # Avoid division by zero
    principal = float(principal_amount) if principal_amount else 1.0
    overdue = float(overdue_amount) if overdue_amount else 0.0

    # Calculate components
    overdue_ratio = min(overdue / principal, 1.0)  # Cap at 1.0
    normalized_days = min(dpd / 180, 1.0)  # Normalize to 180 days
    risk = risk_score if risk_score is not None else 0.5
    penalty_30d = 1.0 if dpd > 30 else 0.0

    # Weighted priority score (0-1 scale)
    score = (
        0.4 * overdue_ratio +
        0.3 * normalized_days +
        0.2 * risk +
        0.1 * penalty_30d
    )

    # Scale to 0-10
    score_10 = round(score * 10, 2)

    # Map to priority level (1-5)
    if score_10 >= 8:
        priority_level = 5  # Critical
    elif score_10 >= 6:
        priority_level = 4  # High
    elif score_10 >= 4:
        priority_level = 3  # Medium
    elif score_10 >= 2:
        priority_level = 2  # Low
    else:
        priority_level = 1  # Minimal

    return {
        "score": score_10,
        "priority_level": priority_level,
        "factors": {
            "overdue_ratio": round(overdue_ratio, 3),
            "days_factor": round(normalized_days, 3),
            "risk_factor": round(risk, 3),
            "penalty_30d": penalty_30d > 0,
        },
        "calculated_at": datetime.utcnow().isoformat(),
    }


def get_collection_strategy(dpd: int, risk_level: str = "Medium") -> dict:
    """
    Get recommended collection strategy based on days past due.

    Returns strategy with channels, frequency, and tone.
    """
    if dpd <= 0:
        return {
            "strategy": "no_action",
            "channels": [],
            "frequency": "none",
            "tone": "none",
            "description": "Loan is current, no collection action needed",
        }
    elif dpd <= 7:
        return {
            "strategy": "gentle_reminder",
            "channels": ["whatsapp", "sms"],
            "frequency": "low",
            "tone": "polite",
            "description": "Soft reminder about upcoming/recent due date",
            "suggested_actions": [
                "Send payment reminder via WhatsApp",
                "Send SMS with payment link",
            ],
        }
    elif dpd <= 30:
        return {
            "strategy": "firm_reminder",
            "channels": ["call", "whatsapp", "sms"],
            "frequency": "medium",
            "tone": "professional",
            "description": "Regular follow-up with payment options",
            "suggested_actions": [
                "Schedule call to discuss payment",
                "Offer payment plan options",
                "Send formal reminder via all channels",
            ],
        }
    elif dpd <= 60:
        return {
            "strategy": "intensive_followup",
            "channels": ["call", "whatsapp", "sms", "email"],
            "frequency": "high",
            "tone": "firm",
            "description": "Intensive collection with escalation warning",
            "suggested_actions": [
                "Daily call attempts",
                "Escalate to senior agent",
                "Discuss settlement options",
                "Send formal notice",
            ],
        }
    elif dpd <= 90:
        return {
            "strategy": "escalated_collection",
            "channels": ["call", "whatsapp", "sms", "email"],
            "frequency": "very_high",
            "tone": "urgent",
            "description": "Escalated collection with legal warning",
            "suggested_actions": [
                "Multiple daily contact attempts",
                "Send legal notice warning",
                "Offer final settlement",
                "Prepare for legal action",
            ],
            "consider_legal_action": True,
        }
    else:
        return {
            "strategy": "legal_recovery",
            "channels": ["call", "email", "legal_notice"],
            "frequency": "as_needed",
            "tone": "formal",
            "description": "Legal recovery process",
            "suggested_actions": [
                "Issue legal notice",
                "Engage legal team",
                "Consider write-off assessment",
            ],
            "legal_action_recommended": True,
        }


def get_bucket_from_dpd(dpd: int) -> str:
    """Get bucket classification from DPD."""
    if dpd <= 0:
        return "current"
    elif dpd <= 30:
        return "X"  # 1-30 days
    elif dpd <= 60:
        return "1"  # 31-60 days
    elif dpd <= 90:
        return "2"  # 61-90 days
    elif dpd <= 180:
        return "3"  # 91-180 days
    else:
        return "NPA"  # 180+ days


def calculate_simple_risk_score(
    dpd: int,
    overdue_amount: Decimal,
    principal_amount: Decimal,
    total_attempts: int = 0,
    promises_broken: int = 0,
) -> dict:
    """
    Calculate a simple risk score without ML model.

    This is a heuristic-based scoring until a proper ML model is trained.
    Returns score 0-1 and risk level.
    """
    principal = float(principal_amount) if principal_amount else 1.0
    overdue = float(overdue_amount) if overdue_amount else 0.0

    # DPD factor (0-0.4)
    dpd_score = min(dpd / 180, 1.0) * 0.4

    # Overdue ratio factor (0-0.3)
    overdue_score = min(overdue / principal, 1.0) * 0.3

    # Contact resistance factor (0-0.2)
    if total_attempts > 0:
        # More attempts without resolution = higher risk
        contact_score = min(total_attempts / 10, 1.0) * 0.2
    else:
        contact_score = 0.1  # Unknown contact history

    # Broken promises factor (0-0.1)
    promise_score = min(promises_broken / 3, 1.0) * 0.1

    risk_score = dpd_score + overdue_score + contact_score + promise_score
    risk_score = round(min(risk_score, 1.0), 3)

    # Determine risk level
    if risk_score < 0.2:
        risk_level = "Low"
    elif risk_score < 0.5:
        risk_level = "Medium"
    elif risk_score < 0.7:
        risk_level = "High"
    else:
        risk_level = "Very High"

    return {
        "score": risk_score,
        "risk_level": risk_level,
        "default_probability": risk_score,
        "factors": {
            "dpd_factor": round(dpd_score, 3),
            "overdue_factor": round(overdue_score, 3),
            "contact_factor": round(contact_score, 3),
            "promise_factor": round(promise_score, 3),
        },
        "assessed_at": datetime.utcnow().isoformat(),
        "model": "heuristic_v1",
    }
