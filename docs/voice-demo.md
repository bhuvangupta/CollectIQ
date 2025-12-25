# Real-Time Voice Demo

The platform includes a browser-based voice demo for testing AI conversations without making real phone calls.

## Accessing the Demo

1. Start all services: `./scripts/start.sh`
2. Login as admin or manager
3. Navigate to **Internal AI Demo** in the sidebar (or go to `/voice-demo`)

## How It Works

```
┌─────────────────────────────────────────┐
│         AI Voice Demo                   │
├─────────────────────────────────────────┤
│  Browser Mic → WebSocket → AI Engine    │
│                                         │
│  1. Hold microphone button to speak     │
│  2. Release to send audio to AI         │
│  3. AI responds in Hinglish via speaker │
├─────────────────────────────────────────┤
│  Voice Pipeline:                        │
│  ├─ VAD detects speech end              │
│  ├─ Whisper/Groq transcribes speech     │
│  ├─ LLM generates contextual response   │
│  └─ Edge TTS speaks response            │
└─────────────────────────────────────────┘
```

## Configuration

Configure the borrower context in the demo:
- Borrower name, outstanding amount, EMI
- Days past due (DPD), loan type
- Language preference

## WebSocket Endpoint

```
ws://localhost:8001/ws/voice/{session_id}
```

### Protocol

- **Client sends**: Binary audio (16-bit PCM, 16kHz, mono)
- **Server sends**: Binary audio (MP3) or JSON messages

### JSON Message Types

| Type | Description |
|------|-------------|
| `greeting_complete` | AI greeting finished |
| `transcript` | User speech transcribed |
| `processing` | AI is generating response |
| `response_complete` | AI response finished |
| `error` | Error occurred |

## Voice Pipeline Components

### Speech-to-Text (STT)

| Provider | Configuration | Speed |
|----------|--------------|-------|
| Whisper (local) | `STT_PROVIDER=whisper` | Slower, offline |
| Groq (cloud) | `STT_PROVIDER=groq` | Fast, requires API key |

### Text-to-Speech (TTS)

Uses Edge TTS (Microsoft) with support for 9 Indian languages:
- Hindi, English, Tamil, Telugu
- Bengali, Marathi, Gujarati
- Kannada, Malayalam

### LLM (Dialog)

| Provider | Configuration | Notes |
|----------|--------------|-------|
| Ollama (local) | `LLM_PROVIDER=ollama` | Free, requires setup |
| Groq (cloud) | `LLM_PROVIDER=groq` | Fast, requires API key |

## Environment Variables

```bash
# Voice Activity Detection
VAD_MIN_SILENCE_MS=500      # Silence before speech end
VAD_MIN_SPEECH_MS=200       # Min speech to process

# TTS
TTS_RATE=+10%               # Speech rate adjustment

# STT Provider
STT_PROVIDER=groq           # whisper or groq
GROQ_STT_MODEL=whisper-large-v3-turbo

# LLM Provider
LLM_PROVIDER=groq           # ollama or groq
GROQ_MODEL=llama-3.1-8b-instant
```
