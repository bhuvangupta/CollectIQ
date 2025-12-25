#!/bin/bash
# Start only the telephony service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

echo "Starting Telephony Service on http://localhost:8002"
echo ""

cd "$PROJECT_ROOT/telephony"
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
