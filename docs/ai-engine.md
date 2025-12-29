# AI Engine

The AI Engine is an internal service that provides speech recognition, text-to-speech, dialog management, and real-time voice conversations. It runs on port 8001 and is used for browser-based voice testing and call analysis.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       AI Engine (port 8001)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │     STT     │  │     TTS     │  │   Dialog Manager    │  │
│  │  (Speech →  │  │  (Text →    │  │  (LLM + Prompts +   │  │
│  │    Text)    │  │   Speech)   │  │    Guardrails)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │               │                    │              │
│         └───────────────┴────────────────────┘              │
│                         │                                   │
│              ┌──────────┴──────────┐                        │
│              │   Voice Pipeline    │                        │
│              │  (Real-time voice   │                        │
│              │   via WebSocket)    │                        │
│              └─────────────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## AI Engine vs Voice AI Providers

| Aspect | AI Engine | Voice AI Providers |
|--------|-----------|-------------------|
| Purpose | Browser testing, call analysis | Real phone calls |
| Connection | WebSocket (browser) | Telephony (phone network) |
| Use case | Internal testing, transcript analysis | Production calls to borrowers |
| Providers | Whisper/Groq/Sarvam STT, Edge/Sarvam TTS | Bolna, LiveKit, Sarvam+Exotel |

**When to use AI Engine**: Testing voice conversations in browser, analyzing call transcripts, sentiment analysis.

**When to use Voice AI**: Making actual phone calls to borrowers in production.

## Components

### Speech-to-Text (STT)

Converts audio to text. Supports multiple providers:

| Provider | Config | Notes |
|----------|--------|-------|
| Whisper | `STT_PROVIDER=whisper` | Local, slower, no API key needed |
| Groq | `STT_PROVIDER=groq` | Fast cloud API, requires `GROQ_API_KEY` |
| Sarvam | `STT_PROVIDER=sarvam` | Best for Indian languages, requires `SARVAM_API_KEY` |

### Text-to-Speech (TTS)

Converts text to speech audio. Supports:

| Provider | Config | Notes |
|----------|--------|-------|
| Edge | `TTS_PROVIDER=edge` | Microsoft Edge TTS, free, good Hindi support |
| Sarvam | `TTS_PROVIDER=sarvam` | Natural Indian voices, requires API key |

### LLM (Language Model)

Powers dialog generation, sentiment analysis, and summarization:

| Provider | Config | Notes |
|----------|--------|-------|
| Ollama | `LLM_PROVIDER=ollama` | Local, free, requires Ollama setup |
| Groq | `LLM_PROVIDER=groq` | Fast cloud API, requires `GROQ_API_KEY` |
| Sarvam | `LLM_PROVIDER=sarvam` | Indian language optimized, requires API key |

### Dialog Manager

Handles conversation logic for collection calls:

- **Response Generation**: Context-aware responses using borrower data
- **Hinglish Support**: Natural Hindi-English code-mixing
- **Guardrails**: RBI compliance, no threats, respectful language
- **Entity Extraction**: Payment dates, amounts, promises

### Voice Pipeline

Real-time voice conversation via WebSocket:

- Voice Activity Detection (VAD)
- Utterance aggregation (waits for complete thought)
- Interruption handling
- Streaming TTS playback

## API Endpoints

### Health Check

```
GET /health
```

Returns status of all services (STT, TTS, Dialog).

### Speech-to-Text

```
POST /stt/transcribe
{
  "audio_url": "https://example.com/audio.wav",
  "language": "hi"
}

POST /stt/transcribe-file
# Form data with audio file
```

### Text-to-Speech

```
POST /tts/synthesize
{
  "text": "Namaste, aapka payment due hai",
  "voice": "default",
  "language": "hi"
}
# Returns: audio/wav binary
```

### Dialog

```
POST /dialog/respond
{
  "conversation_history": [
    {"role": "assistant", "content": "Namaste..."},
    {"role": "user", "content": "Haan boliye"}
  ],
  "context": {
    "borrower_name": "Rahul",
    "outstanding_amount": 25000,
    "dpd": 45
  },
  "language": "hi"
}
```

### Analysis

```
POST /analyze/sentiment
{
  "text": "Main next week payment kar dunga"
}

POST /analyze/summarize
{
  "transcript": "Full call transcript here...",
  "language": "en"
}

POST /analyze/compliance
{
  "transcript": "Full call transcript here..."
}
```

### WebSocket Voice

```
ws://localhost:8001/ws/voice/{session_id}
```

**Client → Server:**
- Binary: Audio chunks (16-bit PCM, 16kHz, mono)
- JSON: `{"type": "update_context", "context": {...}}`
- JSON: `{"type": "end_session"}`
- JSON: `{"type": "interrupt"}`

**Server → Client:**
- Binary: TTS audio (MP3)
- JSON: `{"type": "greeting_complete"}`
- JSON: `{"type": "transcript", "role": "user|assistant", "text": "..."}`
- JSON: `{"type": "response_complete", "action": "...", "should_end": bool}`
- JSON: `{"type": "error", "message": "..."}`

## Configuration

```bash
# STT Provider
STT_PROVIDER=groq              # whisper, groq, or sarvam
GROQ_STT_MODEL=whisper-large-v3-turbo

# TTS Provider
TTS_PROVIDER=edge              # edge or sarvam
TTS_RATE=+10%                  # Speech rate adjustment

# LLM Provider
LLM_PROVIDER=groq              # ollama, groq, or sarvam
GROQ_MODEL=llama-3.1-8b-instant
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:8b

# API Keys (as needed)
GROQ_API_KEY=gsk_...
SARVAM_API_KEY=...

# Voice Activity Detection
VAD_MIN_SILENCE_MS=500         # Silence before speech end
VAD_MIN_SPEECH_MS=200          # Min speech to process
```

## Project Structure

```
ai_engine/
├── main.py              # FastAPI app, endpoints, WebSocket
├── stt/                 # Speech-to-Text
│   ├── factory.py       # Provider selection
│   ├── whisper_provider.py
│   ├── groq_provider.py
│   └── sarvam_provider.py
├── tts/                 # Text-to-Speech
│   ├── factory.py
│   ├── edge_provider.py
│   └── sarvam_provider.py
├── llm/                 # Language Models
│   ├── factory.py
│   ├── ollama_provider.py
│   ├── groq_provider.py
│   └── sarvam_provider.py
├── dialog/              # Dialog Management
│   ├── manager.py       # Main dialog logic
│   ├── prompts.py       # English prompts
│   ├── hinglish_prompts.py  # Hindi/Hinglish prompts
│   └── guardrails.py    # Compliance checks
├── realtime/            # Real-time Voice
│   └── pipeline.py      # Voice conversation pipeline
└── voice/               # Voice utilities
    └── stt_service.py   # STT wrapper service
```

## Running the AI Engine

```bash
# Start AI Engine only
./scripts/start_ai.sh

# Or with all services
./scripts/start.sh

# View logs
./scripts/logs.sh ai
```

Access API docs at: http://localhost:8001/docs

## Testing Voice in Browser

1. Start all services: `./scripts/start.sh`
2. Login to frontend
3. Navigate to **Internal AI Demo** (`/voice-demo`)
4. Configure borrower context
5. Hold microphone button to speak
6. AI responds via speaker

See [Voice Demo Guide](voice-demo.md) for details.
