@echo off
REM ML Trading System - Start with Remote Access
REM This script starts the system and enables remote access via ngrok

echo ========================================================================
echo                 ML TRADING SYSTEM WITH REMOTE ACCESS
echo ========================================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [1/4] Starting Docker containers...
docker compose up -d

if %errorlevel% neq 0 (
    echo ERROR: Failed to start containers!
    pause
    exit /b 1
)

echo OK - Containers starting
echo.

echo [2/4] Waiting for services to be ready...
timeout /t 15 /nobreak >nul
echo OK - Services should be ready
echo.

echo [3/4] Starting ngrok tunnel for remote access...
echo.
echo NOTE: You need Python with pyngrok installed for this step.
echo If you haven't installed it yet, run: pip install pyngrok
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Python not found!
    echo.
    echo The system is running, but remote access won't be available.
    echo You can still access locally at http://localhost:8501
    echo.
    goto :skip_ngrok
)

REM Start ngrok in a new window
start "Ngrok Tunnel" python scripts/setup_remote_access.py

echo OK - Ngrok tunnel started in new window
echo.

:skip_ngrok

echo [4/4] Opening local dashboard...
timeout /t 3 /nobreak >nul
start http://localhost:8501

echo.
echo ========================================================================
echo                          SYSTEM RUNNING!
echo ========================================================================
echo.
echo Local Dashboard:  http://localhost:8501
echo API Documentation: http://localhost:8000/docs
echo.
echo Check the Ngrok window for the public URL (if available)
echo.
echo Default login:
echo   Username: admin
echo   Password: admin123
echo.
echo IMPORTANT: Change the password in ui/auth_config.yaml!
echo.
echo To stop: docker compose down
echo.
echo ========================================================================
echo.
pause
