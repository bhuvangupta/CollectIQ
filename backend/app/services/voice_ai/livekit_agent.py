"""LiveKit-based Collection Agent using Sarvam AI and Groq.

This implements a real-time voice AI agent for loan collection calls using:
- LiveKit for WebRTC audio streaming
- Sarvam STT (Saarika v2) for Hindi speech recognition
- Groq LLM (Qwen3-32B) for Hinglish conversation AI
- Sarvam TTS (Bulbul v2) for Hindi voice synthesis
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

# LiveKit imports
LIVEKIT_AVAILABLE = False
SILERO_AVAILABLE = False

try:
    from livekit import agents, rtc, api
    from livekit.agents import AgentSession, Agent, JobContext
    from livekit.plugins import sarvam
    LIVEKIT_AVAILABLE = True

    # Silero VAD is optional
    try:
        from livekit.plugins import silero
        SILERO_AVAILABLE = True
    except ImportError:
        silero = None
        print("[LiveKit] Silero VAD not available, using default")

except ImportError as e:
    print(f"[LiveKit] Dependencies not installed: {e}")
    print("[LiveKit] Run: pip install livekit-agents livekit-plugins-sarvam")


@dataclass
class BorrowerInfo:
    """Borrower information for personalized collection calls."""
    name: str
    phone_number: str
    outstanding_amount: float
    emi_amount: float
    dpd: int  # Days past due
    loan_type: str = "Personal Loan"
    case_id: Optional[str] = None


# Default collection agent prompt
COLLECTION_AGENT_INSTRUCTIONS = """You are Priya, a friendly collections officer from CollectIQ Finance.

CRITICAL: You MUST respond in HINGLISH only (Hindi words written in Roman script mixed with English).
DO NOT respond in pure English. Use Hindi sentence structure with some English words mixed in.

HINGLISH EXAMPLES (follow this style exactly):
- "Namaste ji, main Priya hoon CollectIQ Finance se"
- "Aapka payment pending hai, kab tak kar sakte hain?"
- "Acha theek hai, toh 15 tarikh tak ho jayega na?"
- "Koi problem hai toh batayein, hum help kar sakte hain"
- "Dhanyavaad ji, payment ke baad mujhe call kar dena"

RULES:
1. ALWAYS use Hinglish - mix Hindi and English naturally
2. Keep responses SHORT - max 1-2 sentences
3. Use "aap", "ji" respectfully
4. Be polite but firm about payment
5. Never threaten

BORROWER INFO:
- Name: {borrower_name}
- Outstanding: Rs {outstanding_amount}
- EMI: Rs {emi_amount}
- Days Overdue: {dpd}
- Loan: {loan_type}

Remember: Respond ONLY in Hinglish, not English!
"""

WELCOME_MESSAGE = "Namaste {borrower_name} ji! Main Priya bol rahi hoon CollectIQ Finance se. Kaise hain aap?"


class CollectionAgent(Agent if LIVEKIT_AVAILABLE else object):
    """LiveKit-based collection agent using Sarvam AI."""

    def __init__(self, borrower: Optional[BorrowerInfo] = None):
        if not LIVEKIT_AVAILABLE:
            raise RuntimeError("LiveKit dependencies not installed")

        # Format instructions with borrower info
        if borrower:
            instructions = COLLECTION_AGENT_INSTRUCTIONS.format(
                borrower_name=borrower.name,
                outstanding_amount=borrower.outstanding_amount,
                emi_amount=borrower.emi_amount,
                dpd=borrower.dpd,
                loan_type=borrower.loan_type
            )
            self.welcome = WELCOME_MESSAGE.format(borrower_name=borrower.name)
        else:
            instructions = COLLECTION_AGENT_INSTRUCTIONS.format(
                borrower_name="Customer",
                outstanding_amount="[Amount]",
                emi_amount="[EMI]",
                dpd="[Days]",
                loan_type="Personal Loan"
            )
            self.welcome = WELCOME_MESSAGE.format(borrower_name="")

        self.borrower = borrower
        self.transcript = []
        self.start_time = datetime.utcnow()

        # Get providers
        stt = self._get_stt()
        llm = self._get_llm()
        tts = self._get_tts()

        # Print configuration
        print(f"[Agent Config] STT: Sarvam (saarika:v2) | LLM: Groq ({os.getenv('GROQ_MODEL', 'qwen/qwen3-32b')}) | TTS: Sarvam ({os.getenv('SARVAM_TTS_VOICE', 'anushka')}, bulbul:v2)")

        # Build agent config
        agent_config = {
            "instructions": instructions,
            "stt": stt,
            "llm": llm,
            "tts": tts
        }

        # Add VAD if silero is available
        if SILERO_AVAILABLE and silero:
            agent_config["vad"] = silero.VAD.load()

        super().__init__(**agent_config)

    def _get_stt(self):
        """Get Sarvam Speech-to-Text for Hindi."""
        return sarvam.STT(
            language="hi-IN",
            model="saarika:v2",
            api_key=os.getenv("SARVAM_API_KEY")
        )

    def _get_tts(self):
        """Get Sarvam Text-to-Speech for Hindi."""
        return sarvam.TTS(
            model="bulbul:v2",
            speaker=os.getenv("SARVAM_TTS_VOICE", "anushka").lower(),
            target_language_code="hi-IN",
            api_key=os.getenv("SARVAM_API_KEY")
        )

    def _get_llm(self):
        """Get Groq LLM with Qwen3 for Hindi/Hinglish."""
        from livekit.plugins import openai
        return openai.LLM(
            model=os.getenv("GROQ_MODEL", "qwen/qwen3-32b"),
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )

    async def on_enter(self):
        """Called when the agent joins the room. Generate welcome message."""
        await self.session.generate_reply(
            instructions=f"Greet the customer warmly: {self.welcome}"
        )

    def on_user_speech_committed(self, text: str):
        """Track user speech in transcript."""
        print(f"[STT] User said: {text}")  # Log what user said
        self.transcript.append({
            "role": "user",
            "content": text,
            "timestamp": datetime.utcnow().isoformat()
        })

    def on_agent_speech_committed(self, text: str):
        """Track agent speech in transcript."""
        print(f"[TTS] Speaking: {text}")  # Log what's being sent to TTS
        self.transcript.append({
            "role": "assistant",
            "content": text,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_transcript(self) -> str:
        """Get formatted transcript."""
        lines = []
        for turn in self.transcript:
            role = "Agent" if turn["role"] == "assistant" else "Customer"
            lines.append(f"{role}: {turn['content']}")
        return "\n".join(lines)

    def get_call_summary(self) -> Dict[str, Any]:
        """Generate call summary."""
        duration = int((datetime.utcnow() - self.start_time).total_seconds())

        # Determine disposition from transcript
        full_text = " ".join([t["content"].lower() for t in self.transcript])
        disposition = "contacted"

        if any(w in full_text for w in ["kar dunga", "kar denge", "pay kar", "bhej dunga"]):
            disposition = "promise_to_pay"
        elif any(w in full_text for w in ["baad mein", "callback", "kal call"]):
            disposition = "callback_requested"
        elif any(w in full_text for w in ["already paid", "pay kar diya"]):
            disposition = "payment_made"
        elif any(w in full_text for w in ["galat number", "wrong number"]):
            disposition = "wrong_number"

        return {
            "duration": duration,
            "transcript": self.transcript,
            "transcript_text": self.get_transcript(),
            "disposition": disposition,
            "borrower_name": self.borrower.name if self.borrower else None,
            "case_id": self.borrower.case_id if self.borrower else None
        }


class LiveKitService:
    """Service for managing LiveKit rooms and agents."""

    def __init__(self):
        self.api_key = os.getenv("LIVEKIT_API_KEY")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET")
        self.url = os.getenv("LIVEKIT_URL", "wss://your-project.livekit.cloud")

        if not all([self.api_key, self.api_secret]):
            print("[LiveKit] Warning: LIVEKIT_API_KEY and LIVEKIT_API_SECRET not set")

        # Store active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def create_token(
        self,
        room_name: str,
        participant_name: str,
        is_agent: bool = False,
        metadata: Optional[str] = None
    ) -> str:
        """Create a LiveKit access token for joining a room.

        Args:
            room_name: Name of the room to join
            participant_name: Name of the participant
            is_agent: Whether this is an agent (grants more permissions)
            metadata: Optional metadata to attach to participant

        Returns:
            JWT access token
        """
        if not LIVEKIT_AVAILABLE:
            raise RuntimeError("LiveKit not installed")

        from livekit.api import AccessToken, VideoGrants

        # Build grants
        grants = VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        )

        if is_agent:
            grants.agent = True
            grants.room_admin = True

        # Build token using builder pattern
        token = (
            AccessToken(self.api_key, self.api_secret)
            .with_identity(participant_name)
            .with_name(participant_name)
            .with_grants(grants)
            .with_ttl(timedelta(hours=6))  # Token valid for 6 hours
        )

        if metadata:
            token = token.with_metadata(metadata)

        return token.to_jwt()

    async def create_room(self, room_name: str) -> Dict[str, Any]:
        """Create a new LiveKit room.

        Args:
            room_name: Unique name for the room

        Returns:
            Room details including name and SID
        """
        if not LIVEKIT_AVAILABLE:
            raise RuntimeError("LiveKit not installed")

        lk_api = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        try:
            room = await lk_api.room.create_room(
                api.CreateRoomRequest(name=room_name)
            )
            return {
                "name": room.name,
                "sid": room.sid,
                "creation_time": room.creation_time
            }
        finally:
            await lk_api.aclose()

    async def delete_room(self, room_name: str) -> bool:
        """Delete a LiveKit room."""
        if not LIVEKIT_AVAILABLE:
            return False

        try:
            lk_api = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
            try:
                await lk_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
                return True
            finally:
                await lk_api.aclose()
        except Exception as e:
            print(f"[LiveKit] Error deleting room: {e}")
            return False

    async def create_room_with_metadata(self, room_name: str, metadata: str) -> Dict[str, Any]:
        """Create a LiveKit room with metadata.

        Args:
            room_name: Unique name for the room
            metadata: JSON string with room metadata

        Returns:
            Room details
        """
        if not LIVEKIT_AVAILABLE:
            raise RuntimeError("LiveKit not installed")

        lk_api = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        try:
            room = await lk_api.room.create_room(
                api.CreateRoomRequest(
                    name=room_name,
                    metadata=metadata
                )
            )
            return {
                "name": room.name,
                "sid": room.sid,
                "creation_time": room.creation_time
            }
        finally:
            await lk_api.aclose()

    async def dispatch_agent(self, room_name: str) -> bool:
        """Dispatch an agent to join a room.

        Args:
            room_name: Name of the room

        Returns:
            True if dispatch was successful
        """
        if not LIVEKIT_AVAILABLE:
            return False

        try:
            lk_api = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
            try:
                await lk_api.agent_dispatch.create_dispatch(
                    api.CreateAgentDispatchRequest(
                        room=room_name,
                        agent_name="collection-agent"
                    )
                )
                print(f"[LiveKit] Agent dispatched to room: {room_name}")
                return True
            finally:
                await lk_api.aclose()
        except Exception as e:
            print(f"[LiveKit] Error dispatching agent: {e}")
            return False

    async def start_collection_call(
        self,
        borrower: BorrowerInfo,
        room_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a collection call session.

        Creates a room and returns tokens for both user and agent.

        Args:
            borrower: Borrower information
            room_name: Optional room name (auto-generated if not provided)

        Returns:
            Room info with access tokens
        """
        import uuid

        if not room_name:
            room_name = f"collection-{borrower.case_id or uuid.uuid4().hex[:8]}"

        # Create room metadata with borrower info for agent
        room_metadata = json.dumps({
            "borrower_name": borrower.name,
            "phone_number": borrower.phone_number,
            "outstanding_amount": borrower.outstanding_amount,
            "emi_amount": borrower.emi_amount,
            "dpd": borrower.dpd,
            "loan_type": borrower.loan_type,
            "case_id": borrower.case_id
        })

        # Create the room with metadata
        room = await self.create_room_with_metadata(room_name, room_metadata)

        # Dispatch agent to the room
        await self.dispatch_agent(room_name)

        # Generate tokens
        user_token = self.create_token(
            room_name=room_name,
            participant_name=borrower.name,
            metadata=f'{{"type":"borrower","case_id":"{borrower.case_id}"}}'
        )

        agent_token = self.create_token(
            room_name=room_name,
            participant_name="Priya (AI Agent)",
            is_agent=True,
            metadata='{"type":"agent","name":"Priya"}'
        )

        # Store session info
        self.active_sessions[room_name] = {
            "room": room,
            "borrower": borrower,
            "start_time": datetime.utcnow().isoformat(),
            "status": "waiting"
        }

        return {
            "room_name": room_name,
            "room_sid": room["sid"],
            "livekit_url": self.url,
            "user_token": user_token,
            "agent_token": agent_token,
            "borrower": {
                "name": borrower.name,
                "case_id": borrower.case_id
            }
        }

    async def end_call(self, room_name: str) -> Dict[str, Any]:
        """End a call and get summary."""
        session = self.active_sessions.pop(room_name, None)

        if not session:
            return {"status": "not_found"}

        # Delete the room
        await self.delete_room(room_name)

        return {
            "status": "ended",
            "room_name": room_name,
            "duration": session.get("duration", 0),
            "borrower": session.get("borrower")
        }


# Singleton instance
_livekit_service: Optional[LiveKitService] = None


def get_livekit_service() -> LiveKitService:
    """Get singleton LiveKit service instance."""
    global _livekit_service
    if _livekit_service is None:
        _livekit_service = LiveKitService()
    return _livekit_service


# Agent entry point for LiveKit CLI
if LIVEKIT_AVAILABLE:
    from livekit.agents import Worker, WorkerOptions, cli

    async def collection_agent_entrypoint(ctx: JobContext):
        """Entry point for LiveKit agent worker.

        This is called when a new room needs an agent.
        """
        print(f"[Agent] Received job for room: {ctx.room.name}")

        # Connect to the room first
        await ctx.connect()
        print(f"[Agent] Connected to room: {ctx.room.name}")

        # Get borrower info from room metadata if available
        borrower = None
        room_metadata = ctx.room.metadata

        if room_metadata:
            try:
                data = json.loads(room_metadata)
                borrower = BorrowerInfo(
                    name=data.get("borrower_name", "Customer"),
                    phone_number=data.get("phone_number", ""),
                    outstanding_amount=float(data.get("outstanding_amount", 0)),
                    emi_amount=float(data.get("emi_amount", 0)),
                    dpd=int(data.get("dpd", 0)),
                    loan_type=data.get("loan_type", "Personal Loan"),
                    case_id=data.get("case_id")
                )
                print(f"[Agent] Borrower: {borrower.name}, DPD: {borrower.dpd}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[Agent] Error parsing room metadata: {e}")

        # Create agent
        agent = CollectionAgent(borrower=borrower)

        # Create session and start it
        session = AgentSession()
        await session.start(
            room=ctx.room,
            agent=agent
        )

        print(f"[Agent] Session started")

        # Wait for room to disconnect (participant leaves or room closes)
        @ctx.room.on("disconnected")
        def on_disconnected():
            summary = agent.get_call_summary()
            print(f"[Agent] Call ended: {summary}")

        # Keep the agent running until the room closes
        # The session handles the conversation lifecycle
        disconnect_future = asyncio.Future()

        @ctx.room.on("disconnected")
        def on_room_disconnected():
            if not disconnect_future.done():
                disconnect_future.set_result(True)

        # Wait for disconnect or timeout (30 min max call)
        try:
            await asyncio.wait_for(disconnect_future, timeout=1800)
        except asyncio.TimeoutError:
            print("[Agent] Call timeout (30 min), ending session")

        summary = agent.get_call_summary()
        print(f"[Agent] Call ended: {summary}")


def run_agent_worker():
    """Run the LiveKit agent worker.

    This should be run as a separate process:
    python -m app.services.voice_ai.livekit_agent
    """
    if not LIVEKIT_AVAILABLE:
        print("LiveKit dependencies not installed!")
        return

    # Print startup configuration
    print("\n" + "="*60)
    print("🎙️  CollectIQ Voice Agent Starting...")
    print("="*60)
    print(f"  STT: Sarvam (saarika:v2)")
    print(f"  LLM: Groq ({os.getenv('GROQ_MODEL', 'qwen/qwen3-32b')})")
    print(f"  TTS: Sarvam ({os.getenv('SARVAM_TTS_VOICE', 'anushka')}, bulbul:v2)")
    print(f"  LiveKit: {os.getenv('LIVEKIT_URL', 'not set')}")
    print("="*60 + "\n")

    # Run the worker with CLI
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=collection_agent_entrypoint,
            agent_name="collection-agent"  # Must match dispatch agent_name
        )
    )


if __name__ == "__main__":
    run_agent_worker()
