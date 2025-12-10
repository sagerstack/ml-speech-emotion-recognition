#!/bin/bash
#
# setup-local-env.sh - Set up local environment files for development
#
# This script creates .env.local files for both backend and frontend
# with secure defaults for local development.
#
# Usage:
#   ./scripts/setup-local-env.sh
#
# Run from the project root directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================="
echo "ML Speech Emotion Recognition - Local Environment Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a file exists
check_file() {
    if [ -f "$1" ]; then
        return 0
    else
        return 1
    fi
}

# Backend .env.local setup
echo "1. Setting up Backend environment..."
BACKEND_ENV_EXAMPLE="${PROJECT_ROOT}/backend/.env.example"
BACKEND_ENV_LOCAL="${PROJECT_ROOT}/backend/.env.local"

if check_file "${BACKEND_ENV_LOCAL}"; then
    echo -e "${YELLOW}   Warning: ${BACKEND_ENV_LOCAL} already exists${NC}"
    read -p "   Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "   Skipping backend .env.local"
    else
        rm -f "${BACKEND_ENV_LOCAL}"
    fi
fi

if ! check_file "${BACKEND_ENV_LOCAL}"; then
    if check_file "${BACKEND_ENV_EXAMPLE}"; then
        cp "${BACKEND_ENV_EXAMPLE}" "${BACKEND_ENV_LOCAL}"

        # Generate a secure SECRET_KEY
        SECRET_KEY=$(openssl rand -hex 32)

        # Replace the placeholder SECRET_KEY (works on both macOS and Linux)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/your-super-secret-key-change-this-in-production/${SECRET_KEY}/" "${BACKEND_ENV_LOCAL}"
        else
            sed -i "s/your-super-secret-key-change-this-in-production/${SECRET_KEY}/" "${BACKEND_ENV_LOCAL}"
        fi

        echo -e "${GREEN}   Created: ${BACKEND_ENV_LOCAL}${NC}"
        echo -e "${GREEN}   Generated secure SECRET_KEY${NC}"
    else
        echo -e "${RED}   Error: ${BACKEND_ENV_EXAMPLE} not found${NC}"
        exit 1
    fi
fi

# Frontend .env.local setup
echo ""
echo "2. Setting up Frontend (Streamlit) environment..."
FRONTEND_ENV_EXAMPLE="${PROJECT_ROOT}/frontend/streamlit_app/.env.example"
FRONTEND_ENV_LOCAL="${PROJECT_ROOT}/frontend/streamlit_app/.env.local"

if check_file "${FRONTEND_ENV_LOCAL}"; then
    echo -e "${YELLOW}   Warning: ${FRONTEND_ENV_LOCAL} already exists${NC}"
    read -p "   Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "   Skipping frontend .env.local"
    else
        rm -f "${FRONTEND_ENV_LOCAL}"
    fi
fi

if ! check_file "${FRONTEND_ENV_LOCAL}"; then
    if check_file "${FRONTEND_ENV_EXAMPLE}"; then
        cp "${FRONTEND_ENV_EXAMPLE}" "${FRONTEND_ENV_LOCAL}"
        echo -e "${GREEN}   Created: ${FRONTEND_ENV_LOCAL}${NC}"
    else
        echo -e "${RED}   Error: ${FRONTEND_ENV_EXAMPLE} not found${NC}"
        exit 1
    fi
fi

# Check for required data files
echo ""
echo "3. Checking required data files..."

MODEL_FILE="${PROJECT_ROOT}/backend/models/v6/model.pkl"
REFERENCE_DATA="${PROJECT_ROOT}/backend/monitoring_data/reference_dataset.csv"

if check_file "${MODEL_FILE}"; then
    echo -e "${GREEN}   Model file found: backend/models/v6/model.pkl${NC}"
else
    echo -e "${YELLOW}   Warning: Model file not found: backend/models/v6/model.pkl${NC}"
    echo "   Please refer to the project submission details on how to download this file."
fi

if check_file "${REFERENCE_DATA}"; then
    echo -e "${GREEN}   Reference dataset found: backend/monitoring_data/reference_dataset.csv${NC}"
else
    echo -e "${YELLOW}   Warning: Reference dataset not found: backend/monitoring_data/reference_dataset.csv${NC}"
    echo "   Please refer to the project submission details on how to download this file."
    echo "   Creating monitoring_data directory..."
    mkdir -p "${PROJECT_ROOT}/backend/monitoring_data"
fi

# Summary
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "  Backend (Terminal 1):"
echo "    cd backend"
echo "    poetry install --with dev"
echo "    poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "  Frontend (Terminal 2):"
echo "    cd frontend/streamlit_app"
echo "    python -m venv .venv && source .venv/bin/activate"
echo "    pip install -r requirements.txt"
echo "    streamlit run src/ml-app.py --server.port=8510"
echo ""
echo "Access:"
echo "  Backend API:  http://localhost:8000/docs"
echo "  Streamlit UI: http://localhost:8510"
echo ""
