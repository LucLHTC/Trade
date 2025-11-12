# ====================================================================
# ML Trading System - ULTRA SIMPLE SETUP
# ====================================================================
# No fancy functions - just works!
# Pre-configured with your API key
# ====================================================================

param(
    [string]$ApiKey = "1BYPHFL2ENMBITNZ"
)

# Clear screen
Clear-Host

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "       ML TRADING SYSTEM - SIMPLE SETUP" -ForegroundColor Cyan
Write-Host "       Pre-configured - Just Wait!" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Start-Sleep -Seconds 1

# ====================================================================
# STEP 0: Detect OneDrive and Move if Needed
# ====================================================================
Write-Host "Step 0: Checking Location..." -ForegroundColor Magenta
Write-Host ""

$currentPath = Get-Location
$isOneDrive = $currentPath.Path -match "OneDrive"

if ($isOneDrive) {
    Write-Host "[!] Project is in OneDrive - moving to C:\Trading..." -ForegroundColor Yellow

    $targetPath = "C:\Trading"

    if (!(Test-Path $targetPath)) {
        New-Item -ItemType Directory -Force -Path $targetPath | Out-Null
    }

    Write-Host "[*] Copying files (30 seconds)..." -ForegroundColor Cyan
    Copy-Item -Path "$currentPath\*" -Destination $targetPath -Recurse -Force -ErrorAction SilentlyContinue

    Set-Location $targetPath
    Write-Host "[OK] Moved to: $targetPath" -ForegroundColor Green
} else {
    Write-Host "[OK] Location is fine" -ForegroundColor Green
}

Write-Host ""

# ====================================================================
# STEP 1: Check Docker
# ====================================================================
Write-Host "Step 1: Checking Docker..." -ForegroundColor Magenta
Write-Host ""

docker --version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker not installed!" -ForegroundColor Red
    Write-Host "Install from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Docker is installed" -ForegroundColor Green

docker compose version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker Compose not available!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Docker Compose available" -ForegroundColor Green

docker ps > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker is not running!" -ForegroundColor Red
    Write-Host "Start Docker Desktop and try again" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Docker is running" -ForegroundColor Green

Write-Host ""

# ====================================================================
# STEP 2: Clean Docker
# ====================================================================
Write-Host "Step 2: Cleaning Docker..." -ForegroundColor Magenta
Write-Host ""

Write-Host "[*] Stopping old containers..." -ForegroundColor Cyan
docker compose down 2>&1 | Out-Null

Write-Host "[*] Cleaning cache..." -ForegroundColor Cyan
docker system prune -a -f --volumes 2>&1 | Out-Null

Write-Host "[OK] Docker cleaned" -ForegroundColor Green
Write-Host ""

Write-Host "IMPORTANT: Restart Docker Desktop now for best results!" -ForegroundColor Yellow
Write-Host "1. Right-click whale icon in system tray" -ForegroundColor Yellow
Write-Host "2. Click 'Quit Docker Desktop'" -ForegroundColor Yellow
Write-Host "3. Start Docker Desktop again" -ForegroundColor Yellow
Write-Host "4. Wait 2 minutes" -ForegroundColor Yellow
Write-Host ""
$restart = Read-Host "Did you restart Docker Desktop? (Y/N)"

if ($restart -eq "Y" -or $restart -eq "y") {
    Write-Host "[*] Waiting for Docker..." -ForegroundColor Cyan

    for ($i = 1; $i -le 20; $i++) {
        Start-Sleep -Seconds 3
        docker ps > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Docker is ready" -ForegroundColor Green
            break
        }
        Write-Host "." -NoNewline
    }

    docker ps > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Docker not responding" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""

# ====================================================================
# STEP 3: Create .env File
# ====================================================================
Write-Host "Step 3: Creating Config..." -ForegroundColor Magenta
Write-Host ""

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
Write-Host "[OK] Config created with API key" -ForegroundColor Green

Write-Host ""

# ====================================================================
# STEP 4: Create Directories
# ====================================================================
Write-Host "Step 4: Creating Folders..." -ForegroundColor Magenta
Write-Host ""

$dirs = @("data/forex", "data/features", "data/labels", "models/current", "models/shadow", "models/archived", "logs/errors")
foreach ($dir in $dirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
}

Write-Host "[OK] All folders created" -ForegroundColor Green
Write-Host ""

# ====================================================================
# STEP 5: Start Containers
# ====================================================================
Write-Host "Step 5: Starting Containers (10-15 min first time)..." -ForegroundColor Magenta
Write-Host ""

Write-Host "[*] Building and starting..." -ForegroundColor Cyan
docker compose up --build -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start containers!" -ForegroundColor Red
    Write-Host "Try:" -ForegroundColor Yellow
    Write-Host "1. Restart Docker Desktop" -ForegroundColor Yellow
    Write-Host "2. Check disk space (need 10GB+)" -ForegroundColor Yellow
    Write-Host "3. Increase Docker memory to 6GB" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Containers started" -ForegroundColor Green
Write-Host ""

# ====================================================================
# STEP 6: Wait for Services
# ====================================================================
Write-Host "Step 6: Waiting for Services..." -ForegroundColor Magenta
Write-Host ""

Write-Host "[*] Waiting for database..." -ForegroundColor Cyan
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 2
    docker compose exec -T db pg_isready -U trader > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Database ready" -ForegroundColor Green
        break
    }
    Write-Host "." -NoNewline
}

Write-Host ""
Write-Host "[*] Waiting for API..." -ForegroundColor Cyan
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] API ready" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "." -NoNewline
    }
}

Write-Host ""
Write-Host ""

# ====================================================================
# STEP 7: Data & Training
# ====================================================================
Write-Host "Step 7: Data Collection & Training (20-30 min)..." -ForegroundColor Magenta
Write-Host ""

Write-Host "[1/4] Collecting 90 days of EUR/USD data (5 min)..." -ForegroundColor Cyan
docker compose exec -T api python -c "from src.data_collection.forex import ForexCollector; c = ForexCollector(); c.fetch_and_store('EURUSD', days=90)"
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Data collected" -ForegroundColor Green
} else {
    Write-Host "[WARN] Data collection had issues" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/4] Generating features (2-3 min)..." -ForegroundColor Cyan
docker compose exec -T api python -c "from src.features.manager import FeatureManager; m = FeatureManager(); m.generate_features('EURUSD')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Features generated" -ForegroundColor Green
} else {
    Write-Host "[WARN] Feature generation had issues" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/4] Generating labels (1 min)..." -ForegroundColor Cyan
docker compose exec -T api python -c "from src.labeling.manager import LabelManager; m = LabelManager(); m.generate_labels('EURUSD')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Labels generated" -ForegroundColor Green
} else {
    Write-Host "[WARN] Label generation had issues" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[4/4] Training model (10-15 min)..." -ForegroundColor Cyan
docker compose exec -T api python -c "from src.training.trainer import ModelTrainer; t = ModelTrainer(); t.train_ensemble('EURUSD')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Model trained!" -ForegroundColor Green
} else {
    Write-Host "[WARN] Model training had issues" -ForegroundColor Yellow
}

Write-Host ""

# ====================================================================
# STEP 8: Done!
# ====================================================================
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "                    SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard:  http://localhost:8501" -ForegroundColor Cyan
Write-Host "API Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health:     http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""

Write-Host "Opening dashboard..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
Start-Process "http://localhost:8501"

Write-Host ""
Write-Host "To stop: docker compose down" -ForegroundColor Yellow
Write-Host ""

Read-Host "Press Enter to exit (system keeps running)"
