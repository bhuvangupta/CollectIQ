"""Base interface for Voice AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


class CallStatus(str, Enum):
    """Standard call status values."""
    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    CANCELLED = "cancelled"


class CallDisposition(str, Enum):
    """Standard call disposition values."""
    PROMISE_TO_PAY = "promise_to_pay"
    CALLBACK_REQUESTED = "callback_requested"
    PAYMENT_MADE = "payment_made"
    DISPUTE = "dispute"
    WRONG_NUMBER = "wrong_number"
    NOT_INTERESTED = "not_interested"
    CONTACTED = "contacted"
    VOICEMAIL = "voicemail"


@dataclass
class AgentConfig:
    """Configuration for a voice AI agent."""
    name: str
    system_prompt: str
    welcome_message: str
    language: str = "hi"  # Hindi/Hinglish
    voice: str = "female"
    voice_name: Optional[str] = None
    webhook_url: Optional[str] = None
    max_call_duration: int = 300  # seconds
    silence_timeout: int = 10  # seconds
    interruption_threshold: int = 100  # ms
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CallResult:
    """Result from initiating a call."""
    success: bool
    call_id: Optional[str] = None  # External call ID
    execution_id: Optional[str] = None  # Provider's execution ID
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CallDetails:
    """Details of a call from webhook or query."""
    call_id: str
    status: CallStatus
    duration: Optional[int] = None  # seconds
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    transcript_segments: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None
    disposition: Optional[CallDisposition] = None
    user_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BorrowerContext:
    """Context about the borrower for collection calls."""
    name: str
    phone_number: str
    outstanding_amount: float
    emi_amount: float
    dpd: int  # Days past due
    loan_type: str = "Personal Loan"
    case_id: Optional[str] = None
    loan_id: Optional[str] = None
    last_payment_date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VoiceAIProvider(ABC):
    """Abstract base class for Voice AI providers.

    Implement this interface to add support for new voice AI platforms
    like Bolna, Vapi, Retell, etc.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'bolna', 'vapi', 'retell')."""
        pass

    @abstractmethod
    async def create_agent(self, config: AgentConfig) -> Dict[str, Any]:
        """Create a new voice AI agent.

        Args:
            config: Agent configuration

        Returns:
            Dict with agent_id and other provider-specific data
        """
        pass

    @abstractmethod
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent details.

        Args:
            agent_id: The agent identifier

        Returns:
            Agent configuration and status
        """
        pass

    @abstractmethod
    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent configuration.

        Args:
            agent_id: The agent identifier
            updates: Fields to update

        Returns:
            Updated agent data
        """
        pass

    @abstractmethod
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent.

        Args:
            agent_id: The agent identifier

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def make_call(
        self,
        agent_id: str,
        borrower: BorrowerContext,
        from_phone: Optional[str] = None
    ) -> CallResult:
        """Initiate an outbound call.

        Args:
            agent_id: The agent to use for the call
            borrower: Borrower context for the call
            from_phone: Optional caller ID

        Returns:
            CallResult with call_id and status
        """
        pass

    @abstractmethod
    async def stop_call(self, call_id: str) -> bool:
        """Stop an active or queued call.

        Args:
            call_id: The call identifier

        Returns:
            True if stopped successfully
        """
        pass

    @abstractmethod
    async def get_call_details(self, call_id: str) -> CallDetails:
        """Get details of a call.

        Args:
            call_id: The call identifier

        Returns:
            CallDetails with status, transcript, recording, etc.
        """
        pass

    @abstractmethod
    def parse_webhook(self, payload: Dict[str, Any]) -> CallDetails:
        """Parse webhook payload from the provider.

        Args:
            payload: Raw webhook payload

        Returns:
            Normalized CallDetails
        """
        pass

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents (optional, may not be supported by all providers).

        Returns:
            List of agents
        """
        raise NotImplementedError("list_agents not supported by this provider")

    async def health_check(self) -> bool:
        """Check if the provider is accessible.

        Returns:
            True if healthy
        """
        return True
