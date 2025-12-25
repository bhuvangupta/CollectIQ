#!/bin/bash
# Start only the AI engine

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

echo "Starting AI Engine on http://localhost:8001"
echo ""

cd "$PROJECT_ROOT/ai_engine"
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
