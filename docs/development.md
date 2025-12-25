# Development Guide

## Running Individual Services

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
./scripts/logs.sh backend
./scripts/logs.sh frontend
./scripts/logs.sh ai
./scripts/logs.sh telephony
./scripts/logs.sh celery
```

## Project Structure

```
collectiq/
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
│   ├── dialog/             # Dialog management
│   └── realtime/           # Real-time voice pipeline
├── telephony/              # Telephony service
│   └── services/           # Call handling
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
