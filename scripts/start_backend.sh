#!/bin/bash
# Start only the backend service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

echo "Starting Backend API on http://localhost:8000"
echo "API Docs available at http://localhost:8000/docs"
echo ""

cd "$PROJECT_ROOT/backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
