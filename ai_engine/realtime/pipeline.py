"""Voice conversation pipeline for real-time AI interactions."""

import asyncio
import os
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass, field

from .audio_buffer import AudioBuffer
from .audio_utils import pcm16_to_float32, create_wav_from_pcm
from .vad import SileroVAD, VADResult, create_vad


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    audio_duration_ms: float = 0


@dataclass
class PipelineResult:
    """Result from processing user audio."""
    user_text: Optional[str] = None
    ai_response: Optional[str] = None
    action: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    should_end: bool = False
    is_processing: bool = False


class VoicePipeline:
    """Orchestrates real-time voice conversation.

    Flow:
    1. Receive audio chunks from client
    2. Accumulate until VAD detects speech end
    3. Transcribe complete utterance via STT
    4. Generate AI response via DialogManager
    5. Stream TTS audio back to client
    """

    def __init__(
        self,
        session_id: str,
        context: Dict[str, Any],
        stt_service=None,
        tts_service=None,
        dialog_manager=None,
        sample_rate: int = 16000,
        use_silero_vad: bool = True
    ):
        """Initialize voice pipeline.

        Args:
            session_id: Unique session identifier
            context: Borrower/loan context for dialog
            stt_service: STT service instance
            tts_service: TTS service instance
            dialog_manager: Dialog manager instance
            sample_rate: Expected audio sample rate
            use_silero_vad: Whether to use Silero VAD (vs energy-based)
        """
        self.session_id = session_id
        self.context = context
        self.stt_service = stt_service
        self.tts_service = tts_service
        self.dialog_manager = dialog_manager
        self.sample_rate = sample_rate

        # Audio processing
        self.audio_buffer = AudioBuffer(sample_rate=sample_rate)

        # Get VAD settings from environment or use fast defaults
        min_silence_ms = int(os.getenv("VAD_MIN_SILENCE_MS", "500"))
        min_speech_ms = int(os.getenv("VAD_MIN_SPEECH_MS", "200"))

        self.vad = create_vad(
            use_silero=use_silero_vad,
            min_speech_ms=min_speech_ms,
            min_silence_ms=min_silence_ms,
            sample_rate=sample_rate
        )

        # Conversation state
        self.conversation_history: List[Dict[str, str]] = []
        self.is_ai_speaking = False
        self.is_processing = False
        self.is_interrupted = False

        # Language (default to Hindi for Hinglish)
        self.language = context.get("language", "hi")

    def interrupt(self) -> bool:
        """Interrupt AI speech (barge-in).

        Returns:
            True if interrupt was triggered, False if nothing to interrupt
        """
        if self.is_ai_speaking:
            self.is_interrupted = True
            self.is_ai_speaking = False
            print(f"[{self.session_id}] User interrupted AI speech")
            return True
        return False

    async def process_audio_chunk(self, audio_chunk: bytes) -> Optional[PipelineResult]:
        """Process incoming audio chunk.

        Args:
            audio_chunk: Raw 16-bit PCM audio bytes

        Returns:
            PipelineResult if speech ended and processing complete, else None
        """
        # Allow barge-in: if AI is speaking, interrupt first
        if self.is_ai_speaking:
            self.interrupt()

        # Add to buffer
        self.audio_buffer.append(audio_chunk)

        # Convert to float32 for VAD
        float_audio = pcm16_to_float32(audio_chunk)

        # Check VAD
        vad_result = self.vad.process(float_audio)

        # If speech ended, process the complete utterance
        if vad_result.is_speech_end:
            return await self._process_complete_utterance()

        return None

    async def _process_complete_utterance(self) -> PipelineResult:
        """Process a complete user utterance.

        Returns:
            PipelineResult with transcription and AI response
        """
        self.is_processing = True

        try:
            # Get complete audio from buffer
            pcm_audio = self.audio_buffer.get_and_reset()
            self.vad.reset()

            if not pcm_audio:
                return PipelineResult(is_processing=False)

            # Convert to WAV for STT
            wav_audio = create_wav_from_pcm(pcm_audio, self.sample_rate)

            # Transcribe
            user_text = await self._transcribe(wav_audio)

            if not user_text or not user_text.strip():
                # For testing: use a default phrase if audio couldn't be transcribed
                if os.getenv("STT_TEST_FALLBACK"):
                    user_text = "Haan, main sun raha hoon"
                else:
                    return PipelineResult(is_processing=False)

            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_text
            })

            # Generate AI response
            ai_result = await self._generate_response()

            ai_response = ai_result.get("response", "")
            action = ai_result.get("action")
            entities = ai_result.get("entities", {})
            should_end = ai_result.get("should_end", False)

            # Add AI response to history
            if ai_response:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": ai_response
                })

            return PipelineResult(
                user_text=user_text,
                ai_response=ai_response,
                action=action,
                entities=entities,
                should_end=should_end,
                is_processing=False
            )

        except Exception as e:
            print(f"Error processing utterance: {e}")
            return PipelineResult(is_processing=False)

        finally:
            self.is_processing = False

    async def _transcribe(self, wav_audio: bytes) -> str:
        """Transcribe audio using STT service.

        Args:
            wav_audio: WAV audio bytes

        Returns:
            Transcribed text
        """
        if not self.stt_service:
            print("Warning: No STT service available")
            return ""

        try:
            result = await self.stt_service.transcribe_bytes(
                wav_audio,
                language=self.language
            )
            return result.get("text", "")
        except Exception as e:
            print(f"STT error: {e}")
            return ""

    async def _generate_response(self) -> Dict[str, Any]:
        """Generate AI response using dialog manager.

        Returns:
            Dialog response with text, action, entities
        """
        if not self.dialog_manager:
            print("Warning: No dialog manager available")
            return {"response": "I'm sorry, I couldn't process that."}

        try:
            result = await self.dialog_manager.generate_response(
                self.conversation_history,
                self.context,
                self.language
            )
            return result
        except Exception as e:
            print(f"Dialog error: {e}")
            return {"response": "I'm sorry, could you repeat that?"}

    async def generate_tts_stream(
        self,
        text: str,
        voice: str = "female"
    ) -> AsyncGenerator[bytes, None]:
        """Generate TTS audio stream for text.

        Args:
            text: Text to synthesize
            voice: Voice type ("male" or "female")

        Yields:
            Audio chunks (MP3 format)
        """
        if not self.tts_service:
            print("Warning: No TTS service available")
            return

        self.is_ai_speaking = True
        self.is_interrupted = False

        try:
            async for chunk in self.tts_service.synthesize_stream(
                text,
                voice=voice,
                language=self.language
            ):
                # Check for interrupt before yielding each chunk
                if self.is_interrupted:
                    print(f"[{self.session_id}] TTS stream interrupted")
                    break
                yield chunk
        except Exception as e:
            print(f"TTS error: {e}")
        finally:
            self.is_ai_speaking = False

    async def generate_greeting(self) -> AsyncGenerator[bytes, None]:
        """Generate initial AI greeting.

        Yields:
            Audio chunks for greeting
        """
        borrower_name = self.context.get("borrower_name", "")

        # Generate appropriate greeting based on context
        if self.language == "hi":
            greeting = f"Namaste! Kya main {borrower_name} ji se baat kar sakti hoon?"
        else:
            greeting = f"Hello! Am I speaking with {borrower_name}?"

        # Add greeting to history
        self.conversation_history.append({
            "role": "assistant",
            "content": greeting
        })

        async for chunk in self.generate_tts_stream(greeting):
            yield chunk

    def set_context(self, context: Dict[str, Any]) -> None:
        """Update conversation context.

        Args:
            context: New context to merge
        """
        self.context.update(context)
        if "language" in context:
            self.language = context["language"]

    def get_transcript(self) -> List[Dict[str, str]]:
        """Get full conversation transcript.

        Returns:
            List of conversation turns
        """
        return self.conversation_history.copy()

    def reset(self) -> None:
        """Reset pipeline state for new conversation."""
        self.audio_buffer.reset()
        self.vad.reset()
        self.conversation_history = []
        self.is_ai_speaking = False
        self.is_processing = False
        self.is_interrupted = False
