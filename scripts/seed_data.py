"""Seed database with sample data for development."""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import random

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Import models
import sys
sys.path.insert(0, '/app')

from app.core.config import settings
from app.models.organization import Organization
from app.models.user import User
from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.case import Case, CaseNote
from app.models.communication import Communication
from app.models.payment import Payment, PromiseToPay


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Sample data
ORGANIZATION_DATA = [
    {
        "name": "ABC Finance Ltd",
        "code": "ABCFIN",
        "type": "nbfc",
        "settings": {"default_language": "hi", "working_hours": "9:00-18:00"}
    },
    {
        "name": "XYZ Collections Agency",
        "code": "XYZCOL",
        "type": "agency",
        "settings": {"default_language": "en", "working_hours": "8:00-20:00"}
    }
]

USER_DATA = [
    {"email": "admin@collectiq.com", "full_name": "Admin User", "role": "admin"},
    {"email": "manager@collectiq.com", "full_name": "Manager User", "role": "manager"},
    {"email": "agent1@collectiq.com", "full_name": "Agent One", "role": "agent"},
    {"email": "agent2@collectiq.com", "full_name": "Agent Two", "role": "agent"},
    {"email": "agent3@collectiq.com", "full_name": "Agent Three", "role": "agent"},
]

BORROWER_NAMES = [
    ("Rahul", "Sharma"), ("Priya", "Patel"), ("Amit", "Kumar"),
    ("Neha", "Singh"), ("Vikram", "Gupta"), ("Anjali", "Verma"),
    ("Rajesh", "Mehta"), ("Sunita", "Agarwal"), ("Deepak", "Joshi"),
    ("Kavita", "Reddy"), ("Suresh", "Nair"), ("Meena", "Iyer"),
    ("Arun", "Pillai"), ("Rekha", "Das"), ("Manoj", "Choudhury"),
]

LOAN_TYPES = ["Personal Loan", "Business Loan", "Two Wheeler", "Consumer Durable", "Gold Loan"]
CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad"]
STATES = ["Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "Telangana", "Maharashtra", "West Bengal", "Gujarat"]


async def seed_database():
    """Seed the database with sample data."""
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("Seeding database...")

        # Create organizations
        orgs = []
        for org_data in ORGANIZATION_DATA:
            org = Organization(
                id=uuid.uuid4(),
                name=org_data["name"],
                code=org_data["code"],
                type=org_data["type"],
                is_active=True,
                settings=org_data["settings"]
            )
            session.add(org)
            orgs.append(org)
            print(f"  Created organization: {org.name}")

        await session.flush()

        # Create users for first org
        org = orgs[0]
        users = []
        for user_data in USER_DATA:
            user = User(
                id=uuid.uuid4(),
                org_id=org.id,
                email=user_data["email"],
                hashed_password=pwd_context.hash("password123"),
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=True
            )
            session.add(user)
            users.append(user)
            print(f"  Created user: {user.email}")

        await session.flush()

        # Create borrowers and loans
        agents = [u for u in users if u.role == "agent"]

        for i, (first_name, last_name) in enumerate(BORROWER_NAMES):
            # Create borrower
            phone = f"+9198{random.randint(10000000, 99999999)}"
            city_idx = i % len(CITIES)

            borrower = Borrower(
                id=uuid.uuid4(),
                org_id=org.id,
                external_id=f"BOR{str(i+1).zfill(6)}",
                first_name=first_name,
                last_name=last_name,
                phone_primary=phone,
                email=f"{first_name.lower()}.{last_name.lower()}@email.com",
                address_city=CITIES[city_idx],
                address_state=STATES[city_idx],
                address_pincode=f"{random.randint(100000, 999999)}",
                preferred_language=random.choice(["hi", "en"]),
                preferred_contact_time="morning" if i % 3 == 0 else "evening",
                do_not_call=False
            )
            session.add(borrower)
            await session.flush()

            # Create loan
            principal = Decimal(random.randint(50000, 500000))
            emi = principal / Decimal(random.randint(12, 36))
            dpd = random.randint(0, 180)

            # Determine bucket based on DPD
            if dpd == 0:
                bucket = "current"
            elif dpd <= 30:
                bucket = "bucket_1"
            elif dpd <= 60:
                bucket = "bucket_2"
            elif dpd <= 90:
                bucket = "bucket_3"
            else:
                bucket = "npa"

            loan = Loan(
                id=uuid.uuid4(),
                org_id=org.id,
                borrower_id=borrower.id,
                external_id=f"LN{str(i+1).zfill(8)}",
                loan_type=random.choice(LOAN_TYPES),
                principal_amount=principal,
                outstanding_amount=principal * Decimal(random.uniform(0.3, 1.0)),
                emi_amount=emi.quantize(Decimal("0.01")),
                interest_rate=Decimal(random.uniform(10, 18)).quantize(Decimal("0.01")),
                tenure_months=random.randint(12, 36),
                disbursement_date=datetime.utcnow() - timedelta(days=random.randint(60, 365)),
                dpd=dpd,
                bucket=bucket,
                status="active" if dpd < 180 else "default"
            )
            session.add(loan)
            await session.flush()

            # Create case for overdue loans
            if dpd > 0:
                agent = random.choice(agents)

                # Determine priority based on amount and DPD
                if loan.outstanding_amount > 200000 or dpd > 90:
                    priority = "high"
                elif loan.outstanding_amount > 100000 or dpd > 60:
                    priority = "medium"
                else:
                    priority = "low"

                case = Case(
                    id=uuid.uuid4(),
                    org_id=org.id,
                    loan_id=loan.id,
                    borrower_id=borrower.id,
                    assigned_to=agent.id,
                    status="open",
                    priority=priority,
                    next_action_date=datetime.utcnow() + timedelta(days=random.randint(1, 7)),
                    attempt_count=random.randint(0, 5),
                    last_contacted_at=datetime.utcnow() - timedelta(days=random.randint(1, 14)) if random.random() > 0.3 else None
                )
                session.add(case)
                await session.flush()

                # Add some communications
                if case.attempt_count > 0:
                    for j in range(min(case.attempt_count, 3)):
                        comm_type = random.choice(["call", "sms", "whatsapp"])
                        comm = Communication(
                            id=uuid.uuid4(),
                            org_id=org.id,
                            case_id=case.id,
                            borrower_id=borrower.id,
                            loan_id=loan.id,
                            type=comm_type,
                            direction="outbound",
                            status="completed" if random.random() > 0.2 else "failed",
                            channel_id=f"{comm_type}_{uuid.uuid4().hex[:8]}",
                            duration=random.randint(30, 300) if comm_type == "call" else None,
                            outcome=random.choice(["contacted", "no_answer", "promise_to_pay", "callback"]) if comm_type == "call" else "delivered",
                            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                        )
                        session.add(comm)

                # Add some case notes
                if random.random() > 0.5:
                    note = CaseNote(
                        id=uuid.uuid4(),
                        case_id=case.id,
                        user_id=agent.id,
                        note=random.choice([
                            "Borrower promised to pay by end of week",
                            "Not reachable, will try again tomorrow",
                            "Requested callback in evening hours",
                            "Discussed payment plan options",
                            "Borrower facing temporary financial difficulty"
                        ])
                    )
                    session.add(note)

                # Add promise to pay for some cases
                if random.random() > 0.7:
                    ptp = PromiseToPay(
                        id=uuid.uuid4(),
                        org_id=org.id,
                        case_id=case.id,
                        borrower_id=borrower.id,
                        loan_id=loan.id,
                        promised_amount=emi.quantize(Decimal("0.01")),
                        promised_date=datetime.utcnow() + timedelta(days=random.randint(1, 14)),
                        status=random.choice(["pending", "kept", "broken"]),
                        recorded_by=agent.id
                    )
                    session.add(ptp)

            print(f"  Created borrower: {first_name} {last_name} with loan {loan.external_id}")

        await session.commit()
        print("\nDatabase seeded successfully!")
        print(f"  Organizations: {len(orgs)}")
        print(f"  Users: {len(users)}")
        print(f"  Borrowers/Loans: {len(BORROWER_NAMES)}")
        print("\nDefault login: admin@collectiq.com / password123")


if __name__ == "__main__":
    asyncio.run(seed_database())
