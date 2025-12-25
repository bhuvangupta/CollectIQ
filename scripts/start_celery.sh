#!/bin/bash
# Start Celery worker and beat

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Activate virtual environment
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo "Error: Virtual environment not found at $PROJECT_ROOT/venv"
    exit 1
fi

cd "$PROJECT_ROOT/backend"

# Check if we should run worker or beat
case "${1:-all}" in
    worker)
        echo "Starting Celery Worker..."
        exec celery -A app.tasks.celery_app worker --loglevel=info
        ;;
    beat)
        echo "Starting Celery Beat..."
        exec celery -A app.tasks.celery_app beat --loglevel=info
        ;;
    all)
        echo "Starting Celery Worker and Beat..."
        celery -A app.tasks.celery_app worker --loglevel=info &
        exec celery -A app.tasks.celery_app beat --loglevel=info
        ;;
    *)
        echo "Usage: $0 {worker|beat|all}"
        exit 1
        ;;
esac
