#!/bin/bash
# Seed database with sample data

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "Seeding Database"
echo "========================================"

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^$' | xargs)
fi

# Run seed script
cd "$PROJECT_ROOT/backend"
python scripts/seed_data.py

echo ""
echo "Default login credentials:"
echo "  Email:    admin@collectiq.com"
echo "  Password: password123"
echo ""
