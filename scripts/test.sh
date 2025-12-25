#!/bin/bash
# Run tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

case "${1:-backend}" in
    backend)
        echo "Running backend tests..."
        cd "$PROJECT_ROOT/backend"
        pytest -v "${@:2}"
        ;;
    frontend)
        echo "Running frontend tests..."
        cd "$PROJECT_ROOT/frontend"
        npm test "${@:2}"
        ;;
    cov)
        echo "Running backend tests with coverage..."
        cd "$PROJECT_ROOT/backend"
        pytest --cov=app --cov-report=html --cov-report=term-missing "${@:2}"
        echo "Coverage report: $PROJECT_ROOT/backend/htmlcov/index.html"
        ;;
    all)
        echo "Running all tests..."
        cd "$PROJECT_ROOT/backend"
        pytest -v
        cd "$PROJECT_ROOT/frontend"
        npm test
        ;;
    *)
        echo "Usage: $0 {backend|frontend|cov|all}"
        exit 1
        ;;
esac
