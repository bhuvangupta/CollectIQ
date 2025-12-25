#!/bin/bash
# Database migration commands

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

case "${1:-upgrade}" in
    upgrade)
        echo "Running migrations..."
        alembic upgrade head
        echo "Migrations complete"
        ;;
    downgrade)
        echo "Rolling back one migration..."
        alembic downgrade -1
        echo "Rollback complete"
        ;;
    create)
        if [ -z "$2" ]; then
            echo "Usage: $0 create <migration_name>"
            exit 1
        fi
        echo "Creating migration: $2"
        alembic revision --autogenerate -m "$2"
        echo "Migration created"
        ;;
    history)
        alembic history
        ;;
    current)
        alembic current
        ;;
    *)
        echo "Usage: $0 {upgrade|downgrade|create <name>|history|current}"
        exit 1
        ;;
esac
