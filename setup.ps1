# ====================================================================
# ML Trading System - Automated Setup Script for Windows
# ====================================================================
# This script automates the complete setup process:
# - Checks prerequisites (Docker)
# - Creates configuration files
# - Sets up directories
# - Starts Docker containers
# - Runs initial data collection and model training
# - Opens the UI in your browser
# ====================================================================

param(
    [string]$ApiKey = "",
    [switch]$SkipTraining,
    [switch]$Quick,
    [int]$DataDays = 90
)

# Colors for output
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Error-Custom { param($Message) Write-Host "✗ $Message" -ForegroundColor Red }
function Write-Info { param($Message) Write-Host "ℹ $Message" -ForegroundColor Cyan }
function Write-Warning-Custom { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Step { param($Message) Write-Host "`n══ $Message ══" -ForegroundColor Magenta }

# Banner
Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       ML TRADING SYSTEM - AUTOMATED SETUP                ║
║       EUR/USD Algorithmic Trading with ML                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

Start-Sleep -Seconds 1

# ====================================================================
# STEP 1: Check Prerequisites
# ====================================================================
Write-Step "Step 1/8: Checking Prerequisites"

Write-Info "Checking Docker installation..."
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker is installed: $dockerVersion"
    } else {
        throw "Docker not found"
    }
} catch {
    Write-Error-Custom "Docker is not installed or not running!"
    Write-Info "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
    Write-Info "Then restart this script."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Info "Checking Docker Compose..."
try {
    $composeVersion = docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker Compose is available: $composeVersion"
    } else {
        throw "Docker Compose not found"
    }
} catch {
    Write-Error-Custom "Docker Compose is not available!"
    Write-Info "Please update Docker Desktop to the latest version."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Info "Checking if Docker daemon is running..."
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker daemon is running"
    } else {
        throw "Docker daemon not running"
    }
} catch {
    Write-Error-Custom "Docker Desktop is not running!"
    Write-Info "Please start Docker Desktop and wait for it to fully initialize."
    Write-Info "Look for the whale icon in your system tray (bottom-right)."
    Read-Host "Press Enter to exit"
    exit 1
}

# ====================================================================
# STEP 2: Get API Key
# ====================================================================
Write-Step "Step 2/8: Configuration"

$envPath = ".env"
$apiKeyFromEnv = ""

# Check if .env exists and has API key
if (Test-Path $envPath) {
    Write-Info "Found existing .env file"
    $envContent = Get-Content $envPath -Raw
    if ($envContent -match "ALPHAVANTAGE_API_KEY=([A-Z0-9]+)") {
        $apiKeyFromEnv = $matches[1]
        if ($apiKeyFromEnv -ne "YOUR_API_KEY_HERE" -and $apiKeyFromEnv.Length -gt 5) {
            Write-Success "Using API key from .env file"
            $ApiKey = $apiKeyFromEnv
        }
    }
}

# If no API key found, ask user
if ([string]::IsNullOrEmpty($ApiKey) -or $ApiKey -eq "YOUR_API_KEY_HERE") {
    Write-Info "Alpha Vantage API Key is required for data collection."
    Write-Info "Get your free API key here: https://www.alphavantage.co/support/#api-key"
    Write-Host ""
    $ApiKey = Read-Host "Enter your Alpha Vantage API key"

    if ([string]::IsNullOrEmpty($ApiKey)) {
        Write-Error-Custom "API key is required!"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Success "API key configured"

# ====================================================================
# STEP 3: Create Configuration Files
# ====================================================================
Write-Step "Step 3/8: Creating Configuration Files"

# Create .env file
if (Test-Path ".env.example") {
    Write-Info "Creating .env from template..."
    $envContent = Get-Content ".env.example" -Raw
    $envContent = $envContent -replace "ALPHAVANTAGE_API_KEY=YOUR_API_KEY_HERE", "ALPHAVANTAGE_API_KEY=$ApiKey"
    $envContent | Out-File -FilePath ".env" -Encoding UTF8 -NoNewline
    Write-Success ".env file created"
} else {
    Write-Warning-Custom ".env.example not found, creating basic .env file..."

    $basicEnv = @"
# Database Configuration
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=trading
POSTGRES_USER=trader
POSTGRES_PASSWORD=traderpwd

# API Configuration
API_HOST=api
API_PORT=8000
API_BASE_URL=http://api:8000

# Timezone
TZ=UTC

# Alpha Vantage API
ALPHAVANTAGE_API_KEY=$ApiKey

# Trading Configuration
INITIAL_EQUITY=10000.00
RISK_PER_TRADE=0.01
MAX_TRADES_PER_WEEK=3

# Model Configuration
MODEL_PATH=models/current/model.pkl
SHADOW_MODEL_PATH=models/shadow/model.pkl
TRAINING_WINDOW_DAYS=90
VALIDATION_WINDOW_DAYS=10

# Drift Detection
DRIFT_PSI_THRESHOLD=0.25
DRIFT_KS_PVALUE=0.01

# Feature Engineering
LOOKAHEAD_PERIODS=3
LABEL_THRESHOLD_MULTIPLIER=0.7

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs/errors

# Scheduler
SCHEDULER_ENABLED=true
HOURLY_JOBS_ENABLED=true
DAILY_JOBS_ENABLED=true
"@

    $basicEnv | Out-File -FilePath ".env" -Encoding UTF8
    Write-Success ".env file created"
}

# ====================================================================
# STEP 4: Create Required Directories
# ====================================================================
Write-Step "Step 4/8: Creating Directory Structure"

$directories = @(
    "data/forex",
    "data/features",
    "data/labels",
    "models/current",
    "models/shadow",
    "models/archived",
    "logs/errors"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Success "Created: $dir"
    } else {
        Write-Info "Already exists: $dir"
    }
}

# ====================================================================
# STEP 5: Start Docker Containers
# ====================================================================
Write-Step "Step 5/8: Starting Docker Containers"

Write-Info "This will take 5-10 minutes on first run (downloading images, building containers)..."
Write-Info "Starting containers..."

# Stop any existing containers
docker compose down 2>&1 | Out-Null

# Start containers
try {
    docker compose up --build -d
    if ($LASTEXITCODE -ne 0) {
        throw "Docker compose failed"
    }
    Write-Success "Containers started successfully"
} catch {
    Write-Error-Custom "Failed to start containers!"
    Write-Info "Check the error messages above."
    Read-Host "Press Enter to exit"
    exit 1
}

# ====================================================================
# STEP 6: Wait for Services to be Ready
# ====================================================================
Write-Step "Step 6/8: Waiting for Services to Initialize"

Write-Info "Waiting for database to be ready..."
$maxAttempts = 30
$attempt = 0
$dbReady = $false

while ($attempt -lt $maxAttempts -and !$dbReady) {
    Start-Sleep -Seconds 2
    $attempt++

    $healthCheck = docker compose ps --format json | ConvertFrom-Json
    $dbService = $healthCheck | Where-Object { $_.Service -eq "db" }

    if ($dbService.Health -eq "healthy") {
        $dbReady = $true
        Write-Success "Database is ready"
    } else {
        Write-Host "." -NoNewline
    }
}

if (!$dbReady) {
    Write-Error-Custom "Database failed to start in time"
    Write-Info "Check logs with: docker compose logs db"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Info "Waiting for API to be ready..."
$attempt = 0
$apiReady = $false

while ($attempt -lt $maxAttempts -and !$apiReady) {
    Start-Sleep -Seconds 2
    $attempt++

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $apiReady = $true
            Write-Success "API is ready"
        }
    } catch {
        Write-Host "." -NoNewline
    }
}

if (!$apiReady) {
    Write-Error-Custom "API failed to start in time"
    Write-Info "Check logs with: docker compose logs api"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Info "Waiting for UI to be ready..."
$attempt = 0
$uiReady = $false

while ($attempt -lt 20 -and !$uiReady) {
    Start-Sleep -Seconds 2
    $attempt++

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8501" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $uiReady = $true
            Write-Success "UI is ready"
        }
    } catch {
        Write-Host "." -NoNewline
    }
}

if (!$uiReady) {
    Write-Warning-Custom "UI took longer than expected, but may still be starting..."
}

# ====================================================================
# STEP 7: Initial Data Setup (if requested)
# ====================================================================
if (!$SkipTraining) {
    Write-Step "Step 7/8: Initial Data Setup and Model Training"

    if ($Quick) {
        $DataDays = 30
        Write-Info "Quick mode: Using 30 days of data"
    }

    Write-Info "This process takes ~20-30 minutes. Please be patient..."
    Write-Host ""

    # 1. Collect historical data
    Write-Info "1/4: Collecting $DataDays days of historical EUR/USD data..."
    Write-Info "     (This takes ~5 minutes due to API rate limits)"

    $command = @"
from src.data_collection.forex import ForexCollector
import sys
print('Initializing ForexCollector...')
collector = ForexCollector()
print('Fetching EUR/USD data...')
collector.fetch_and_store('EURUSD', days=$DataDays)
print('✓ Data collection complete!')
"@

    try {
        docker compose exec -T api python -c $command
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Historical data collected"
        } else {
            throw "Data collection failed"
        }
    } catch {
        Write-Error-Custom "Failed to collect historical data"
        Write-Info "You can try manually with: docker compose exec api python -c ""from src.data_collection.forex import ForexCollector; ForexCollector().fetch_and_store('EURUSD', days=$DataDays)"""
    }

    # 2. Generate features
    Write-Info "2/4: Generating features (technical indicators, macro events)..."
    Write-Info "     (This takes ~2-3 minutes)"

    $command = @"
from src.features.manager import FeatureManager
import sys
print('Initializing FeatureManager...')
manager = FeatureManager()
print('Generating features...')
manager.generate_features('EURUSD')
print('✓ Feature generation complete!')
"@

    try {
        docker compose exec -T api python -c $command
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Features generated"
        } else {
            throw "Feature generation failed"
        }
    } catch {
        Write-Error-Custom "Failed to generate features"
    }

    # 3. Generate labels
    Write-Info "3/4: Generating labels (trade signals)..."
    Write-Info "     (This takes ~1 minute)"

    $command = @"
from src.labeling.manager import LabelManager
import sys
print('Initializing LabelManager...')
manager = LabelManager()
print('Generating labels...')
manager.generate_labels('EURUSD')
print('✓ Label generation complete!')
"@

    try {
        docker compose exec -T api python -c $command
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Labels generated"
        } else {
            throw "Label generation failed"
        }
    } catch {
        Write-Error-Custom "Failed to generate labels"
    }

    # 4. Train model
    Write-Info "4/4: Training ensemble model (XGBoost + LightGBM + RandomForest)..."
    Write-Info "     (This takes ~10-15 minutes)"

    $command = @"
from src.training.trainer import ModelTrainer
import sys
print('Initializing ModelTrainer...')
trainer = ModelTrainer()
print('Training ensemble model...')
trainer.train_ensemble('EURUSD')
print('✓ Model training complete!')
"@

    try {
        docker compose exec -T api python -c $command
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Model trained successfully"
        } else {
            throw "Model training failed"
        }
    } catch {
        Write-Error-Custom "Failed to train model"
    }

} else {
    Write-Step "Step 7/8: Skipping Initial Data Setup (as requested)"
    Write-Info "You can run data setup later with: .\setup.ps1 -ApiKey YOUR_KEY"
}

# ====================================================================
# STEP 8: Open UI
# ====================================================================
Write-Step "Step 8/8: Opening Dashboard"

Write-Success "Setup complete!"
Write-Host ""
Write-Info "Access points:"
Write-Info "  • Dashboard:  http://localhost:8501"
Write-Info "  • API Docs:   http://localhost:8000/docs"
Write-Info "  • Health:     http://localhost:8000/health"
Write-Host ""

# Open browser
Write-Info "Opening dashboard in your browser..."
Start-Sleep -Seconds 2
Start-Process "http://localhost:8501"

Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║                  SYSTEM IS READY! 🎉                     ║
║                                                           ║
║  The dashboard should open in your browser automatically ║
║                                                           ║
║  Useful commands:                                        ║
║  • View logs:    docker compose logs -f                  ║
║  • Stop system:  docker compose down                     ║
║  • Restart:      docker compose up -d                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Green

Write-Info "To stop the system, run: docker compose down"
Write-Info "To view logs, run: docker compose logs -f"
Write-Host ""

Read-Host "Press Enter to exit setup script (system continues running)"
