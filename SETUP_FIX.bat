@echo off
REM ====================================================================
REM ML Trading System - SMART FIX & SETUP
REM ====================================================================
REM This script automatically fixes:
REM - OneDrive location issues (auto-relocates)
REM - Docker I/O errors (cleans cache)
REM - All common setup problems
REM
REM Just double-click and follow the prompts!
REM ====================================================================

echo.
echo ========================================================================
echo.
echo           ML TRADING SYSTEM - SMART SETUP (AUTO-FIX)
echo.
echo   This script will automatically detect and fix common problems:
echo   - OneDrive location issues
echo   - Docker cache/I/O errors
echo   - Configuration problems
echo.
echo   Just answer a few questions and it handles everything!
echo.
echo ========================================================================
echo.
echo.

REM Check if PowerShell is available
where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell not found!
    echo This script requires Windows PowerShell.
    echo.
    pause
    exit /b 1
)

REM Check if setup-fixed.ps1 exists
if not exist "%~dp0setup-fixed.ps1" (
    echo ERROR: setup-fixed.ps1 not found!
    echo Please make sure all files are in the same folder.
    echo.
    pause
    exit /b 1
)

echo Starting smart setup...
echo.
echo NOTE: You may be asked to:
echo  - Enter your API key (get free at alphavantage.co)
echo  - Restart Docker Desktop (we'll guide you)
echo  - Answer Y/N to a few questions
echo.
echo Everything else is automatic!
echo.
pause

REM Run the PowerShell setup script
powershell -ExecutionPolicy Bypass -File "%~dp0setup-fixed.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================================
    echo                         SETUP SUCCESSFUL!
    echo ========================================================================
    echo.
    echo Your trading system is now running!
    echo Open your browser to: http://localhost:8501
    echo.
    echo To stop the system: Run STOP_SYSTEM.bat
    echo.
) else (
    echo.
    echo ========================================================================
    echo                      SETUP HAD ERRORS
    echo ========================================================================
    echo.
    echo Please check the error messages above.
    echo.
    echo Common solutions:
    echo  1. Make sure Docker Desktop is running
    echo  2. Check you have at least 10GB free disk space
    echo  3. Try restarting Docker Desktop and running this again
    echo.
)

echo.
pause
