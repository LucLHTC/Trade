@echo off
REM ====================================================================
REM ML Trading System - Stop Script for Windows
REM ====================================================================
REM Double-click this file to gracefully stop the trading system
REM ====================================================================

echo.
echo ========================================
echo   ML TRADING SYSTEM - STOP
echo ========================================
echo.

echo Stopping all containers...
echo.

docker compose down

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   SYSTEM STOPPED SUCCESSFULLY
    echo ========================================
    echo.
    echo All containers have been stopped.
    echo Your data is preserved and safe.
    echo.
    echo To restart, double-click START_SYSTEM.bat
    echo.
) else (
    echo.
    echo ========================================
    echo   ERROR STOPPING SYSTEM
    echo ========================================
    echo.
    echo Please check if Docker Desktop is running.
    echo.
)

pause
