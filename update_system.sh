#!/bin/bash
# Update Trading System with New Features
# This rebuilds containers with authentication and remote access support

echo "========================================================================"
echo "         UPDATING ML TRADING SYSTEM WITH NEW FEATURES"
echo "========================================================================"
echo ""
echo "This will:"
echo " - Rebuild containers with new dependencies"
echo " - Install streamlit-authenticator for password protection"
echo " - Install pyngrok for remote access"
echo " - Update UI with new charts and features"
echo ""

read -p "Press Enter to continue..."

echo "[1/4] Stopping existing containers..."
docker compose down
echo "OK"
echo ""

echo "[2/4] Removing old UI container to force rebuild..."
docker rmi trade-claude-upload-master-prompt-011cv4yvkednfpe41cyck8ni-ui 2>/dev/null || true
echo "OK"
echo ""

echo "[3/4] Rebuilding containers with new dependencies (~5 min)..."
docker compose build --no-cache ui
if [ $? -ne 0 ]; then
    echo "ERROR: Build failed!"
    exit 1
fi
echo "OK"
echo ""

echo "[4/4] Starting updated system..."
docker compose up -d
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start containers!"
    exit 1
fi
echo "OK"
echo ""

echo "Waiting for services to start..."
sleep 15
echo ""

echo "========================================================================"
echo "                        UPDATE COMPLETE!"
echo "========================================================================"
echo ""
echo "NEW FEATURES ACTIVE:"
echo " - Password-protected dashboard"
echo " - Live price charts with indicators"
echo " - Paper trading tab with real-time positions"
echo " - Performance analysis with trade markers"
echo " - Remote access support (via start_with_remote_access.sh)"
echo ""
echo "Opening dashboard..."
sleep 3

# Open browser based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:8501
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:8501 2>/dev/null || echo "Please open http://localhost:8501 in your browser"
fi

echo ""
echo "========================================================================"
echo ""
echo "LOGIN CREDENTIALS:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "IMPORTANT: Change the password in ui/auth_config.yaml after login!"
echo ""
echo "To use remote access: Run ./start_with_remote_access.sh instead"
echo ""
echo "========================================================================"
echo ""
