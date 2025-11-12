#!/usr/bin/env python3
"""
ML Trading System - Automated Setup Script
Cross-platform setup automation for Windows, macOS, and Linux
"""

import os
import sys
import time
import subprocess
import platform
import webbrowser
import argparse
from pathlib import Path
from typing import Optional, Tuple

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.CYAN}ℹ {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")

def print_step(msg: str):
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}══ {msg} ══{Colors.RESET}\n")

def print_banner():
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       ML TRADING SYSTEM - AUTOMATED SETUP                ║
║       EUR/USD Algorithmic Trading with ML                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(f"{Colors.CYAN}{banner}{Colors.RESET}")
    time.sleep(1)

def run_command(cmd: list, capture_output: bool = False, timeout: int = None) -> Tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.returncode == 0, result.stdout
        else:
            result = subprocess.run(cmd, timeout=timeout, check=False)
            return result.returncode == 0, ""
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def check_prerequisites() -> bool:
    """Check if Docker and Docker Compose are installed and running."""
    print_step("Step 1/8: Checking Prerequisites")

    # Check Docker
    print_info("Checking Docker installation...")
    success, output = run_command(["docker", "--version"], capture_output=True)
    if success:
        print_success(f"Docker is installed: {output.strip()}")
    else:
        print_error("Docker is not installed!")
        print_info("Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/")
        return False

    # Check Docker Compose
    print_info("Checking Docker Compose...")
    success, output = run_command(["docker", "compose", "version"], capture_output=True)
    if success:
        print_success(f"Docker Compose is available: {output.strip()}")
    else:
        print_error("Docker Compose is not available!")
        print_info("Please update Docker Desktop to the latest version.")
        return False

    # Check if Docker daemon is running
    print_info("Checking if Docker daemon is running...")
    success, _ = run_command(["docker", "ps"], capture_output=True, timeout=5)
    if success:
        print_success("Docker daemon is running")
    else:
        print_error("Docker Desktop is not running!")
        print_info("Please start Docker Desktop and wait for it to fully initialize.")
        return False

    return True

def get_api_key(provided_key: Optional[str] = None) -> str:
    """Get API key from user, environment, or .env file."""
    print_step("Step 2/8: Configuration")

    env_path = Path(".env")

    # Check existing .env file
    if env_path.exists():
        print_info("Found existing .env file")
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith("ALPHAVANTAGE_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    if key and key != "YOUR_API_KEY_HERE" and len(key) > 5:
                        print_success("Using API key from .env file")
                        return key

    # Use provided key
    if provided_key and provided_key != "YOUR_API_KEY_HERE":
        print_success("Using provided API key")
        return provided_key

    # Ask user
    print_info("Alpha Vantage API Key is required for data collection.")
    print_info("Get your free API key here: https://www.alphavantage.co/support/#api-key")
    print()
    api_key = input("Enter your Alpha Vantage API key: ").strip()

    if not api_key:
        print_error("API key is required!")
        sys.exit(1)

    return api_key

def create_env_file(api_key: str) -> bool:
    """Create .env configuration file."""
    print_step("Step 3/8: Creating Configuration Files")

    env_example = Path(".env.example")
    env_path = Path(".env")

    if env_example.exists():
        print_info("Creating .env from template...")
        with open(env_example, 'r') as f:
            content = f.read()
        content = content.replace("ALPHAVANTAGE_API_KEY=YOUR_API_KEY_HERE", f"ALPHAVANTAGE_API_KEY={api_key}")
        with open(env_path, 'w') as f:
            f.write(content)
        print_success(".env file created")
    else:
        print_warning(".env.example not found, creating basic .env file...")

        basic_env = f"""# Database Configuration
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
ALPHAVANTAGE_API_KEY={api_key}

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
"""
        with open(env_path, 'w') as f:
            f.write(basic_env)
        print_success(".env file created")

    return True

def create_directories() -> bool:
    """Create required directory structure."""
    print_step("Step 4/8: Creating Directory Structure")

    directories = [
        "data/forex",
        "data/features",
        "data/labels",
        "models/current",
        "models/shadow",
        "models/archived",
        "logs/errors"
    ]

    for dir_path in directories:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print_success(f"Created: {dir_path}")
        else:
            print_info(f"Already exists: {dir_path}")

    return True

def start_containers() -> bool:
    """Start Docker containers."""
    print_step("Step 5/8: Starting Docker Containers")

    print_info("This will take 5-10 minutes on first run (downloading images, building containers)...")
    print_info("Starting containers...")

    # Stop existing containers
    run_command(["docker", "compose", "down"], capture_output=True)

    # Start containers
    success, _ = run_command(["docker", "compose", "up", "--build", "-d"])
    if success:
        print_success("Containers started successfully")
        return True
    else:
        print_error("Failed to start containers!")
        print_info("Check the error messages above.")
        return False

def wait_for_services() -> bool:
    """Wait for all services to be ready."""
    print_step("Step 6/8: Waiting for Services to Initialize")

    # Wait for database
    print_info("Waiting for database to be ready...")
    for attempt in range(30):
        time.sleep(2)
        success, output = run_command(
            ["docker", "compose", "exec", "-T", "db", "pg_isready", "-U", "trader"],
            capture_output=True,
            timeout=5
        )
        if success:
            print_success("Database is ready")
            break
        print(".", end="", flush=True)
    else:
        print_error("\nDatabase failed to start in time")
        return False

    # Wait for API
    print_info("Waiting for API to be ready...")
    for attempt in range(30):
        time.sleep(2)
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:8000/health", timeout=2)
            print_success("API is ready")
            break
        except:
            print(".", end="", flush=True)
    else:
        print_warning("\nAPI took longer than expected, but may still be starting...")

    # Wait for UI
    print_info("Waiting for UI to be ready...")
    for attempt in range(20):
        time.sleep(2)
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:8501", timeout=2)
            print_success("UI is ready")
            break
        except:
            print(".", end="", flush=True)
    else:
        print_warning("\nUI took longer than expected, but may still be starting...")

    return True

def run_initial_setup(data_days: int) -> bool:
    """Run initial data collection and model training."""
    print_step("Step 7/8: Initial Data Setup and Model Training")

    print_info(f"This process takes ~20-30 minutes. Please be patient...")
    print()

    # 1. Collect historical data
    print_info(f"1/4: Collecting {data_days} days of historical EUR/USD data...")
    print_info("     (This takes ~5 minutes due to API rate limits)")

    cmd = f"""
from src.data_collection.forex import ForexCollector
print('Initializing ForexCollector...')
collector = ForexCollector()
print('Fetching EUR/USD data...')
collector.fetch_and_store('EURUSD', days={data_days})
print('✓ Data collection complete!')
"""

    success, _ = run_command(["docker", "compose", "exec", "-T", "api", "python", "-c", cmd])
    if success:
        print_success("Historical data collected")
    else:
        print_error("Failed to collect historical data")
        return False

    # 2. Generate features
    print_info("2/4: Generating features (technical indicators, macro events)...")
    print_info("     (This takes ~2-3 minutes)")

    cmd = """
from src.features.manager import FeatureManager
print('Initializing FeatureManager...')
manager = FeatureManager()
print('Generating features...')
manager.generate_features('EURUSD')
print('✓ Feature generation complete!')
"""

    success, _ = run_command(["docker", "compose", "exec", "-T", "api", "python", "-c", cmd])
    if success:
        print_success("Features generated")
    else:
        print_error("Failed to generate features")
        return False

    # 3. Generate labels
    print_info("3/4: Generating labels (trade signals)...")
    print_info("     (This takes ~1 minute)")

    cmd = """
from src.labeling.manager import LabelManager
print('Initializing LabelManager...')
manager = LabelManager()
print('Generating labels...')
manager.generate_labels('EURUSD')
print('✓ Label generation complete!')
"""

    success, _ = run_command(["docker", "compose", "exec", "-T", "api", "python", "-c", cmd])
    if success:
        print_success("Labels generated")
    else:
        print_error("Failed to generate labels")
        return False

    # 4. Train model
    print_info("4/4: Training ensemble model (XGBoost + LightGBM + RandomForest)...")
    print_info("     (This takes ~10-15 minutes)")

    cmd = """
from src.training.trainer import ModelTrainer
print('Initializing ModelTrainer...')
trainer = ModelTrainer()
print('Training ensemble model...')
trainer.train_ensemble('EURUSD')
print('✓ Model training complete!')
"""

    success, _ = run_command(["docker", "compose", "exec", "-T", "api", "python", "-c", cmd])
    if success:
        print_success("Model trained successfully")
    else:
        print_error("Failed to train model")
        return False

    return True

def open_dashboard():
    """Open the dashboard in the default browser."""
    print_step("Step 8/8: Opening Dashboard")

    print_success("Setup complete!")
    print()
    print_info("Access points:")
    print_info("  • Dashboard:  http://localhost:8501")
    print_info("  • API Docs:   http://localhost:8000/docs")
    print_info("  • Health:     http://localhost:8000/health")
    print()

    print_info("Opening dashboard in your browser...")
    time.sleep(2)
    webbrowser.open("http://localhost:8501")

def print_completion():
    """Print completion message."""
    completion_msg = """
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
    """
    print(f"{Colors.GREEN}{completion_msg}{Colors.RESET}")

    print_info("To stop the system, run: docker compose down")
    print_info("To view logs, run: docker compose logs -f")
    print()

def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="ML Trading System - Automated Setup")
    parser.add_argument("--api-key", type=str, help="Alpha Vantage API key")
    parser.add_argument("--skip-training", action="store_true", help="Skip initial data collection and training")
    parser.add_argument("--quick", action="store_true", help="Quick mode (30 days of data instead of 90)")
    parser.add_argument("--data-days", type=int, default=90, help="Number of days of historical data (default: 90)")

    args = parser.parse_args()

    print_banner()

    # Step 1: Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Step 2: Get API key
    api_key = get_api_key(args.api_key)

    # Step 3: Create .env file
    if not create_env_file(api_key):
        sys.exit(1)

    # Step 4: Create directories
    if not create_directories():
        sys.exit(1)

    # Step 5: Start containers
    if not start_containers():
        sys.exit(1)

    # Step 6: Wait for services
    if not wait_for_services():
        print_warning("Some services may not be fully ready, but you can continue")

    # Step 7: Initial setup
    if not args.skip_training:
        data_days = 30 if args.quick else args.data_days
        if not run_initial_setup(data_days):
            print_warning("Initial setup had some errors, but the system is running")
            print_info("You can retry setup steps manually - see WINDOWS_SETUP.md")
    else:
        print_step("Step 7/8: Skipping Initial Data Setup (as requested)")
        print_info("You can run data setup later with: python setup.py --api-key YOUR_KEY")

    # Step 8: Open dashboard
    open_dashboard()
    print_completion()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
