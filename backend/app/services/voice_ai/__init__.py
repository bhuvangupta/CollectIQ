"""Voice AI provider abstraction for collection calls."""

from .base import (
    VoiceAIProvider,
    AgentConfig,
    CallResult,
    CallDetails,
    CallStatus,
    CallDisposition,
    BorrowerContext
)
from .factory import get_voice_ai_provider

__all__ = [
    "VoiceAIProvider",
    "AgentConfig",
    "CallResult",
    "CallDetails",
    "CallStatus",
    "CallDisposition",
    "BorrowerContext",
    "get_voice_ai_provider"
]
