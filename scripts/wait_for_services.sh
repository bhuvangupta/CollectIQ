#!/bin/bash
# Wait for dependent services to be ready

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Waiting for services to be ready...${NC}"

# Wait for PostgreSQL
echo -n "PostgreSQL: "
until pg_isready -h ${POSTGRES_HOST:-postgres} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-postgres} > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "${GREEN}Ready${NC}"

# Wait for Redis
echo -n "Redis: "
until redis-cli -h ${REDIS_HOST:-redis} -p ${REDIS_PORT:-6379} ping > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "${GREEN}Ready${NC}"

# Wait for MinIO
echo -n "MinIO: "
until curl -sf http://${MINIO_HOST:-minio}:${MINIO_PORT:-9000}/minio/health/live > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "${GREEN}Ready${NC}"

# Wait for Ollama (optional, with timeout)
echo -n "Ollama: "
OLLAMA_TIMEOUT=60
OLLAMA_COUNT=0
until curl -sf http://${OLLAMA_HOST:-ollama}:11434/api/tags > /dev/null 2>&1; do
    echo -n "."
    sleep 1
    OLLAMA_COUNT=$((OLLAMA_COUNT + 1))
    if [ $OLLAMA_COUNT -ge $OLLAMA_TIMEOUT ]; then
        echo -e "${YELLOW}Timeout (will continue without)${NC}"
        break
    fi
done
if [ $OLLAMA_COUNT -lt $OLLAMA_TIMEOUT ]; then
    echo -e "${GREEN}Ready${NC}"
fi

echo -e "${GREEN}All services ready!${NC}"
