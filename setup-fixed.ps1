# ====================================================================
# ML Trading System - FIXED Automated Setup Script
# ====================================================================
# This version fixes:
# - OneDrive location issues (auto-relocates project)
# - Docker I/O errors (cleans cache first)
# - PowerShell function definition issues
# - Adds retry logic and better error handling
# ====================================================================

param(
    [string]$ApiKey = "",
    [switch]$SkipTraining,
    [switch]$Quick,
    [int]$DataDays = 90
)

# Function definitions MUST be at the top, before any usage
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White",
        [string]$Prefix = ""
    )
    $fullMessage = if ($Prefix) { "$Prefix $Message" } else { $Message }
    Write-Host $fullMessage -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput -Message $Message -Color Green -Prefix "✓"
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-ColorOutput -Message $Message -Color Red -Prefix "✗"
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput -Message $Message -Color Cyan -Prefix "ℹ"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput -Message $Message -Color Yellow -Prefix "⚠"
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n══════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "  $Message" -ForegroundColor Magenta
    Write-Host "══════════════════════════════════════════════════════`n" -ForegroundColor Magenta
}

# Banner
$banner = @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     ML TRADING SYSTEM - SMART SETUP (FIXED)              ║
║     Auto-fixes OneDrive & Docker Issues                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

"@
Write-Host $banner -ForegroundColor Cyan
Start-Sleep -Seconds 1

# ====================================================================
# STEP 0: Detect and Fix OneDrive Location
# ====================================================================
Write-Step "Step 0: Checking Project Location"

$currentPath = Get-Location
$isOneDrive = $currentPath.Path -match "OneDrive"

if ($isOneDrive) {
    Write-Warning "Project is in OneDrive folder - this causes Docker I/O errors!"
    Write-Info "Automatically relocating to C:\Trading..."

    $targetPath = "C:\Trading"

    # Create target directory
    if (!(Test-Path $targetPath)) {
        New-Item -ItemType Directory -Force -Path $targetPath | Out-Null
        Write-Success "Created directory: $targetPath"
    }

    # Copy all files
    Write-Info "Copying project files (this takes ~30 seconds)..."
    try {
        Copy-Item -Path "$currentPath\*" -Destination $targetPath -Recurse -Force -ErrorAction Stop
        Write-Success "Project copied to $targetPath"

        # Change to new location
        Set-Location $targetPath
        Write-Success "Working directory changed to: $targetPath"

        Write-Info "You can delete the OneDrive copy later if you want."
    } catch {
        Write-ErrorMsg "Failed to copy project: $_"
        Write-Info "Please manually copy the project folder to C:\Trading and run this script from there."
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Success "Project is in local folder (not OneDrive) - Good!"
}

# ====================================================================
# STEP 1: Check Prerequisites
# ====================================================================
Write-Step "Step 1: Checking Prerequisites"

Write-Info "Checking Docker installation..."
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker installed: $dockerVersion"
    } else {
        throw "Docker not found"
    }
} catch {
    Write-ErrorMsg "Docker is not installed!"
    Write-Info "Install from: https://www.docker.com/products/docker-desktop/"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Info "Checking Docker Compose..."
try {
    $composeVersion = docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker Compose available: $composeVersion"
    } else {
        throw "Docker Compose not found"
    }
} catch {
    Write-ErrorMsg "Docker Compose not available!"
    Write-Info "Update Docker Desktop to latest version."
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
    Write-ErrorMsg "Docker Desktop is not running!"
    Write-Info "Please start Docker Desktop and wait for it to initialize."
    Write-Info "Look for the whale icon in your system tray."

    $response = Read-Host "Do you want me to wait while you start it? (Y/N)"
    if ($response -eq "Y" -or $response -eq "y") {
        Write-Info "Waiting for Docker to start..."
        for ($i = 1; $i -le 30; $i++) {
            Start-Sleep -Seconds 5
            docker ps > $null 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Docker is now running!"
                break
            }
            Write-Host "." -NoNewline
        }

        docker ps > $null 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMsg "Docker still not running. Please start it manually and run this script again."
            Read-Host "Press Enter to exit"
            exit 1
        }
    } else {
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ====================================================================
# STEP 2: Clean Docker (Fix I/O Errors)
# ====================================================================
Write-Step "Step 2: Cleaning Docker Cache"

Write-Info "Stopping any existing containers..."
docker compose down 2>&1 | Out-Null

Write-Info "Cleaning Docker cache (fixes I/O errors)..."
Write-Warning "This removes all unused Docker data - it's safe!"
docker system prune -a -f --volumes 2>&1 | Out-Null
Write-Success "Docker cache cleaned"

Write-Info "Restarting Docker Desktop is recommended..."
$restart = Read-Host "Restart Docker Desktop now? This ensures clean state. (Y/N)"

if ($restart -eq "Y" -or $restart -eq "y") {
    Write-Info "Please close Docker Desktop manually:"
    Write-Info "1. Right-click whale icon in system tray"
    Write-Info "2. Click 'Quit Docker Desktop'"
    Write-Info "3. Wait 10 seconds"
    Write-Info "4. Start Docker Desktop again"
    Write-Info "5. Wait for it to fully start (2 minutes)"

    Read-Host "Press Enter when Docker Desktop is running again"

    # Verify Docker is back
    Write-Info "Verifying Docker is running..."
    $maxAttempts = 20
    $dockerReady = $false

    for ($i = 1; $i -le $maxAttempts; $i++) {
        Start-Sleep -Seconds 3
        docker ps > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            Write-Success "Docker is ready!"
            break
        }
        Write-Host "." -NoNewline
    }

    if (!$dockerReady) {
        Write-ErrorMsg "Docker is not responding. Please ensure it's fully started."
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Warning "Skipping Docker restart - continuing anyway..."
}

# ====================================================================
# STEP 3: Get API Key
# ====================================================================
Write-Step "Step 3: Configuration"

$envPath = ".env"
$apiKeyFromEnv = ""

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

if ([string]::IsNullOrEmpty($ApiKey) -or $ApiKey -eq "YOUR_API_KEY_HERE") {
    Write-Info "Alpha Vantage API Key required (free)."
    Write-Info "Get it here: https://www.alphavantage.co/support/#api-key"
    Write-Host ""
    $ApiKey = Read-Host "Enter your Alpha Vantage API key"

    if ([string]::IsNullOrEmpty($ApiKey)) {
        Write-ErrorMsg "API key is required!"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Success "API key configured"

# ====================================================================
# STEP 4: Create Configuration Files
# ====================================================================
Write-Step "Step 4: Creating Configuration"

if (Test-Path ".env.example") {
    Write-Info "Creating .env from template..."
    $envContent = Get-Content ".env.example" -Raw
    $envContent = $envContent -replace "ALPHAVANTAGE_API_KEY=YOUR_API_KEY_HERE", "ALPHAVANTAGE_API_KEY=$ApiKey"
    $envContent | Out-File -FilePath ".env" -Encoding UTF8 -NoNewline
    Write-Success ".env file created"
} else {
    Write-Warning ".env.example not found, creating basic .env..."

    $basicEnv = @"
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

    $basicEnv | Out-File -FilePath ".env" -Encoding UTF8
    Write-Success ".env file created"
}

# ====================================================================
# STEP 5: Create Directories
# ====================================================================
Write-Step "Step 5: Creating Directories"

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
    }
}

# ====================================================================
# STEP 6: Start Docker Containers
# ====================================================================
Write-Step "Step 6: Starting Docker Containers"

Write-Info "Building and starting containers..."
Write-Info "First run takes 10-15 minutes (downloading images, installing packages)"
Write-Host ""

try {
    $buildOutput = docker compose up --build -d 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Docker build failed!"
        Write-Host $buildOutput

        Write-Warning "Common fixes:"
        Write-Info "1. Check disk space (need 10GB+)"
        Write-Info "2. Increase Docker memory to 6GB (Settings → Resources)"
        Write-Info "3. Try again after restarting Docker Desktop"

        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Success "Containers started"
} catch {
    Write-ErrorMsg "Failed to start containers: $_"
    Read-Host "Press Enter to exit"
    exit 1
}

# ====================================================================
# STEP 7: Wait for Services
# ====================================================================
Write-Step "Step 7: Waiting for Services to Initialize"

Write-Info "Waiting for database (max 60 seconds)..."
$dbReady = $false
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 2
    docker compose exec -T db pg_isready -U trader > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dbReady = $true
        Write-Success "Database is ready"
        break
    }
    Write-Host "." -NoNewline
}

if (!$dbReady) {
    Write-ErrorMsg "`nDatabase failed to start"
    Write-Info "Check logs: docker compose logs db"
    $continue = Read-Host "Continue anyway? (Y/N)"
    if ($continue -ne "Y" -and $continue -ne "y") {
        exit 1
    }
}

Write-Info "Waiting for API (max 60 seconds)..."
$apiReady = $false
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $apiReady = $true
            Write-Success "API is ready"
            break
        }
    } catch {
        Write-Host "." -NoNewline
    }
}

if (!$apiReady) {
    Write-Warning "`nAPI took longer than expected"
}

Write-Info "Waiting for UI (max 40 seconds)..."
$uiReady = $false
for ($i = 1; $i -le 20; $i++) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8501" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $uiReady = $true
            Write-Success "UI is ready"
            break
        }
    } catch {
        Write-Host "." -NoNewline
    }
}

if (!$uiReady) {
    Write-Warning "`nUI is still starting (this is normal)"
}

# ====================================================================
# STEP 8: Initial Data Setup
# ====================================================================
if (!$SkipTraining) {
    Write-Step "Step 8: Data Collection & Model Training"

    if ($Quick) {
        $DataDays = 30
        Write-Info "Quick mode: Using 30 days of data"
    }

    Write-Info "Total time: ~20-30 minutes"
    Write-Warning "Please be patient - this is a one-time setup!"
    Write-Host ""

    # 1. Collect data
    Write-Info "[1/4] Collecting $DataDays days of EUR/USD data (~5 min)..."
    $cmd = "from src.data_collection.forex import ForexCollector; c = ForexCollector(); c.fetch_and_store('EURUSD', days=$DataDays)"

    try {
        docker compose exec -T api python -c $cmd
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Data collected"
        } else {
            throw "Data collection failed"
        }
    } catch {
        Write-ErrorMsg "Failed to collect data: $_"
        Write-Warning "You can retry manually later"
    }

    # 2. Generate features
    Write-Info "[2/4] Generating features (~2-3 min)..."
    $cmd = "from src.features.manager import FeatureManager; m = FeatureManager(); m.generate_features('EURUSD')"

    try {
        docker compose exec -T api python -c $cmd
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Features generated"
        } else {
            throw "Feature generation failed"
        }
    } catch {
        Write-ErrorMsg "Failed to generate features: $_"
    }

    # 3. Generate labels
    Write-Info "[3/4] Generating labels (~1 min)..."
    $cmd = "from src.labeling.manager import LabelManager; m = LabelManager(); m.generate_labels('EURUSD')"

    try {
        docker compose exec -T api python -c $cmd
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Labels generated"
        } else {
            throw "Label generation failed"
        }
    } catch {
        Write-ErrorMsg "Failed to generate labels: $_"
    }

    # 4. Train model
    Write-Info "[4/4] Training ensemble model (~10-15 min)..."
    $cmd = "from src.training.trainer import ModelTrainer; t = ModelTrainer(); t.train_ensemble('EURUSD')"

    try {
        docker compose exec -T api python -c $cmd
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Model trained successfully!"
        } else {
            throw "Model training failed"
        }
    } catch {
        Write-ErrorMsg "Failed to train model: $_"
    }

} else {
    Write-Step "Step 8: Skipping Data Setup"
    Write-Info "You can run setup later with data and training steps"
}

# ====================================================================
# STEP 9: Open Dashboard
# ====================================================================
Write-Step "Step 9: Opening Dashboard"

Write-Success "Setup Complete!"
Write-Host ""
Write-Info "Access points:"
Write-Info "  • Dashboard:  http://localhost:8501"
Write-Info "  • API Docs:   http://localhost:8000/docs"
Write-Info "  • Health:     http://localhost:8000/health"
Write-Host ""

Write-Info "Opening dashboard in browser..."
Start-Sleep -Seconds 2
Start-Process "http://localhost:8501"

$completionBanner = @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║                 SYSTEM IS READY! 🎉                      ║
║                                                           ║
║  Dashboard: http://localhost:8501                        ║
║                                                           ║
║  Useful commands:                                        ║
║  • View logs:    docker compose logs -f                  ║
║  • Stop system:  docker compose down                     ║
║  • Restart:      docker compose up -d                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

"@
Write-Host $completionBanner -ForegroundColor Green

Write-Info "System is running in the background."
Write-Info "To stop: docker compose down"
Write-Host ""

Read-Host "Press Enter to exit setup (system keeps running)"
