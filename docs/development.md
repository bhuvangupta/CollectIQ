# Development Guide

## Architecture

CollectIQ runs as 2 main services:

| Service | Port | Description |
|---------|------|-------------|
| Backend + Telephony | 8000 | FastAPI backend with integrated telephony |
| AI Engine | 8001 | STT/TTS/LLM services |

Supporting services: PostgreSQL, Redis, Celery (worker + beat).

## Running Individual Services

```bash
# Backend only (includes telephony)
./scripts/start_backend.sh

# Frontend only
./scripts/start_frontend.sh

# AI Engine only
./scripts/start_ai.sh

# Celery worker
./scripts/start_celery.sh worker

# Celery beat (scheduler)
./scripts/start_celery.sh beat
```

## Database Migrations

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

## Running Tests

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

## Code Quality

```bash
# Check linting
./scripts/lint.sh check

# Fix linting issues
./scripts/lint.sh fix

# Format code
./scripts/lint.sh format
```

## Viewing Logs

```bash
# All logs
./scripts/logs.sh all

# Specific service
./scripts/logs.sh backend    # Includes telephony logs
./scripts/logs.sh frontend
./scripts/logs.sh ai
./scripts/logs.sh celery
```

## Project Structure

```
collectiq/
├── backend/                 # FastAPI backend (includes telephony)
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   │           ├── telephony.py   # Call/SMS endpoints
│   │   │           └── ...
│   │   ├── core/           # Config, security, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   │   └── telephony/  # Telephony providers (Exotel, Mock)
│   │   └── tasks/          # Celery tasks
│   └── alembic/            # Database migrations
├── frontend/               # React frontend
│   └── src/
│       ├── components/     # UI components
│       ├── pages/          # Page components
│       ├── stores/         # Zustand stores
│       ├── services/       # API services
│       └── hooks/          # Custom hooks
├── ai_engine/              # AI/ML services (separate process)
│   ├── voice/              # STT/TTS services
│   ├── dialog/             # Dialog management
│   └── realtime/           # Real-time voice pipeline
├── scripts/                # Bash scripts
├── docs/                   # Documentation
├── logs/                   # Service logs
└── README.md
```

## Scripts Reference

| Script | Description |
|--------|-------------|
| `./scripts/install.sh` | Install all dependencies |
| `./scripts/setup_db.sh` | Create database and run migrations |
| `./scripts/seed.sh` | Seed database with sample data |
| `./scripts/start.sh` | Start all services (2 processes) |
| `./scripts/stop.sh` | Stop all services |
| `./scripts/start_backend.sh` | Start backend API (includes telephony) |
| `./scripts/start_frontend.sh` | Start only frontend |
| `./scripts/start_ai.sh` | Start only AI engine |
| `./scripts/start_celery.sh` | Start Celery worker/beat |
| `./scripts/migrate.sh` | Database migration commands |
| `./scripts/test.sh` | Run tests |
| `./scripts/lint.sh` | Run linting |
| `./scripts/logs.sh` | View service logs |
| `./scripts/ollama_setup.sh` | Setup Ollama with Llama model |

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

### Telephony Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/telephony/calls/initiate` | Initiate outbound call |
| `GET /api/v1/telephony/calls/active` | List active calls |
| `GET /api/v1/telephony/calls/{call_id}` | Get call details |
| `POST /api/v1/telephony/calls/{call_id}/end` | End active call |
| `POST /api/v1/telephony/sms/send` | Send SMS message |
| `POST /api/v1/telephony/whatsapp/send` | Send WhatsApp message |
| `GET /api/v1/telephony/provider/stats` | Provider statistics |
| `GET /api/v1/telephony/provider/balance` | Account balance |
| `POST /api/v1/telephony/webhook/exotel/status` | Exotel webhook |

## Telephony Configuration

The telephony service is integrated into the backend. Configure via environment variables:

```bash
# Provider selection
TELEPHONY_PROVIDER=mock     # mock (development) or exotel (production)

# Exotel credentials (for production)
EXOTEL_API_KEY=your-api-key
EXOTEL_API_TOKEN=your-api-token
EXOTEL_SID=your-account-sid
EXOTEL_CALLER_ID=+91XXXXXXXXXX
EXOTEL_WEBHOOK_URL=https://your-domain.com/api/v1/telephony/webhook/exotel/status

# AI Engine connection
AI_ENGINE_URL=http://localhost:8001
```
