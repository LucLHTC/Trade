@echo off
REM Complete fresh start - removes EVERYTHING and starts clean
REM Use this for a completely clean installation

echo ========================================================================
echo                    COMPLETE FRESH START
echo ========================================================================
echo.
echo WARNING: This will DELETE:
echo  - All Docker containers for this project
echo  - All Docker volumes (database data will be LOST)
echo  - All cached Docker images
echo.
echo Use this if you want a completely clean installation.
echo.

set /p confirm="Are you sure? Type YES to continue: "
if not "%confirm%"=="YES" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo [1/6] Stopping all containers...
docker compose down
echo OK
echo.

echo [2/6] Removing Docker volumes...
docker volume rm trade-claude-upload-master-prompt-011cv4yvkednfpe41cyck8ni_postgres_data 2>nul
echo OK - All data volumes removed
echo.

echo [3/6] Removing old images to force rebuild...
docker rmi trade-claude-upload-master-prompt-011cv4yvkednfpe41cyck8ni-api 2>nul
docker rmi trade-claude-upload-master-prompt-011cv4yvkednfpe41cyck8ni-ui 2>nul
docker rmi trade-claude-upload-master-prompt-011cv4yvkednfpe41cyck8ni-scheduler 2>nul
echo OK - Old images removed
echo.

echo [4/6] Cleaning Docker system...
docker system prune -f
echo OK
echo.

echo [5/6] Ready for fresh start!
echo.
echo Now you can run ONE_CLICK_SETUP.bat for a completely fresh installation.
echo.

set /p runsetup="Run ONE_CLICK_SETUP.bat now? (Y/N): "
if /i "%runsetup%"=="Y" (
    echo.
    echo [6/6] Starting ONE_CLICK_SETUP.bat...
    echo.
    call ONE_CLICK_SETUP.bat
) else (
    echo.
    echo Run ONE_CLICK_SETUP.bat when ready.
    echo.
    pause
)
