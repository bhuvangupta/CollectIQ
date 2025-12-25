#!/bin/bash
# Start only the backend service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Check virtual environment exists
VENV_PATH="$PROJECT_ROOT/venv"
if [ ! -f "$VENV_PATH/bin/uvicorn" ]; then
    echo "Error: uvicorn not found in $VENV_PATH"
    exit 1
fi

echo "Starting Backend API on http://localhost:8000"
echo "API Docs available at http://localhost:8000/docs"
echo ""

cd "$PROJECT_ROOT/backend"
exec "$VENV_PATH/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload
