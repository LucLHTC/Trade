@echo off
REM ====================================================================
REM ML TRADING SYSTEM - ULTIMATE SIMPLE SETUP
REM ====================================================================
REM Just double-click this file!
REM Everything is pre-configured with your API key
REM ====================================================================

echo.
echo ========================================================================
echo.
echo           START HERE - ML TRADING SYSTEM SETUP
echo.
echo   This is the SIMPLEST way to get started!
echo   Your API key is already configured.
echo.
echo   Total time: About 30 minutes on first run
echo.
echo ========================================================================
echo.
echo.

REM Check PowerShell
where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell not found!
    pause
    exit /b 1
)

REM Check if setup-simple.ps1 exists
if not exist "%~dp0setup-simple.ps1" (
    echo ERROR: setup-simple.ps1 not found!
    echo Make sure all files are in the same folder.
    pause
    exit /b 1
)

echo Starting setup...
echo.

REM Run the simple PowerShell setup
powershell -ExecutionPolicy Bypass -File "%~dp0setup-simple.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo         SYSTEM READY!
    echo ========================================
    echo.
) else (
    echo.
    echo ========================================
    echo      SETUP HAD SOME ISSUES
    echo ========================================
    echo.
)

pause
