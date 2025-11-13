#!/bin/bash
# ML Trading System - Start with Remote Access
# This script starts the system and enables remote access via ngrok

echo "========================================================================"
echo "               ML TRADING SYSTEM WITH REMOTE ACCESS"
echo "========================================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "[1/4] Starting Docker containers..."
docker compose up -d

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start containers!"
    exit 1
fi

echo "OK - Containers starting"
echo ""

echo "[2/4] Waiting for services to be ready..."
sleep 15
echo "OK - Services should be ready"
echo ""

echo "[3/4] Starting ngrok tunnel for remote access..."
echo ""
echo "NOTE: You need Python with pyngrok installed for this step."
echo "If you haven't installed it yet, run: pip install pyngrok"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "WARNING: Python not found!"
    echo ""
    echo "The system is running, but remote access won't be available."
    echo "You can still access locally at http://localhost:8501"
    echo ""
else
    # Start ngrok in background
    python3 scripts/setup_remote_access.py &
    NGROK_PID=$!

    echo "OK - Ngrok tunnel started (PID: $NGROK_PID)"
    echo ""
fi

echo "[4/4] Opening local dashboard..."
sleep 3

# Open browser based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://localhost:8501
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8501
    else
        echo "Please open http://localhost:8501 in your browser"
    fi
fi

echo ""
echo "========================================================================"
echo "                        SYSTEM RUNNING!"
echo "========================================================================"
echo ""
echo "Local Dashboard:    http://localhost:8501"
echo "API Documentation:  http://localhost:8000/docs"
echo ""
echo "Check console output above for the ngrok public URL (if available)"
echo ""
echo "Default login:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "IMPORTANT: Change the password in ui/auth_config.yaml!"
echo ""
echo "To stop: docker compose down"
echo ""
echo "========================================================================"
echo ""
