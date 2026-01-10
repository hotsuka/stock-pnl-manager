#!/bin/bash
# Stock P&L Manager - Production Startup Script (Linux/macOS)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Stock P&L Manager - Production Startup${NC}"
echo -e "${GREEN}======================================${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root is not recommended${NC}"
fi

# Change to project directory
cd "$PROJECT_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file from .env.example"
    echo "cp .env.example .env"
    exit 1
fi

# Load environment variables
echo -e "${YELLOW}Loading environment variables...${NC}"
export $(cat .env | grep -v '^#' | xargs)

# Check if SECRET_KEY is set
if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "dev-secret-key-please-change-in-production" ]; then
    echo -e "${RED}Error: SECRET_KEY is not set or using default value${NC}"
    echo "Please generate a secure SECRET_KEY:"
    echo "python -c \"import secrets; print(secrets.token_hex(32))\""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt --quiet

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p data/uploads
mkdir -p logs
mkdir -p backups

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
if ! flask db upgrade; then
    echo -e "${RED}Error: Database migration failed${NC}"
    exit 1
fi

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo -e "${RED}Error: Gunicorn not found${NC}"
    echo "Installing gunicorn..."
    pip install gunicorn
fi

# Configuration
WORKERS=${WORKERS:-4}
PORT=${PORT:-8000}
TIMEOUT=${TIMEOUT:-120}
LOG_FILE=${LOG_FILE:-logs/gunicorn.log}
ACCESS_LOG=${ACCESS_LOG:-logs/access.log}

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Configuration:${NC}"
echo -e "  Workers: ${WORKERS}"
echo -e "  Port: ${PORT}"
echo -e "  Timeout: ${TIMEOUT}s"
echo -e "  Log file: ${LOG_FILE}"
echo -e "${GREEN}======================================${NC}"

# Start gunicorn
echo -e "${GREEN}Starting Stock P&L Manager...${NC}"

exec gunicorn \
    --workers "$WORKERS" \
    --bind "0.0.0.0:$PORT" \
    --timeout "$TIMEOUT" \
    --access-logfile "$ACCESS_LOG" \
    --error-logfile "$LOG_FILE" \
    --log-level info \
    --capture-output \
    --enable-stdio-inheritance \
    'app:create_app("production")'
