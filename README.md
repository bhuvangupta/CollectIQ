# CollectIQ - AI-Powered Loan Collection Platform

An intelligent loan collection platform for Indian financial institutions, featuring AI voice bots, multi-channel communication, and comprehensive analytics.

## Features

- **AI Voice Bot**: Automated collection calls using speech recognition (Whisper) and text-to-speech (Coqui XTTS)
- **Multi-Language Support**: Hindi and English support for voice and text
- **Intelligent Dialog**: Context-aware conversations using configurable LLM (Ollama or Groq)
- **Multi-Channel Communication**: Phone calls, SMS, and WhatsApp integration
- **Campaign Management**: Bulk outreach campaigns with targeting and scheduling
- **Case Management**: Assign, track, and manage collection cases
- **Analytics Dashboard**: Real-time metrics, collection trends, and agent performance
- **Compliance Built-in**: RBI guideline compliance checking in conversations
- **Multi-Tenant**: Row-level security for multiple organizations

## Tech Stack

### Backend
- Python 3.11+ with FastAPI
- PostgreSQL 15
- Redis for caching and Celery broker
- SQLAlchemy with async support
- Alembic for migrations

### Frontend
- React 18 with TypeScript
- Tailwind CSS for styling
- Zustand for state management
- React Query for data fetching
- Recharts for visualizations

### AI/ML
- OpenAI Whisper (large-v3) for speech-to-text
- Edge TTS (Microsoft) for text-to-speech (supports 9 Indian languages)
- Configurable LLM provider for dialog management:
  - **Ollama** (default): Local inference with Qwen3 8B
  - **Groq**: Cloud API with Qwen QwQ 32B
- Custom compliance checking

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis
- 16GB+ RAM recommended (for AI models)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd v1

# Run installation script
./scripts/install.sh
```

### Setup Database

```bash
# Setup PostgreSQL database and run migrations
./scripts/setup_db.sh

# Seed sample data (optional)
./scripts/seed.sh
```

### Setup Ollama (for AI features)

```bash
./scripts/ollama_setup.sh
```

### Start All Services

```bash
# Start all services (backend, frontend, AI engine, telephony, celery)
./scripts/start.sh
```

### Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- AI Engine: http://localhost:8001/docs
- Telephony: http://localhost:8002/docs

### Default Credentials

- Email: `admin@collectiq.com`
- Password: `password123`

## Scripts Reference

| Script | Description |
|--------|-------------|
| `./scripts/install.sh` | Install all dependencies |
| `./scripts/setup_db.sh` | Create database and run migrations |
| `./scripts/seed.sh` | Seed database with sample data |
| `./scripts/start.sh` | Start all services |
| `./scripts/stop.sh` | Stop all services |
| `./scripts/start_backend.sh` | Start only backend API |
| `./scripts/start_frontend.sh` | Start only frontend |
| `./scripts/start_ai.sh` | Start only AI engine |
| `./scripts/start_telephony.sh` | Start only telephony service |
| `./scripts/start_celery.sh` | Start Celery worker/beat |
| `./scripts/migrate.sh` | Database migration commands |
| `./scripts/test.sh` | Run tests |
| `./scripts/lint.sh` | Run linting |
| `./scripts/logs.sh` | View service logs |
| `./scripts/ollama_setup.sh` | Setup Ollama with Llama model |

## Project Structure

```
v1/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Config, security, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── tasks/          # Celery tasks
│   └── alembic/            # Database migrations
├── frontend/               # React frontend
│   └── src/
│       ├── components/     # UI components
│       ├── pages/          # Page components
│       ├── stores/         # Zustand stores
│       ├── services/       # API services
│       └── hooks/          # Custom hooks
├── ai_engine/              # AI/ML services
│   ├── voice/              # STT/TTS services
│   └── dialog/             # Dialog management
├── telephony/              # Telephony service
│   └── services/           # Call handling
├── scripts/                # Bash scripts
├── logs/                   # Service logs
└── README.md
```

## Development

### Running Individual Services

```bash
# Backend only
./scripts/start_backend.sh

# Frontend only
./scripts/start_frontend.sh

# AI Engine only
./scripts/start_ai.sh

# Telephony only
./scripts/start_telephony.sh

# Celery worker
./scripts/start_celery.sh worker

# Celery beat (scheduler)
./scripts/start_celery.sh beat
```

### Database Migrations

```bash
# Run pending migrations
./scripts/migrate.sh upgrade

# Rollback one migration
./scripts/migrate.sh downgrade

# Create new migration
./scripts/migrate.sh create "add_new_table"

# View migration history
./scripts/migrate.sh history
```

### Running Tests

```bash
# Backend tests
./scripts/test.sh backend

# Frontend tests
./scripts/test.sh frontend

# Backend with coverage
./scripts/test.sh cov

# All tests
./scripts/test.sh all
```

### Code Quality

```bash
# Check linting
./scripts/lint.sh check

# Fix linting issues
./scripts/lint.sh fix

# Format code
./scripts/lint.sh format
```

### Viewing Logs

```bash
# All logs
./scripts/logs.sh all

# Specific service
./scripts/logs.sh backend
./scripts/logs.sh frontend
./scripts/logs.sh ai
./scripts/logs.sh telephony
./scripts/logs.sh celery
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/login` | User authentication |
| `GET /api/v1/cases` | List collection cases |
| `POST /api/v1/communications/call` | Initiate a call |
| `GET /api/v1/analytics/dashboard` | Dashboard metrics |
| `POST /api/v1/campaigns` | Create campaign |

## Configuration

Key environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT secret key | (generated) |
| `LLM_PROVIDER` | LLM provider to use | `ollama` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model to use | `qwen3:8b` |
| `GROQ_API_KEY` | Groq API key (required if using Groq) | - |
| `GROQ_MODEL` | Groq model to use | `qwen-qwq-32b` |

## Compliance

This platform includes built-in compliance features for RBI collection guidelines:

- **Timing Restrictions**: Calls only between 8 AM - 7 PM
- **Language Monitoring**: Detection of threatening/abusive language
- **Privacy Protection**: Prevention of third-party disclosure
- **Call Recording**: All calls recorded for audit

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
