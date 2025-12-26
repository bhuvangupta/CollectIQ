# Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and modify as needed.

## Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | `LoanCollectionPlatform` |
| `DEBUG` | Debug mode | `true` |
| `SECRET_KEY` | Application secret key | (required) |
| `API_V1_PREFIX` | API route prefix | `/api/v1` |

## Database

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | (empty) |
| `POSTGRES_DB` | Database name | `loan_collection` |

## Redis

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_PASSWORD` | Redis password | (empty) |

## JWT Authentication

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | JWT signing key | (required) |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | `7` |

## AI Engine

### LLM Provider

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider (`ollama`, `groq`, or `sarvam`) | `ollama` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model | `qwen3:8b` |
| `GROQ_API_KEY` | Groq API key | (required for groq) |
| `GROQ_MODEL` | Groq LLM model | `llama-3.1-8b-instant` |

### Sarvam AI (Indian Languages)

| Variable | Description | Default |
|----------|-------------|---------|
| `SARVAM_API_KEY` | Sarvam API key | (required for sarvam) |
| `SARVAM_LLM_MODEL` | Sarvam LLM model | `sarvam-m` |
| `SARVAM_STT_MODEL` | Sarvam STT model | `saarika:v2` |
| `SARVAM_TTS_MODEL` | Sarvam TTS model | `bulbul:v2` |
| `SARVAM_TTS_VOICE` | Default TTS voice | `Anushka` |

See [Sarvam AI Guide](sarvam-ai.md) for detailed setup.

### Speech-to-Text

| Variable | Description | Default |
|----------|-------------|---------|
| `STT_PROVIDER` | STT provider (`whisper`, `groq`, or `sarvam`) | `whisper` |
| `WHISPER_MODEL` | Local Whisper model | `large-v3` |
| `GROQ_STT_MODEL` | Groq STT model | `whisper-large-v3-turbo` |

### Text-to-Speech

| Variable | Description | Default |
|----------|-------------|---------|
| `TTS_PROVIDER` | TTS provider (`edge` or `sarvam`) | `edge` |

- **edge**: Microsoft Edge TTS - free, good quality, supports Hindi
- **sarvam**: Sarvam AI TTS - better Indian voices, requires API key

### Voice Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `VAD_MIN_SILENCE_MS` | Min silence before speech end | `500` |
| `VAD_MIN_SPEECH_MS` | Min speech duration | `200` |
| `TTS_RATE` | TTS speech rate | `+10%` |

## Voice AI Providers

| Variable | Description | Default |
|----------|-------------|---------|
| `VOICE_AI_PROVIDER` | Voice AI provider | `mock` |

Supported providers: `mock`, `bolna`, `sarvam`, `livekit`

See [Voice AI Providers Guide](voice-ai-providers.md) for detailed setup.

### Mock (Development)

No configuration required. Simulates AI calls for testing.

### Bolna AI

| Variable | Description | Default |
|----------|-------------|---------|
| `VOICE_AI_PROVIDER` | Set to `bolna` | - |
| `BOLNA_API_KEY` | Bolna API key | (required) |
| `BOLNA_AGENT_ID` | Bolna agent ID | (required) |
| `VOICE_AI_WEBHOOK_URL` | Webhook URL for callbacks | (optional) |

### Sarvam AI

| Variable | Description | Default |
|----------|-------------|---------|
| `VOICE_AI_PROVIDER` | Set to `sarvam` | - |
| `SARVAM_API_KEY` | Sarvam API key | (required) |
| `GROQ_API_KEY` | Groq API key for LLM | (required) |

Requires Exotel for telephony (see below).

### LiveKit

| Variable | Description | Default |
|----------|-------------|---------|
| `VOICE_AI_PROVIDER` | Set to `livekit` | - |
| `LIVEKIT_URL` | LiveKit server URL | (required) |
| `LIVEKIT_API_KEY` | LiveKit API key | (required) |
| `LIVEKIT_API_SECRET` | LiveKit API secret | (required) |
| `SARVAM_API_KEY` | Sarvam API key for STT/TTS | (required) |
| `GROQ_API_KEY` | Groq API key for LLM | (required) |

## Telephony

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEPHONY_PROVIDER` | Telephony provider (`mock` or `exotel`) | `mock` |

- **mock**: For development/testing without real phone calls
- **exotel**: For production phone calls via Exotel API

### Exotel Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `EXOTEL_API_KEY` | Exotel API key | (required) |
| `EXOTEL_API_TOKEN` | Exotel API token | (required) |
| `EXOTEL_SID` | Exotel account SID | (required) |
| `EXOTEL_SUBDOMAIN` | Exotel subdomain | `api` |
| `EXOTEL_CALLER_ID` | Outbound caller ID | (required) |
| `EXOTEL_WEBHOOK_URL` | Webhook base URL for callbacks | (required) |

See [Exotel Integration](exotel.md) for detailed setup.

## Service Ports

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_ENGINE_HOST` | AI engine host | `localhost` |
| `AI_ENGINE_PORT` | AI engine port | `8001` |

> **Note**: Telephony is integrated into the backend (port 8000). No separate service needed.

## Example .env File

```bash
# Core
APP_NAME=CollectIQ
DEBUG=true
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
POSTGRES_DB=loan_collection

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# AI Providers
LLM_PROVIDER=groq           # ollama, groq, or sarvam
STT_PROVIDER=groq           # whisper, groq, or sarvam
TTS_PROVIDER=edge           # edge or sarvam
GROQ_API_KEY=gsk_your_api_key
GROQ_MODEL=llama-3.1-8b-instant
GROQ_STT_MODEL=whisper-large-v3-turbo

# Voice AI - for AI phone calls
VOICE_AI_PROVIDER=mock      # mock, bolna, sarvam, or livekit
# BOLNA_API_KEY=bn-your-api-key
# BOLNA_AGENT_ID=your-agent-id

# Telephony - Direct phone calls
TELEPHONY_PROVIDER=mock     # mock or exotel
# EXOTEL_API_KEY=your-key
# EXOTEL_SID=your-sid
# EXOTEL_CALLER_ID=+91XXXXXXXXXX
```
