@echo off
REM ====================================================================
REM Fix Authentication - Update password hash in running container
REM ====================================================================

echo.
echo ========================================
echo   FIXING AUTHENTICATION
echo ========================================
echo.
echo This will update the password hash in the running UI container
echo Default login: admin / admin123
echo.

REM Copy updated auth_config.yaml to running container
echo Copying updated auth_config.yaml to container...
docker cp ui/auth_config.yaml trading_ui:/app/ui/auth_config.yaml

if %ERRORLEVEL% EQU 0 (
    echo OK - File copied successfully
    echo.
    echo Restarting UI container...
    docker compose restart ui
    echo.
    echo ========================================
    echo   AUTH FIX COMPLETE
    echo ========================================
    echo.
    echo Login credentials:
    echo   Username: admin
    echo   Password: admin123
    echo.
    echo Dashboard: http://localhost:8501
    echo.
) else (
    echo.
    echo ERROR - Failed to copy file
    echo Make sure the container is running: docker compose up -d
    echo.
)

pause
