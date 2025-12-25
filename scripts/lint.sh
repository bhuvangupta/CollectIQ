#!/bin/bash
# Run linting and formatting

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

case "${1:-check}" in
    check)
        echo "Running linting checks..."
        echo ""
        echo "Backend (ruff):"
        cd "$PROJECT_ROOT/backend"
        ruff check app/ || true
        echo ""
        echo "Frontend (eslint):"
        cd "$PROJECT_ROOT/frontend"
        npm run lint || true
        ;;
    fix)
        echo "Fixing linting issues..."
        echo ""
        echo "Backend (ruff):"
        cd "$PROJECT_ROOT/backend"
        ruff check --fix app/
        echo ""
        echo "Frontend (eslint):"
        cd "$PROJECT_ROOT/frontend"
        npm run lint:fix || true
        ;;
    format)
        echo "Formatting code..."
        echo ""
        echo "Backend (black):"
        cd "$PROJECT_ROOT/backend"
        black app/
        echo ""
        echo "Frontend (prettier):"
        cd "$PROJECT_ROOT/frontend"
        npm run format || true
        ;;
    *)
        echo "Usage: $0 {check|fix|format}"
        exit 1
        ;;
esac
