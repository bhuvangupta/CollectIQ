#!/bin/bash
# Start only the frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting Frontend on http://localhost:3000"
echo ""

cd "$PROJECT_ROOT/frontend"
npm run dev
