from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    organizations,
    users,
    borrowers,
    loans,
    cases,
    communications,
    campaigns,
    analytics,
    telephony,
    templates,
    agent_performance,
    compliance,
    payments,
    audit_logs,
    voice,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(borrowers.router, prefix="/borrowers", tags=["Borrowers"])
api_router.include_router(loans.router, prefix="/loans", tags=["Loans"])
api_router.include_router(cases.router, prefix="/cases", tags=["Cases"])
api_router.include_router(communications.router, prefix="/communications", tags=["Communications"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(telephony.router, prefix="/telephony", tags=["Telephony"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
api_router.include_router(agent_performance.router, prefix="/agent-performance", tags=["Agent Performance"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(voice.router, prefix="/voice", tags=["Voice AI"])
