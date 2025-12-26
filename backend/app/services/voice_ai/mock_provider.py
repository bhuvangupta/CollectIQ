"""Mock Voice AI provider for development/testing."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import (
    VoiceAIProvider,
    AgentConfig,
    CallResult,
    CallDetails,
    CallStatus,
    CallDisposition,
    BorrowerContext
)


class MockVoiceAIProvider(VoiceAIProvider):
    """Mock provider for development and testing.

    Simulates voice AI calls without actually making them.
    """

    def __init__(self):
        self._agents: Dict[str, AgentConfig] = {}
        self._calls: Dict[str, Dict[str, Any]] = {}

    @property
    def provider_name(self) -> str:
        return "mock"

    async def create_agent(self, config: AgentConfig) -> Dict[str, Any]:
        """Create a mock agent."""
        agent_id = f"mock_agent_{uuid.uuid4().hex[:8]}"
        self._agents[agent_id] = config
        return {
            "agent_id": agent_id,
            "name": config.name,
            "status": "created"
        }

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get mock agent details."""
        if agent_id in self._agents:
            config = self._agents[agent_id]
            return {
                "agent_id": agent_id,
                "name": config.name,
                "language": config.language,
                "voice": config.voice,
                "status": "active"
            }
        return None

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all mock agents."""
        return [
            {
                "agent_id": agent_id,
                "name": config.name,
                "status": "active"
            }
            for agent_id, config in self._agents.items()
        ]

    async def make_call(
        self,
        agent_id: str,
        borrower: BorrowerContext
    ) -> CallResult:
        """Simulate making a call."""
        call_id = f"mock_call_{uuid.uuid4().hex[:8]}"

        self._calls[call_id] = {
            "agent_id": agent_id,
            "borrower": borrower,
            "status": CallStatus.QUEUED,
            "started_at": datetime.utcnow(),
            "duration": 0
        }

        print(f"[Mock Voice AI] Simulated call {call_id} to {borrower.phone_number}")
        print(f"  Borrower: {borrower.name}")
        print(f"  Amount: Rs {borrower.outstanding_amount}")
        print(f"  DPD: {borrower.dpd} days")

        return CallResult(
            success=True,
            call_id=call_id,
            message=f"Mock call initiated to {borrower.phone_number}"
        )

    async def stop_call(self, call_id: str) -> bool:
        """Stop a mock call."""
        if call_id in self._calls:
            self._calls[call_id]["status"] = CallStatus.CANCELLED
            return True
        return False

    async def get_call_details(self, call_id: str) -> CallDetails:
        """Get mock call details."""
        if call_id in self._calls:
            call = self._calls[call_id]
            return CallDetails(
                call_id=call_id,
                status=call["status"],
                duration=call.get("duration", 45),
                recording_url=None,
                transcript="[Mock] Simulated conversation transcript",
                disposition=CallDisposition.CONTACTED,
                summary="Mock call completed successfully. Borrower contacted."
            )

        return CallDetails(
            call_id=call_id,
            status=CallStatus.COMPLETED,
            duration=45,
            transcript="[Mock] Sample transcript - borrower agreed to pay",
            disposition=CallDisposition.PROMISE_TO_PAY,
            summary="Borrower promised to pay within 3 days"
        )

    def parse_webhook(self, payload: Dict[str, Any]) -> CallDetails:
        """Parse mock webhook payload."""
        return CallDetails(
            call_id=payload.get("call_id", "unknown"),
            status=CallStatus.COMPLETED,
            duration=payload.get("duration", 60),
            transcript=payload.get("transcript", "Mock transcript"),
            disposition=CallDisposition.CONTACTED
        )

    async def health_check(self) -> bool:
        """Mock health check always succeeds."""
        return True
