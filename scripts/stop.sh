#!/bin/bash
# Stop all services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "Stopping AI Collection Platform"
echo "========================================"

# Kill processes from PID file
PID_FILE="$PROJECT_ROOT/.pids"
if [ -f "$PID_FILE" ]; then
    echo -e "${YELLOW}Stopping tracked processes...${NC}"
    while read pid; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  Stopped PID $pid"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
fi

# Kill by port
echo -e "\n${YELLOW}Checking for processes on ports...${NC}"
for port in 8000 8001 8002 3000; do
    pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null || true
        echo "  Stopped process on port $port"
    fi
done

# Kill Celery workers
echo -e "\n${YELLOW}Stopping Celery workers...${NC}"
pkill -f "celery.*worker" 2>/dev/null || true
pkill -f "celery.*beat" 2>/dev/null || true

echo -e "\n${GREEN}All services stopped${NC}"
