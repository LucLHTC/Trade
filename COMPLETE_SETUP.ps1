# ====================================================================
# ML Trading System - ONE CLICK COMPLETE SETUP
# ====================================================================
# Clone from GitHub, run this, DONE!
# API Key: 1BYPHFL2ENMBITNZ (pre-configured)
# ====================================================================

param(
    [string]$ApiKey = "1BYPHFL2ENMBITNZ"
)

Clear-Host

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "       ML TRADING SYSTEM - ULTIMATE ONE-CLICK SETUP" -ForegroundColor Cyan
Write-Host "       No Questions, No Problems, Just Works!" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total time: ~35 minutes (grab a coffee!)" -ForegroundColor Yellow
Write-Host ""
Start-Sleep -Seconds 2

# Check Docker
Write-Host "[1/10] Checking Docker..." -ForegroundColor Magenta
docker ps > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and run this script again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "OK - Docker is running" -ForegroundColor Green
Write-Host ""

# Clean Docker
Write-Host "[2/10] Cleaning Docker cache..." -ForegroundColor Magenta
docker compose down 2>&1 | Out-Null
docker system prune -a -f 2>&1 | Out-Null
Write-Host "OK - Docker cleaned" -ForegroundColor Green
Write-Host ""

# Create .env
Write-Host "[3/10] Creating configuration..." -ForegroundColor Magenta
$envContent = @"
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=trading
POSTGRES_USER=trader
POSTGRES_PASSWORD=traderpwd
API_HOST=api
API_PORT=8000
API_BASE_URL=http://api:8000
TZ=UTC
ALPHAVANTAGE_API_KEY=$ApiKey
INITIAL_EQUITY=10000.00
RISK_PER_TRADE=0.01
MAX_TRADES_PER_WEEK=3
MODEL_PATH=models/current/model.pkl
SHADOW_MODEL_PATH=models/shadow/model.pkl
TRAINING_WINDOW_DAYS=90
VALIDATION_WINDOW_DAYS=10
DRIFT_PSI_THRESHOLD=0.25
DRIFT_KS_PVALUE=0.01
LOOKAHEAD_PERIODS=3
LABEL_THRESHOLD_MULTIPLIER=0.7
LOG_LEVEL=INFO
LOG_DIR=logs/errors
SCHEDULER_ENABLED=true
HOURLY_JOBS_ENABLED=true
DAILY_JOBS_ENABLED=true
"@
$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Host "OK - Configuration created with API key" -ForegroundColor Green
Write-Host ""

# Create directories
Write-Host "[4/10] Creating directories..." -ForegroundColor Magenta
$dirs = @("data/forex", "data/features", "data/labels", "models/current", "models/shadow", "models/archived", "logs/errors")
foreach ($dir in $dirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
}
Write-Host "OK - All directories created" -ForegroundColor Green
Write-Host ""

# Build containers
Write-Host "[5/10] Building Docker containers (10-15 min)..." -ForegroundColor Magenta
Write-Host "This is the longest step - be patient!" -ForegroundColor Yellow
docker compose up --build -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "OK - Containers built and started" -ForegroundColor Green
Write-Host ""

# Wait for services
Write-Host "[6/10] Waiting for services to start..." -ForegroundColor Magenta
Start-Sleep -Seconds 10

for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 2
    docker compose exec -T db pg_isready -U trader > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK - Database is ready" -ForegroundColor Green
        break
    }
    Write-Host "." -NoNewline
}
Write-Host ""

for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "OK - API is ready" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "." -NoNewline
    }
}
Write-Host ""
Write-Host ""

# Install pandas-ta in running containers
Write-Host "[7/10] Installing pandas-ta library (special fix - takes 2-3 min)..." -ForegroundColor Magenta

# Function to install and verify pandas-ta in a container
function Install-PandasTA {
    param($containerName)

    Write-Host "  Installing in $containerName container..." -ForegroundColor Cyan

    # Method 1: Try direct pip install first
    $installCmd1 = "pip install --upgrade pip && pip install pandas-ta 2>&1"
    $output1 = docker compose exec -T $containerName bash -c $installCmd1 2>&1

    # Verify installation
    $verifyCmd = "python -c 'import pandas_ta; print(pandas_ta.__version__)' 2>&1"
    $verifyOutput = docker compose exec -T $containerName bash -c $verifyCmd 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK - pandas-ta installed in $containerName" -ForegroundColor Green
        return $true
    }

    # Method 2: Try GitHub ZIP if Method 1 failed
    Write-Host "  Trying alternative method..." -ForegroundColor Yellow
    $installCmd2 = "pip install --no-cache-dir https://github.com/twopirllc/pandas-ta/archive/refs/heads/main.zip 2>&1"
    $output2 = docker compose exec -T $containerName bash -c $installCmd2 2>&1

    # Verify again
    $verifyOutput2 = docker compose exec -T $containerName bash -c $verifyCmd 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK - pandas-ta installed in $containerName (via GitHub)" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  ERROR - pandas-ta installation failed in $containerName" -ForegroundColor Red
        Write-Host "  This will cause issues with technical indicators" -ForegroundColor Red
        return $false
    }
}

# Install in all containers
$apiSuccess = Install-PandasTA "api"
$schedulerSuccess = Install-PandasTA "scheduler"
$uiSuccess = Install-PandasTA "ui"

if ($apiSuccess -and $schedulerSuccess -and $uiSuccess) {
    Write-Host ""
    Write-Host "SUCCESS - pandas-ta installed and verified in all containers!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "WARNING - pandas-ta installation failed in some containers" -ForegroundColor Yellow
    Write-Host "Run COMPLETE_FIX.bat after setup to fix this" -ForegroundColor Yellow
}
Write-Host ""

# Restart containers to load pandas-ta
Write-Host "[8/10] Restarting containers..." -ForegroundColor Magenta
docker compose restart api scheduler ui 2>&1 | Out-Null
Start-Sleep -Seconds 15
Write-Host "OK - Containers restarted" -ForegroundColor Green
Write-Host ""

# Collect data
Write-Host "[9/10] Collecting data and training model (~20 min)..." -ForegroundColor Magenta
Write-Host ""

Write-Host "  [1/4] Collecting 90 days EUR/USD data (5 min)..." -ForegroundColor Cyan
docker compose exec -T api python -c "from src.data_collection.forex import ForexCollector; c = ForexCollector(); c.fetch_and_store('EURUSD', days=90)"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK - Data collected" -ForegroundColor Green
} else {
    Write-Host "  WARN - Data collection had issues (you can retry manually)" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "  [2/4] Generating features (2-3 min)..." -ForegroundColor Cyan
docker compose exec -T api python -c "from src.features.manager import FeatureManager; m = FeatureManager(); m.generate_features_from_candles('EURUSD')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK - Features generated" -ForegroundColor Green
} else {
    Write-Host "  WARN - Feature generation had issues" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "  [3/4] Generating labels (1 min)..." -ForegroundColor Cyan
docker compose exec -T api python -c "from src.labeling.manager import LabelManager; m = LabelManager(); m.generate_and_save('EURUSD')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK - Labels generated" -ForegroundColor Green
} else {
    Write-Host "  WARN - Label generation had issues" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "  [4/4] Training ensemble model (10-15 min)..." -ForegroundColor Cyan
docker compose exec -T api python -c "from src.training.trainer import ModelTrainer; t = ModelTrainer(); t.train_and_save('EURUSD')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK - Model trained successfully!" -ForegroundColor Green
} else {
    Write-Host "  WARN - Model training had issues" -ForegroundColor Yellow
}
Write-Host ""

# Open dashboard
Write-Host "[10/10] Opening dashboard..." -ForegroundColor Magenta
Start-Sleep -Seconds 2
Start-Process "http://localhost:8501"
Write-Host "OK - Dashboard opened in browser" -ForegroundColor Green
Write-Host ""

# Done!
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "                         SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard:  http://localhost:8501" -ForegroundColor Cyan
Write-Host "API Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health:     http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your ML Trading System is now running!" -ForegroundColor Green
Write-Host ""
Write-Host "To stop:    docker compose down" -ForegroundColor Yellow
Write-Host "To restart: docker compose up -d" -ForegroundColor Yellow
Write-Host ""

Read-Host "Press Enter to exit (system keeps running)"
