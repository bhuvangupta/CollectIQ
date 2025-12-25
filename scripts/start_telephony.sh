#!/bin/bash
# Start only the telephony service

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

echo "Starting Telephony Service on http://localhost:8002"
echo ""

cd "$PROJECT_ROOT/telephony"
exec uvicorn main:app --host 0.0.0.0 --port 8002 --reload
