@echo off
REM ====================================================================
REM ML Trading System - One-Click Launcher for Windows
REM ====================================================================
REM Simply double-click this file to start the trading system!
REM ====================================================================

echo.
echo ========================================
echo   ML TRADING SYSTEM - QUICK START
echo ========================================
echo.

REM Check if PowerShell is available
where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell is not found!
    echo Please use Windows 7 or later.
    pause
    exit /b 1
)

REM Check if setup.ps1 exists
if not exist "%~dp0setup.ps1" (
    echo ERROR: setup.ps1 not found!
    echo Please make sure you're in the correct directory.
    pause
    exit /b 1
)

echo Starting automated setup...
echo.
echo This will:
echo  1. Check if Docker is installed and running
echo  2. Configure the system with your API key
echo  3. Start all containers
echo  4. Collect data and train the model
echo  5. Open the dashboard in your browser
echo.
echo The first run takes about 30 minutes.
echo.

REM Run the PowerShell setup script
powershell -ExecutionPolicy Bypass -File "%~dp0setup.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   SETUP COMPLETE!
    echo ========================================
    echo.
) else (
    echo.
    echo ========================================
    echo   SETUP HAD ERRORS
    echo ========================================
    echo.
    echo Please check the error messages above.
    echo.
)

pause
