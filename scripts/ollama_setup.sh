#!/bin/bash
# Setup Ollama with Llama model

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "Ollama Setup for AI Collection Platform"
echo "========================================"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Ollama not found. Installing...${NC}"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "Download Ollama from: https://ollama.ai/download"
        echo "Or install via: brew install ollama"
        exit 1
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        echo -e "${RED}Unsupported OS. Please install Ollama manually from https://ollama.ai${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Ollama is installed${NC}"

# Start Ollama service if not running
echo -e "\n${YELLOW}Checking Ollama service...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama service..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi
echo -e "${GREEN}Ollama service is running${NC}"

# Pull the Qwen3 model
echo -e "\n${YELLOW}Pulling Qwen3 8B model...${NC}"
echo "This may take a while (4-5 GB download)"
ollama pull qwen3:8b

echo -e "\n${GREEN}========================================"
echo "Ollama Setup Complete!"
echo "========================================${NC}"
echo ""
echo "Model: qwen3:8b"
echo "Ollama URL: http://localhost:11434"
echo ""
echo "Test with: ollama run qwen3:8b 'Hello'"
