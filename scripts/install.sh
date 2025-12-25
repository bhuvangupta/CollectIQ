#!/bin/bash
# Install all dependencies for the AI Collection Platform

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "AI Collection Platform - Installation"
echo "========================================"

# Check Python version
echo -e "\n${YELLOW}Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}Python $PYTHON_VERSION found${NC}"
else
    echo -e "${RED}Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

# Check Node.js
echo -e "\n${YELLOW}Checking Node.js...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}Node.js $NODE_VERSION found${NC}"
else
    echo -e "${RED}Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi

# Check PostgreSQL
echo -e "\n${YELLOW}Checking PostgreSQL...${NC}"
if command -v psql &> /dev/null; then
    PSQL_VERSION=$(psql --version | cut -d' ' -f3)
    echo -e "${GREEN}PostgreSQL $PSQL_VERSION found${NC}"
else
    echo -e "${YELLOW}PostgreSQL not found. Install it or use a remote database.${NC}"
fi

# Check Redis
echo -e "\n${YELLOW}Checking Redis...${NC}"
if command -v redis-server &> /dev/null; then
    REDIS_VERSION=$(redis-server --version | cut -d' ' -f3 | cut -d'=' -f2)
    echo -e "${GREEN}Redis $REDIS_VERSION found${NC}"
else
    echo -e "${YELLOW}Redis not found. Install it or use a remote Redis.${NC}"
fi

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create Python virtual environment
echo -e "\n${YELLOW}Creating Python virtual environment...${NC}"
cd "$PROJECT_ROOT"
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
echo -e "\n${YELLOW}Installing backend dependencies...${NC}"
cd "$PROJECT_ROOT/backend"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}Backend dependencies installed${NC}"

# Install AI engine dependencies
echo -e "\n${YELLOW}Installing AI engine dependencies...${NC}"
cd "$PROJECT_ROOT/ai_engine"
pip install -r requirements.txt
echo -e "${GREEN}AI engine dependencies installed${NC}"

# Install telephony dependencies
echo -e "\n${YELLOW}Installing telephony dependencies...${NC}"
cd "$PROJECT_ROOT/telephony"
pip install -r requirements.txt
echo -e "${GREEN}Telephony dependencies installed${NC}"

# Install frontend dependencies
echo -e "\n${YELLOW}Installing frontend dependencies...${NC}"
cd "$PROJECT_ROOT/frontend"
npm install
echo -e "${GREEN}Frontend dependencies installed${NC}"

# Create .env if not exists
cd "$PROJECT_ROOT"
if [ ! -f .env ]; then
    echo -e "\n${YELLOW}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${GREEN}.env file created. Please update with your settings.${NC}"
fi

# Create data directories
echo -e "\n${YELLOW}Creating data directories...${NC}"
mkdir -p "$PROJECT_ROOT/data/uploads"
mkdir -p "$PROJECT_ROOT/data/recordings"
mkdir -p "$PROJECT_ROOT/data/exports"
mkdir -p "$PROJECT_ROOT/logs"

echo -e "\n${GREEN}========================================"
echo "Installation Complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Update .env with your database credentials"
echo "  2. Run: ./scripts/setup_db.sh"
echo "  3. Run: ./scripts/start.sh"
echo ""
