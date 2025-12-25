#!/bin/bash
# Setup database for AI Collection Platform

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^$' | xargs)
fi

# Default values
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-$(whoami)}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"
DB_NAME="${POSTGRES_DB:-loan_collection}"

echo "========================================"
echo "Database Setup"
echo "========================================"
echo ""
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo ""

# Check if PostgreSQL is running by trying to connect
echo -e "${YELLOW}Checking PostgreSQL connection...${NC}"
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c '\q' 2>/dev/null; then
    echo -e "${RED}Cannot connect to PostgreSQL. Make sure it's running.${NC}"
    echo "Try: brew services start postgresql@15 (macOS)"
    echo "  or: sudo systemctl start postgresql (Linux)"
    exit 1
fi
echo -e "${GREEN}PostgreSQL is running${NC}"

# Create database if not exists
echo -e "\n${YELLOW}Creating database...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME"
echo -e "${GREEN}Database '$DB_NAME' ready${NC}"

# Create extensions
echo -e "\n${YELLOW}Creating extensions...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
echo -e "${GREEN}Extensions created${NC}"

# Activate virtual environment
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo -e "${RED}Virtual environment not found. Run ./scripts/install.sh first${NC}"
    exit 1
fi

# Run migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
cd "$PROJECT_ROOT/backend"
alembic upgrade head
echo -e "${GREEN}Migrations complete${NC}"

echo -e "\n${GREEN}========================================"
echo "Database Setup Complete!"
echo "========================================${NC}"
echo ""
echo "Run './scripts/seed.sh' to add sample data"
echo ""
