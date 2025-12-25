from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json
import uuid

from voice.stt_service import STTService
from voice.tts_service import TTSService
from dialog.manager import DialogManager
from realtime.pipeline import VoicePipeline


# Initialize services
stt_service: Optional[STTService] = None
tts_service: Optional[TTSService] = None
dialog_manager: Optional[DialogManager] = None

# Active voice sessions
voice_sessions: Dict[str, VoicePipeline] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global stt_service, tts_service, dialog_manager

    print("Initializing AI Engine services...")

    # Initialize services
    stt_service = STTService()
    tts_service = TTSService()
    dialog_manager = DialogManager()

    print("AI Engine ready!")

    yield

    # Cleanup
    print("Shutting down AI Engine...")


app = FastAPI(
    title="Loan Collection AI Engine",
    description="AI services for speech recognition, synthesis, and dialog management",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class TranscribeRequest(BaseModel):
    audio_url: str
    language: str = "hi"


class TranscribeResponse(BaseModel):
    text: str
    segments: List[Dict[str, Any]]
    language: str
    confidence: float


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "default"
    language: str = "hi"


class DialogRequest(BaseModel):
    conversation_history: List[Dict[str, str]]
    context: Dict[str, Any]
    language: str = "hi"


class DialogResponse(BaseModel):
    response: str
    action: Optional[str] = None
    entities: Dict[str, Any] = {}
    should_end: bool = False


class SentimentRequest(BaseModel):
    text: str


class SentimentResponse(BaseModel):
    sentiment: str
    score: float


class SummarizeRequest(BaseModel):
    transcript: str
    language: str = "en"


class SummarizeResponse(BaseModel):
    summary: str
    key_points: List[str]
    action_items: List[str]
    entities: Dict[str, List[str]]


class ComplianceRequest(BaseModel):
    transcript: str


class ComplianceResponse(BaseModel):
    flags: List[Dict[str, str]]
    is_compliant: bool


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "stt": stt_service is not None,
            "tts": tts_service is not None,
            "dialog": dialog_manager is not None,
        }
    }


# STT endpoints
@app.post("/stt/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """Transcribe audio from URL."""
    if not stt_service:
        raise HTTPException(status_code=503, detail="STT service not available")

    try:
        result = await stt_service.transcribe(request.audio_url, request.language)
        return TranscribeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stt/transcribe-file")
async def transcribe_audio_file(
    file: UploadFile = File(...),
    language: str = "hi"
):
    """Transcribe uploaded audio file."""
    if not stt_service:
        raise HTTPException(status_code=503, detail="STT service not available")

    try:
        audio_data = await file.read()
        result = await stt_service.transcribe_bytes(audio_data, language)
        return TranscribeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TTS endpoints
@app.post("/tts/synthesize")
async def synthesize_speech(request: SynthesizeRequest):
    """Convert text to speech."""
    if not tts_service:
        raise HTTPException(status_code=503, detail="TTS service not available")

    try:
        audio_data = await tts_service.synthesize(
            request.text,
            request.voice,
            request.language
        )
        from fastapi.responses import Response
        return Response(content=audio_data, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Dialog endpoints
@app.post("/dialog/respond", response_model=DialogResponse)
async def generate_dialog_response(request: DialogRequest):
    """Generate AI response for collection dialog."""
    if not dialog_manager:
        raise HTTPException(status_code=503, detail="Dialog service not available")

    try:
        result = await dialog_manager.generate_response(
            request.conversation_history,
            request.context,
            request.language
        )
        return DialogResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Analysis endpoints
@app.post("/analyze/sentiment", response_model=SentimentResponse)
async def analyze_sentiment(request: SentimentRequest):
    """Analyze sentiment of text."""
    if not dialog_manager:
        raise HTTPException(status_code=503, detail="Dialog service not available")

    try:
        result = await dialog_manager.analyze_sentiment(request.text)
        return SentimentResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/summarize", response_model=SummarizeResponse)
async def summarize_call(request: SummarizeRequest):
    """Summarize a call transcript."""
    if not dialog_manager:
        raise HTTPException(status_code=503, detail="Dialog service not available")

    try:
        result = await dialog_manager.summarize_transcript(
            request.transcript,
            request.language
        )
        return SummarizeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/compliance", response_model=ComplianceResponse)
async def check_compliance(request: ComplianceRequest):
    """Check transcript for compliance issues."""
    if not dialog_manager:
        raise HTTPException(status_code=503, detail="Dialog service not available")

    try:
        result = await dialog_manager.check_compliance(request.transcript)
        return ComplianceResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Voice WebSocket endpoint
@app.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    """Real-time voice conversation WebSocket.

    Protocol:
    - Client sends: binary audio chunks (16-bit PCM, 16kHz, mono)
    - Server sends: binary audio chunks (MP3 from TTS) or JSON messages

    JSON message types from server:
    - {"type": "greeting_complete"}: AI greeting finished
    - {"type": "processing"}: AI is processing user speech
    - {"type": "transcript", "role": "user"|"assistant", "text": "..."}: Transcript update
    - {"type": "response_complete", "action": "...", "should_end": bool}: Response finished
    - {"type": "error", "message": "..."}: Error occurred

    JSON message types from client:
    - {"type": "update_context", "context": {...}}: Update borrower context
    - {"type": "end_session"}: End the session
    """
    await websocket.accept()

    # Default context
    context = {
        "borrower_name": "Customer",
        "outstanding_amount": 50000,
        "emi_amount": 5000,
        "dpd": 30,
        "loan_type": "Personal Loan",
        "organization_name": "CollectIQ Finance",
        "language": "hi"
    }

    # Create pipeline
    pipeline = VoicePipeline(
        session_id=session_id,
        context=context,
        stt_service=stt_service,
        tts_service=tts_service,
        dialog_manager=dialog_manager,
        sample_rate=16000,
        use_silero_vad=False  # Use energy VAD for lighter demo
    )
    voice_sessions[session_id] = pipeline

    try:
        # Send initial greeting
        print(f"Voice session {session_id} started, sending greeting...")
        async for audio_chunk in pipeline.generate_greeting():
            await websocket.send_bytes(audio_chunk)

        # Signal greeting complete
        await websocket.send_json({"type": "greeting_complete"})
        print(f"Greeting complete for session {session_id}")

        # Main conversation loop
        while True:
            try:
                data = await websocket.receive()

                if "bytes" in data:
                    # Audio data from client
                    audio_chunk = data["bytes"]

                    # Check if this will interrupt AI speech
                    was_speaking = pipeline.is_ai_speaking

                    # Process through pipeline (will auto-interrupt if needed)
                    result = await pipeline.process_audio_chunk(audio_chunk)

                    # Notify client if AI was interrupted
                    if was_speaking and not pipeline.is_ai_speaking:
                        await websocket.send_json({"type": "interrupted"})

                    if result and result.user_text:
                        # Send user transcript
                        await websocket.send_json({
                            "type": "transcript",
                            "role": "user",
                            "text": result.user_text
                        })

                        # Send processing indicator
                        await websocket.send_json({"type": "processing"})

                        if result.ai_response:
                            # Send AI transcript
                            await websocket.send_json({
                                "type": "transcript",
                                "role": "assistant",
                                "text": result.ai_response
                            })

                            # Stream TTS audio
                            async for tts_chunk in pipeline.generate_tts_stream(result.ai_response):
                                await websocket.send_bytes(tts_chunk)

                            # Signal response complete
                            await websocket.send_json({
                                "type": "response_complete",
                                "action": result.action,
                                "should_end": result.should_end
                            })

                            # End session if dialog manager says so
                            if result.should_end:
                                await websocket.send_json({
                                    "type": "session_ended",
                                    "reason": "conversation_complete"
                                })
                                break

                elif "text" in data:
                    # JSON message from client
                    try:
                        msg = json.loads(data["text"])
                        msg_type = msg.get("type")

                        if msg_type == "end_session":
                            print(f"Client ended session {session_id}")
                            break

                        elif msg_type == "interrupt":
                            # User wants to interrupt AI speech
                            if pipeline.interrupt():
                                await websocket.send_json({
                                    "type": "interrupted"
                                })

                        elif msg_type == "update_context":
                            new_context = msg.get("context", {})
                            pipeline.set_context(new_context)
                            await websocket.send_json({
                                "type": "context_updated"
                            })

                    except json.JSONDecodeError:
                        print(f"Invalid JSON from client: {data['text']}")

            except WebSocketDisconnect:
                print(f"Client disconnected from session {session_id}")
                break

    except Exception as e:
        print(f"Voice session {session_id} error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass

    finally:
        # Cleanup
        if session_id in voice_sessions:
            del voice_sessions[session_id]
        print(f"Voice session {session_id} ended")


@app.get("/voice/sessions")
async def list_voice_sessions():
    """List active voice sessions (for debugging)."""
    return {
        "active_sessions": list(voice_sessions.keys()),
        "count": len(voice_sessions)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
