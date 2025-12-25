# CollectIQ - AI-Powered Loan Collection Platform

An intelligent loan collection platform for Indian financial institutions, featuring AI voice bots, multi-channel communication, and comprehensive analytics.

## Features

- **AI Voice Calling** - Automated collection calls via [Bolna AI](docs/voice-ai-providers.md#bolna-ai-setup) or [ElevenLabs](docs/voice-ai-providers.md#elevenlabs-setup)
- **Real-Time Voice Demo** - Browser-based [voice testing](docs/voice-demo.md) with AI agent
- **Multi-Language Support** - Hindi, English, and Hinglish
- **Multi-Channel Communication** - Phone calls, SMS, WhatsApp
- **Campaign Management** - Bulk outreach with targeting and scheduling
- **Case Management** - Assign, track, and manage collection cases
- **Analytics Dashboard** - Real-time metrics and agent performance
- **Compliance Built-in** - RBI guideline compliance checking

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, FastAPI, PostgreSQL, Redis, Celery |
| Frontend | React 18, TypeScript, Tailwind CSS, Zustand |
| AI/ML | Whisper/Groq/Sarvam STT, Edge/Sarvam TTS, Ollama/Groq/Sarvam LLM |
| Voice AI | Bolna AI, ElevenLabs |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis

### Installation

```bash
# Clone and install
git clone <repository-url>
cd collectiq
./scripts/install.sh

# Setup database
./scripts/setup_db.sh
./scripts/seed.sh  # Optional: sample data

# Setup AI (optional, for local LLM)
./scripts/ollama_setup.sh

# Start all services
./scripts/start.sh
```

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/docs |
| AI Engine | http://localhost:8001/docs |

### Default Login

- Email: `admin@collectiq.com`
- Password: `password123`

## Documentation

| Document | Description |
|----------|-------------|
| [Voice AI Providers](docs/voice-ai-providers.md) | Setup Bolna AI or ElevenLabs for automated calls |
| [Sarvam AI](docs/sarvam-ai.md) | Indian language AI (STT, TTS, LLM) |
| [Voice Demo](docs/voice-demo.md) | Browser-based voice testing guide |
| [Development](docs/development.md) | Running services, testing, project structure |
| [Configuration](docs/configuration.md) | Environment variables reference |

## Quick Configuration

```bash
# .env - Minimal setup for AI calling

# Database
POSTGRES_HOST=localhost
POSTGRES_DB=loan_collection

# AI (use Groq for fast cloud inference)
LLM_PROVIDER=groq
STT_PROVIDER=groq
GROQ_API_KEY=gsk_your_api_key

# Voice AI (choose one)
VOICE_AI_PROVIDER=bolna
BOLNA_API_KEY=bn-your-api-key
BOLNA_AGENT_ID=your-agent-id
```

See [Configuration Guide](docs/configuration.md) for all options.

## Scripts

| Script | Description |
|--------|-------------|
| `./scripts/start.sh` | Start all services |
| `./scripts/stop.sh` | Stop all services |
| `./scripts/migrate.sh upgrade` | Run database migrations |
| `./scripts/seed.sh` | Seed sample data |
| `./scripts/logs.sh all` | View all logs |

See [Development Guide](docs/development.md) for more scripts.

## Compliance

Built-in RBI collection guideline compliance:
- Timing restrictions (8 AM - 7 PM)
- Language monitoring
- Privacy protection
- Call recording for audit

## License

Apache License 2.0 - see [LICENSE](LICENSE)
