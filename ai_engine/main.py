from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os

from voice.stt_service import STTService
from voice.tts_service import TTSService
from dialog.manager import DialogManager


# Initialize services
stt_service: Optional[STTService] = None
tts_service: Optional[TTSService] = None
dialog_manager: Optional[DialogManager] = None


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
