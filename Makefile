.PHONY: help build up down logs shell migrate seed test lint format clean

# Default target
help:
	@echo "AI-Powered Loan Collection Platform"
	@echo ""
	@echo "Usage:"
	@echo "  make build        Build all Docker images"
	@echo "  make up           Start all services"
	@echo "  make down         Stop all services"
	@echo "  make logs         View logs from all services"
	@echo "  make shell        Open shell in backend container"
	@echo "  make migrate      Run database migrations"
	@echo "  make seed         Seed database with sample data"
	@echo "  make test         Run all tests"
	@echo "  make lint         Run linting"
	@echo "  make format       Format code"
	@echo "  make clean        Clean up containers and volumes"
	@echo ""
	@echo "Development:"
	@echo "  make dev          Start in development mode"
	@echo "  make dev-backend  Start only backend services"
	@echo "  make dev-frontend Start only frontend"
	@echo ""
	@echo "Production:"
	@echo "  make prod         Start in production mode"
	@echo ""

# Build all images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000/docs"
	@echo "AI Engine: http://localhost:8001/docs"
	@echo "Telephony: http://localhost:8002/docs"

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-ai:
	docker-compose logs -f ai-engine

logs-telephony:
	docker-compose logs -f telephony

# Shell access
shell:
	docker-compose exec backend bash

shell-db:
	docker-compose exec postgres psql -U postgres -d loan_collection

shell-redis:
	docker-compose exec redis redis-cli

# Database
migrate:
	docker-compose exec backend alembic upgrade head

migrate-create:
	@read -p "Migration name: " name; \
	docker-compose exec backend alembic revision --autogenerate -m "$$name"

migrate-down:
	docker-compose exec backend alembic downgrade -1

seed:
	docker-compose exec backend python -m scripts.seed_data

# Testing
test:
	docker-compose exec backend pytest -v

test-cov:
	docker-compose exec backend pytest --cov=app --cov-report=html

test-frontend:
	docker-compose exec frontend npm test

# Linting and formatting
lint:
	docker-compose exec backend ruff check app/
	docker-compose exec frontend npm run lint

lint-fix:
	docker-compose exec backend ruff check --fix app/
	docker-compose exec frontend npm run lint:fix

format:
	docker-compose exec backend black app/
	docker-compose exec frontend npm run format

# Development mode
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

dev-backend:
	docker-compose up -d postgres redis minio ollama
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-ai:
	cd ai_engine && uvicorn main:app --reload --host 0.0.0.0 --port 8001

dev-telephony:
	cd telephony && uvicorn main:app --reload --host 0.0.0.0 --port 8002

# Production mode
prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Ollama model management
ollama-pull:
	docker-compose exec ollama ollama pull llama3.1:8b

ollama-list:
	docker-compose exec ollama ollama list

# MinIO setup
minio-setup:
	docker-compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin123
	docker-compose exec minio mc mb local/recordings --ignore-existing
	docker-compose exec minio mc mb local/exports --ignore-existing
	docker-compose exec minio mc mb local/imports --ignore-existing

# Cleanup
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

clean-all:
	docker-compose down -v --remove-orphans
	docker system prune -af
	docker volume prune -f

# Health check
health:
	@echo "Checking services..."
	@curl -s http://localhost:8000/health | jq . || echo "Backend: DOWN"
	@curl -s http://localhost:8001/health | jq . || echo "AI Engine: DOWN"
	@curl -s http://localhost:8002/health | jq . || echo "Telephony: DOWN"
	@curl -s http://localhost:3000 > /dev/null && echo "Frontend: UP" || echo "Frontend: DOWN"

# Backup
backup-db:
	docker-compose exec postgres pg_dump -U postgres loan_collection > backup_$$(date +%Y%m%d_%H%M%S).sql

restore-db:
	@read -p "Backup file: " file; \
	cat $$file | docker-compose exec -T postgres psql -U postgres -d loan_collection

# Generate API client
generate-client:
	docker-compose exec backend python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > openapi.json
	npx openapi-typescript-codegen --input openapi.json --output frontend/src/api/generated --client axios
