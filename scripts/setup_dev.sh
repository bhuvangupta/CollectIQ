#!/bin/bash
# Development environment setup script

set -e

echo "==================================="
echo "AI Collection Platform Dev Setup"
echo "==================================="

# Check prerequisites
echo ""
echo "Checking prerequisites..."

check_command() {
    if command -v $1 &> /dev/null; then
        echo "✓ $1 is installed"
        return 0
    else
        echo "✗ $1 is NOT installed"
        return 1
    fi
}

MISSING=0
check_command docker || MISSING=1
check_command docker-compose || MISSING=1
check_command node || echo "  (optional, for local frontend dev)"
check_command python3 || echo "  (optional, for local backend dev)"

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "Please install missing required dependencies and run again."
    exit 1
fi

# Create .env file if not exists
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo "  Please review and update .env with your settings"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/postgres data/redis data/minio data/ollama
echo "✓ Created data directories"

# Build Docker images
echo ""
echo "Building Docker images (this may take a while)..."
docker-compose build

# Start infrastructure services
echo ""
echo "Starting infrastructure services..."
docker-compose up -d postgres redis minio

# Wait for services
echo ""
echo "Waiting for services to be ready..."
sleep 10

# Initialize database
echo ""
echo "Initializing database..."
docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE loan_collection;" 2>/dev/null || true
docker-compose exec -T postgres psql -U postgres -d loan_collection -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" 2>/dev/null || true
docker-compose exec -T postgres psql -U postgres -d loan_collection -c "CREATE EXTENSION IF NOT EXISTS timescaledb;" 2>/dev/null || true

# Start Ollama and pull model
echo ""
echo "Starting Ollama and pulling Llama model..."
docker-compose up -d ollama
sleep 5
docker-compose exec -T ollama ollama pull llama3.1:8b || echo "  (Model will be pulled on first use)"

# Start all services
echo ""
echo "Starting all services..."
docker-compose up -d

# Run migrations
echo ""
echo "Running database migrations..."
sleep 5
docker-compose exec -T backend alembic upgrade head || echo "  (Migrations may need to be run manually)"

# Seed data (optional)
read -p "Seed database with sample data? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Seeding database..."
    docker-compose exec -T backend python -m scripts.seed_data || echo "  (Seeding may need to be run manually)"
fi

# Print success message
echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Services are running at:"
echo "  Frontend:      http://localhost:3000"
echo "  Backend API:   http://localhost:8000"
echo "  API Docs:      http://localhost:8000/docs"
echo "  AI Engine:     http://localhost:8001"
echo "  Telephony:     http://localhost:8002"
echo "  MinIO Console: http://localhost:9001"
echo ""
echo "Default login credentials:"
echo "  Email:    admin@collectiq.com"
echo "  Password: password123"
echo ""
echo "Useful commands:"
echo "  make logs        - View logs"
echo "  make down        - Stop services"
echo "  make clean       - Remove all data"
echo "  make help        - Show all commands"
echo ""
