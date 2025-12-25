#!/bin/bash
# Start only the AI engine

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# AI engine has its own venv
if [ -f "$PROJECT_ROOT/ai_engine/venv/bin/uvicorn" ]; then
    VENV_PATH="$PROJECT_ROOT/ai_engine/venv"
elif [ -f "$PROJECT_ROOT/venv/bin/uvicorn" ]; then
    VENV_PATH="$PROJECT_ROOT/venv"
else
    echo "Error: uvicorn not found"
    exit 1
fi

echo "Starting AI Engine on http://localhost:8001"
echo ""

cd "$PROJECT_ROOT/ai_engine"
exec "$VENV_PATH/bin/uvicorn" main:app --host 0.0.0.0 --port 8001 --reload
