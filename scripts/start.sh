#!/bin/bash
# Start all services for AI Collection Platform

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# PID file for tracking processes
PID_FILE="$PROJECT_ROOT/.pids"
> "$PID_FILE"

cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    if [ -f "$PID_FILE" ]; then
        while read pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "========================================"
echo "Starting AI Collection Platform"
echo "========================================"

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

# Check Redis
echo -e "\n${YELLOW}Checking Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}Redis is running${NC}"
else
    echo -e "${YELLOW}Starting Redis...${NC}"
    redis-server --daemonize yes
    sleep 1
    echo -e "${GREEN}Redis started${NC}"
fi

# Start Backend
echo -e "\n${YELLOW}Starting Backend API...${NC}"
cd "$PROJECT_ROOT/backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
echo $! >> "$PID_FILE"
echo -e "${GREEN}Backend started on http://localhost:8000${NC}"

# Start AI Engine
echo -e "\n${YELLOW}Starting AI Engine...${NC}"
cd "$PROJECT_ROOT/ai_engine"
uvicorn main:app --host 0.0.0.0 --port 8001 --reload > "$PROJECT_ROOT/logs/ai_engine.log" 2>&1 &
echo $! >> "$PID_FILE"
echo -e "${GREEN}AI Engine started on http://localhost:8001${NC}"

# Start Telephony Service
echo -e "\n${YELLOW}Starting Telephony Service...${NC}"
cd "$PROJECT_ROOT/telephony"
uvicorn main:app --host 0.0.0.0 --port 8002 --reload > "$PROJECT_ROOT/logs/telephony.log" 2>&1 &
echo $! >> "$PID_FILE"
echo -e "${GREEN}Telephony started on http://localhost:8002${NC}"

# Start Celery Worker
echo -e "\n${YELLOW}Starting Celery Worker...${NC}"
cd "$PROJECT_ROOT/backend"
celery -A app.tasks.celery_app worker --loglevel=info > "$PROJECT_ROOT/logs/celery_worker.log" 2>&1 &
echo $! >> "$PID_FILE"
echo -e "${GREEN}Celery Worker started${NC}"

# Start Celery Beat
echo -e "\n${YELLOW}Starting Celery Beat...${NC}"
cd "$PROJECT_ROOT/backend"
celery -A app.tasks.celery_app beat --loglevel=info > "$PROJECT_ROOT/logs/celery_beat.log" 2>&1 &
echo $! >> "$PID_FILE"
echo -e "${GREEN}Celery Beat started${NC}"

# Start Frontend
echo -e "\n${YELLOW}Starting Frontend...${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
echo $! >> "$PID_FILE"
echo -e "${GREEN}Frontend started on http://localhost:3000${NC}"

echo -e "\n${GREEN}========================================"
echo "All Services Started!"
echo "========================================${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo "  Frontend:     http://localhost:3000"
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  AI Engine:    http://localhost:8001"
echo "  Telephony:    http://localhost:8002"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo "  Backend:      $PROJECT_ROOT/logs/backend.log"
echo "  AI Engine:    $PROJECT_ROOT/logs/ai_engine.log"
echo "  Telephony:    $PROJECT_ROOT/logs/telephony.log"
echo "  Celery:       $PROJECT_ROOT/logs/celery_worker.log"
echo "  Frontend:     $PROJECT_ROOT/logs/frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait and keep script running
wait
