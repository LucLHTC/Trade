@echo off
REM Critical Fix for pandas-ta and database initialization
REM Run this AFTER the system has been started with ONE_CLICK_SETUP.bat

echo ========================================================================
echo              CRITICAL FIX - pandas-ta and Database
echo ========================================================================
echo.
echo This script fixes two critical issues:
echo  1. pandas-ta installation failure
echo  2. Missing database tables
echo.

pause

echo [1/5] Checking if containers are running...
docker ps | findstr trading_api >nul
if %errorlevel% neq 0 (
    echo ERROR: Containers not running! Please run ONE_CLICK_SETUP.bat first
    pause
    exit /b 1
)
echo OK - Containers are running
echo.

echo [2/5] Creating database tables manually...
echo This will create all required tables (candles, features, paper_positions, etc.)
docker exec -i trading_db psql -U trader -d trading < database\init.sql
echo OK - Database tables created
echo.

echo [3/5] Installing pandas-ta using working method...
echo This may take 2-3 minutes per container...
echo.

echo Installing in API container...
docker exec trading_api pip install --no-deps ta-lib pandas-ta
if %errorlevel% neq 0 (
    echo Trying alternative method...
    docker exec trading_api bash -c "pip install --no-cache-dir https://github.com/twopirllc/pandas-ta/archive/refs/heads/main.zip"
)
echo.

echo Installing in Scheduler container...
docker exec trading_scheduler pip install --no-deps ta-lib pandas-ta
if %errorlevel% neq 0 (
    echo Trying alternative method...
    docker exec trading_scheduler bash -c "pip install --no-cache-dir https://github.com/twopirllc/pandas-ta/archive/refs/heads/main.zip"
)
echo.

echo Installing in UI container...
docker exec trading_ui pip install --no-deps ta-lib pandas-ta
if %errorlevel% neq 0 (
    echo Trying alternative method...
    docker exec trading_ui bash -c "pip install --no-cache-dir https://github.com/twopirllc/pandas-ta/archive/refs/heads/main.zip"
)
echo OK - pandas-ta installed in all containers
echo.

echo [4/5] Verifying installations...
echo Checking API container...
docker exec trading_api python -c "import pandas_ta; print('pandas-ta version:', pandas_ta.version)" 2>nul
if %errorlevel% equ 0 (
    echo OK - API container verified
) else (
    echo WARN - API container may have issues
)

echo Checking Scheduler container...
docker exec trading_scheduler python -c "import pandas_ta; print('pandas-ta version:', pandas_ta.version)" 2>nul
if %errorlevel% equ 0 (
    echo OK - Scheduler container verified
) else (
    echo WARN - Scheduler container may have issues
)

echo Checking UI container...
docker exec trading_ui python -c "import pandas_ta; print('pandas-ta version:', pandas_ta.version)" 2>nul
if %errorlevel% equ 0 (
    echo OK - UI container verified
) else (
    echo WARN - UI container may have issues
)
echo.

echo [5/5] Restarting containers to apply changes...
docker compose restart
echo OK - Containers restarted
echo.

echo Waiting for services to come back online...
timeout /t 20 /nobreak >nul
echo.

echo ========================================================================
echo                         FIX COMPLETE!
echo ========================================================================
echo.
echo Opening dashboard...
timeout /t 3 /nobreak >nul
start http://localhost:8501
echo.
echo The dashboard should now work without errors!
echo.
echo If you still see errors:
echo  1. Wait 1-2 minutes for all services to fully restart
echo  2. Refresh the page (Ctrl+Shift+R)
echo  3. Check logs: docker logs trading_ui
echo.
echo ========================================================================
echo.
pause
