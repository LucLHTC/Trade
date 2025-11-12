@echo off
REM ====================================================================
REM ML TRADING SYSTEM - ONE CLICK SETUP
REM ====================================================================
REM Just double-click this file after git clone!
REM Everything is automated - NO questions asked!
REM ====================================================================

echo.
echo ================================================================================
echo.
echo                   ML TRADING SYSTEM - ONE CLICK SETUP
echo.
echo   After git clone, just run this - EVERYTHING is automated!
echo.
echo   Total time: About 35 minutes
echo   - Building containers: 10-15 min
echo   - Collecting data: 5 min
echo   - Training model: 10-15 min
echo.
echo ================================================================================
echo.
echo.

REM Check PowerShell
where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell not found!
    pause
    exit /b 1
)

REM Check if setup script exists
if not exist "%~dp0COMPLETE_SETUP.ps1" (
    echo ERROR: COMPLETE_SETUP.ps1 not found!
    pause
    exit /b 1
)

echo Starting complete automated setup...
echo.
echo NO questions will be asked!
echo Your API key is already configured.
echo.
pause

REM Run PowerShell setup
powershell -ExecutionPolicy Bypass -File "%~dp0COMPLETE_SETUP.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo         SYSTEM READY!
    echo ========================================
    echo.
    echo Dashboard: http://localhost:8501
    echo.
) else (
    echo.
    echo ========================================
    echo      SETUP HAD ISSUES
    echo ========================================
    echo.
)

pause
