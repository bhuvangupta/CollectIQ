#!/bin/bash
# Start Celery worker and beat

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

cd "$PROJECT_ROOT/backend"

# Check if we should run worker or beat
case "${1:-all}" in
    worker)
        echo "Starting Celery Worker..."
        celery -A app.tasks.celery_app worker --loglevel=info
        ;;
    beat)
        echo "Starting Celery Beat..."
        celery -A app.tasks.celery_app beat --loglevel=info
        ;;
    all)
        echo "Starting Celery Worker and Beat..."
        celery -A app.tasks.celery_app worker --loglevel=info &
        celery -A app.tasks.celery_app beat --loglevel=info
        ;;
    *)
        echo "Usage: $0 {worker|beat|all}"
        exit 1
        ;;
esac
