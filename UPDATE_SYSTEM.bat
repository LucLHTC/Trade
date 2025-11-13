@echo off
REM Update Trading System with New Features
REM This rebuilds containers with authentication and remote access support

echo ========================================================================
echo           UPDATING ML TRADING SYSTEM WITH NEW FEATURES
echo ========================================================================
echo.
echo This will:
echo  - Rebuild containers with new dependencies
echo  - Install streamlit-authenticator for password protection
echo  - Install pyngrok for remote access
echo  - Update UI with new charts and features
echo.

pause

echo [1/4] Stopping existing containers...
docker compose down
echo OK
echo.

echo [2/4] Removing old UI container to force rebuild...
docker rmi trade-claude-upload-master-prompt-011cv4yvkednfpe41cyck8ni-ui 2>nul
echo OK
echo.

echo [3/4] Rebuilding containers with new dependencies (~5 min)...
docker compose build --no-cache ui
if %errorlevel% neq 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)
echo OK
echo.

echo [4/4] Starting updated system...
docker compose up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start containers!
    pause
    exit /b 1
)
echo OK
echo.

echo Waiting for services to start...
timeout /t 15 /nobreak >nul
echo.

echo ========================================================================
echo                          UPDATE COMPLETE!
echo ========================================================================
echo.
echo NEW FEATURES ACTIVE:
echo  - Password-protected dashboard
echo  - Live price charts with indicators
echo  - Paper trading tab with real-time positions
echo  - Performance analysis with trade markers
echo  - Remote access support (via START_WITH_REMOTE_ACCESS.bat)
echo.
echo Opening dashboard...
timeout /t 3 /nobreak >nul
start http://localhost:8501
echo.
echo ========================================================================
echo.
echo LOGIN CREDENTIALS:
echo   Username: admin
echo   Password: admin123
echo.
echo IMPORTANT: Change the password in ui/auth_config.yaml after login!
echo.
echo To use remote access: Run START_WITH_REMOTE_ACCESS.bat instead
echo.
echo ========================================================================
echo.
pause
