"""Seed database with sample data for development."""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import random
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from app.core.config import settings
from app.models.organization import Organization
from app.models.user import User
from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.case import Case, CaseNote


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Sample data
ORGANIZATION_DATA = [
    {
        "name": "ABC Finance Ltd",
        "slug": "abc-finance",
        "org_type": "nbfc",
    },
    {
        "name": "XYZ Collections Agency",
        "slug": "xyz-collections",
        "org_type": "agency",
    }
]

USER_DATA = [
    {"email": "admin@collectiq.com", "first_name": "Admin", "last_name": "User", "role": "admin"},
    {"email": "manager@collectiq.com", "first_name": "Manager", "last_name": "User", "role": "manager"},
    {"email": "agent1@collectiq.com", "first_name": "Agent", "last_name": "One", "role": "agent"},
    {"email": "agent2@collectiq.com", "first_name": "Agent", "last_name": "Two", "role": "agent"},
    {"email": "agent3@collectiq.com", "first_name": "Agent", "last_name": "Three", "role": "agent"},
]

BORROWER_NAMES = [
    ("Rahul", "Sharma"), ("Priya", "Patel"), ("Amit", "Kumar"),
    ("Neha", "Singh"), ("Vikram", "Gupta"), ("Anjali", "Verma"),
    ("Rajesh", "Mehta"), ("Sunita", "Agarwal"), ("Deepak", "Joshi"),
    ("Kavita", "Reddy"), ("Suresh", "Nair"), ("Meena", "Iyer"),
    ("Arun", "Pillai"), ("Rekha", "Das"), ("Manoj", "Choudhury"),
]

LOAN_TYPES = ["personal", "business", "auto", "home", "gold"]
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
                slug=org_data["slug"],
                org_type=org_data["org_type"],
                is_active=True,
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
                organization_id=org.id,
                email=user_data["email"],
                hashed_password=pwd_context.hash("password123"),
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
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
                organization_id=org.id,
                external_id=f"BOR{str(i+1).zfill(6)}",
                first_name=first_name,
                last_name=last_name,
                primary_phone=phone,
                email=f"{first_name.lower()}.{last_name.lower()}@email.com",
                city=CITIES[city_idx],
                state=STATES[city_idx],
                pincode=f"{random.randint(100000, 999999)}",
                preferred_language=random.choice(["hi", "en"]),
                preferred_contact_time=random.choice(["morning", "afternoon", "evening"]),
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
                bucket = "1-30"
            elif dpd <= 60:
                bucket = "31-60"
            elif dpd <= 90:
                bucket = "61-90"
            else:
                bucket = "90+"

            loan = Loan(
                id=uuid.uuid4(),
                organization_id=org.id,
                borrower_id=borrower.id,
                external_loan_id=f"LN{str(i+1).zfill(8)}",
                loan_type=random.choice(LOAN_TYPES),
                principal_amount=principal,
                total_outstanding=principal * Decimal(random.uniform(0.3, 1.0)),
                emi_amount=emi.quantize(Decimal("0.01")),
                interest_rate=Decimal(random.uniform(10, 18)).quantize(Decimal("0.01")),
                tenure_months=random.randint(12, 36),
                disbursement_date=datetime.utcnow().date() - timedelta(days=random.randint(60, 365)),
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
                if loan.total_outstanding > 200000 or dpd > 90:
                    priority = 5
                elif loan.total_outstanding > 100000 or dpd > 60:
                    priority = 3
                else:
                    priority = 1

                case = Case(
                    id=uuid.uuid4(),
                    organization_id=org.id,
                    loan_id=loan.id,
                    case_number=f"CASE{str(i+1).zfill(8)}",
                    status="open",
                    priority=priority,
                    next_follow_up=datetime.utcnow() + timedelta(days=random.randint(1, 7)),
                    total_attempts=random.randint(0, 5),
                    last_contact_date=datetime.utcnow() - timedelta(days=random.randint(1, 14)) if random.random() > 0.3 else None
                )
                session.add(case)
                await session.flush()

                # Add some case notes
                if random.random() > 0.5:
                    note = CaseNote(
                        id=uuid.uuid4(),
                        case_id=case.id,
                        author_id=agent.id,
                        content=random.choice([
                            "Borrower promised to pay by end of week",
                            "Not reachable, will try again tomorrow",
                            "Requested callback in evening hours",
                            "Discussed payment plan options",
                            "Borrower facing temporary financial difficulty"
                        ])
                    )
                    session.add(note)

            print(f"  Created borrower: {first_name} {last_name} with loan LN{str(i+1).zfill(8)}")

        await session.commit()
        print("\nDatabase seeded successfully!")
        print(f"  Organizations: {len(orgs)}")
        print(f"  Users: {len(users)}")
        print(f"  Borrowers/Loans: {len(BORROWER_NAMES)}")
        print("\nDefault login: admin@collectiq.com / password123")


if __name__ == "__main__":
    asyncio.run(seed_database())
