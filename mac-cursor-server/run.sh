#!/bin/bash

# Simple run script for the Python cursor server
# Usage: ./run.sh [environment variables]
# Example: DEBUG=1 SELFTEST=1 ./run.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/../.venv/bin/python"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at $VENV_PYTHON"
    echo "Please run: python -m venv ../.venv && pip install -r requirements.txt"
    exit 1
fi

# Check if dependencies are installed
if ! "$VENV_PYTHON" -c "import websockets, pynput" 2>/dev/null; then
    echo "Error: Dependencies not installed"
    echo "Please run: pip install -r requirements.txt"
    exit 1
fi

echo "Starting Python cursor server..."
echo "Environment variables:"
echo "  PORT=${PORT:-8080}"
echo "  GAIN=${GAIN:-1.2}"
echo "  MAX_STEP=${MAX_STEP:-60}"
echo "  FRICTION=${FRICTION:-0.12}"
echo "  DEBUG=${DEBUG:-0}"
echo "  SELFTEST=${SELFTEST:-0}"
echo ""

cd "$SCRIPT_DIR"
exec "$VENV_PYTHON" cursor_server.py