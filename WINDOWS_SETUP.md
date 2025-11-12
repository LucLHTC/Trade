# 🪟 Windows Setup Guide

Complete step-by-step guide to start the ML Trading System on Windows.

## 📋 Prerequisites

### 1. Install Docker Desktop for Windows

**Download and Install:**
1. Go to https://www.docker.com/products/docker-desktop/
2. Download Docker Desktop for Windows
3. Run the installer (requires admin rights)
4. Restart your computer when prompted
5. Start Docker Desktop from the Start menu
6. Wait for Docker to fully start (whale icon in system tray should be steady)

**Verify Installation:**
Open PowerShell or Command Prompt and run:
```powershell
docker --version
docker compose version
```

You should see version numbers (e.g., Docker version 24.0.x).

### 2. Get Alpha Vantage API Key

**Free API Key (Required for data collection):**
1. Go to https://www.alphavantage.co/support/#api-key
2. Fill in your name and email
3. Click "GET FREE API KEY"
4. Copy the API key (looks like: `ABC123XYZ456`)
5. Keep this for step 4 below

**Note:** Free tier allows 25 API calls/day, 5 calls/minute - sufficient for this system.

## 🚀 Setup Instructions

### Step 1: Navigate to Your Project Folder

Open PowerShell and navigate to your extracted folder:
```powershell
cd "C:\Users\PC\OneDrive\Bureaublad\trading algo v3"
```

Or open the folder in File Explorer, type `powershell` in the address bar, and press Enter.

### Step 2: Verify Files

Check that you have these important files:
```powershell
dir
```

You should see:
- `docker-compose.yml`
- `.env.example`
- `init.sql`
- `requirements.txt`
- `src/` folder
- `ui/` folder
- etc.

### Step 3: Create Configuration File

Create your `.env` file from the example:
```powershell
# Copy the example file
Copy-Item .env.example .env
```

### Step 4: Configure API Key

Edit the `.env` file with your API key:

**Option A: Using Notepad**
```powershell
notepad .env
```

**Option B: Using VS Code (if installed)**
```powershell
code .env
```

**What to change:**
1. Find this line:
   ```
   ALPHAVANTAGE_API_KEY=YOUR_API_KEY_HERE
   ```

2. Replace `YOUR_API_KEY_HERE` with your actual API key:
   ```
   ALPHAVANTAGE_API_KEY=ABC123XYZ456
   ```

3. Optionally, adjust trading parameters:
   ```
   INITIAL_EQUITY=10000.00        # Starting capital
   RISK_PER_TRADE=0.01            # Risk 1% per trade
   MAX_TRADES_PER_WEEK=3          # Maximum 3 trades/week
   ```

4. Save the file (Ctrl+S) and close the editor

### Step 5: Create Required Folders

Create folders for data storage (if they don't exist):
```powershell
# Create data directories
New-Item -ItemType Directory -Force -Path "data\forex"
New-Item -ItemType Directory -Force -Path "data\features"
New-Item -ItemType Directory -Force -Path "data\labels"

# Create model directories
New-Item -ItemType Directory -Force -Path "models\current"
New-Item -ItemType Directory -Force -Path "models\shadow"
New-Item -ItemType Directory -Force -Path "models\archived"

# Create logs directory
New-Item -ItemType Directory -Force -Path "logs\errors"
```

### Step 6: Start the System

**Make sure Docker Desktop is running!** (Check system tray for whale icon)

Start all services:
```powershell
docker compose up --build
```

**What this does:**
- Builds 3 Docker images (API, UI, Scheduler)
- Pulls PostgreSQL image
- Creates database with schema
- Starts all 4 services

**First-time startup takes 5-10 minutes** to:
- Download Docker images (~500MB)
- Install Python dependencies
- Initialize database

**You'll see lots of logs scrolling by - this is normal!**

Look for these success messages:
```
trading_db        | database system is ready to accept connections
trading_api       | Uvicorn running on http://0.0.0.0:8000
trading_ui        | You can now view your Streamlit app in your browser
trading_scheduler | Scheduler started successfully
```

### Step 7: Access the UI

Once all services are running, open your web browser:

**Streamlit Dashboard:**
```
http://localhost:8501
```

**FastAPI Documentation:**
```
http://localhost:8000/docs
```

**Health Check:**
```
http://localhost:8000/health
```

## 🎮 Using the System

### First Time Setup

The system needs initial data before trading:

1. **Collect Historical Data** (in a new PowerShell window):
   ```powershell
   docker compose exec api python -c "
   from src.data_collection.forex import ForexCollector
   collector = ForexCollector()
   collector.fetch_and_store('EURUSD', days=90)
   "
   ```
   This takes ~5 minutes (fetches 90 days of hourly candles).

2. **Generate Features**:
   ```powershell
   docker compose exec api python -c "
   from src.features.manager import FeatureManager
   manager = FeatureManager()
   manager.generate_features('EURUSD')
   "
   ```

3. **Generate Labels**:
   ```powershell
   docker compose exec api python -c "
   from src.labeling.manager import LabelManager
   manager = LabelManager()
   manager.generate_labels('EURUSD')
   "
   ```

4. **Train Initial Model**:
   ```powershell
   docker compose exec api python -c "
   from src.training.trainer import ModelTrainer
   trainer = ModelTrainer()
   trainer.train_ensemble('EURUSD')
   "
   ```
   This takes ~10 minutes to train XGBoost, LightGBM, and RandomForest models.

### Dashboard Overview

Once set up, the Streamlit UI has 5 tabs:

1. **📊 Overview**: System status, recent trades, equity curve
2. **💰 Trading**: Open positions, trade history with filters
3. **📈 Performance**: Detailed metrics, charts (win rate, drawdown, P&L)
4. **🤖 Model**: Model predictions, SHAP feature importance
5. **⚙️ System**: Controls, health checks, configuration

### Running the Scheduler

The scheduler automatically runs jobs every hour/day:
- Data collection: Every hour
- Feature generation: Every hour
- Model inference: Every hour
- Drift detection: Every 2 days
- Auto-retraining: Every Monday

Check scheduler logs:
```powershell
docker compose logs -f scheduler
```

## 🛑 Stopping the System

**Graceful Shutdown:**
In the PowerShell window where `docker compose up` is running:
- Press `Ctrl+C` once
- Wait for services to stop (takes ~10 seconds)

**Force Stop (if needed):**
```powershell
docker compose down
```

**Stop and Remove All Data:**
```powershell
docker compose down -v
```
⚠️ This deletes the database! Only use if you want a fresh start.

## 🔄 Restarting the System

Next time you want to start:
```powershell
cd "C:\Users\PC\OneDrive\Bureaublad\trading algo v3"
docker compose up
```

No need for `--build` unless you've changed code.

## 📊 Monitoring & Logs

### View Logs in Real-Time

**All services:**
```powershell
docker compose logs -f
```

**Specific service:**
```powershell
docker compose logs -f api        # API logs
docker compose logs -f ui         # UI logs
docker compose logs -f scheduler  # Scheduler logs
docker compose logs -f db         # Database logs
```

Press `Ctrl+C` to stop following logs.

### Check Service Status

```powershell
docker compose ps
```

All services should show "Up" and "healthy".

### Access Database

If you want to query the database directly:
```powershell
docker compose exec db psql -U trader -d trading
```

Then run SQL:
```sql
-- View recent trades
SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10;

-- View drift logs
SELECT * FROM drift_log ORDER BY detected_at DESC LIMIT 5;

-- Exit
\q
```

## 🐛 Troubleshooting

### Problem: "Docker daemon is not running"

**Solution:**
1. Open Docker Desktop from Start menu
2. Wait for it to fully start (30-60 seconds)
3. Look for whale icon in system tray
4. Try `docker compose up` again

### Problem: Port Already in Use

**Error:** `Bind for 0.0.0.0:8501 failed: port is already allocated`

**Solution:**
```powershell
# Find what's using the port
netstat -ano | findstr :8501

# Kill the process (replace PID with number from above)
taskkill /PID <PID> /F
```

Or change the port in `docker-compose.yml`:
```yaml
ports:
  - "8502:8501"  # Use 8502 instead
```

### Problem: API Key Not Working

**Error:** `Invalid API key` or `API rate limit reached`

**Solutions:**
1. Check `.env` file - no quotes around API key
2. Verify key at https://www.alphavantage.co/support/#api-key
3. Free tier: Only 25 calls/day - wait 24 hours if exceeded
4. Check key is on one line with no spaces:
   ```
   ALPHAVANTAGE_API_KEY=ABC123XYZ456
   ```

### Problem: Database Connection Failed

**Error:** `could not connect to database`

**Solution:**
```powershell
# Check if database is healthy
docker compose ps

# If unhealthy, restart database
docker compose restart db

# Wait 10 seconds, then restart API
docker compose restart api
```

### Problem: Out of Memory / Slow Performance

**Solution:**
1. Open Docker Desktop
2. Go to Settings → Resources
3. Increase Memory to at least 4GB
4. Click "Apply & Restart"

### Problem: UI Shows "Connecting..."

**Solution:**
1. Check API is running: http://localhost:8000/health
2. Restart UI:
   ```powershell
   docker compose restart ui
   ```
3. Clear browser cache (Ctrl+Shift+Delete)
4. Refresh page (Ctrl+F5)

### Problem: "No such file or directory"

**Error when creating folders or files**

**Solution:**
Make sure you're in the correct directory:
```powershell
cd "C:\Users\PC\OneDrive\Bureaublad\trading algo v3"
pwd  # Should show your project path
```

### Problem: Model Not Found

**Error:** `FileNotFoundError: models/current/model.pkl`

**Solution:**
Train the initial model (see "First Time Setup" above) or check that the `models/current/` folder exists.

## 💡 Tips

1. **Keep Docker Desktop Running**: It must be running for the system to work
2. **Check Logs First**: Most issues show clear error messages in logs
3. **Use PowerShell (Not CMD)**: PowerShell has better command support
4. **API Rate Limits**: Free Alpha Vantage tier allows 25 calls/day
5. **Initial Training**: Takes ~10 minutes, be patient
6. **Data Storage**: System uses ~500MB for 90 days of data + models
7. **Auto-Refresh**: UI refreshes every 60 seconds automatically
8. **Background Mode**: Use `docker compose up -d` to run in background

## 🔒 Security Notes

1. **Never commit `.env` file** to git (contains API keys)
2. **Change default passwords** in production
3. **API key is free tier** - no financial risk
4. **System trades with simulation** - no real money by default
5. **Database is local only** - not exposed to internet

## 📚 Next Steps

Once the system is running:

1. **Explore the UI** - Check all 5 tabs
2. **Review Trades** - See historical performance
3. **Monitor Drift** - Check model stability
4. **Adjust Risk** - Change risk parameters in `.env`
5. **Read Documentation** - See README.md for details

## 🆘 Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review logs: `docker compose logs -f`
3. Check README.md for technical details
4. Ensure all prerequisites are met
5. Verify Docker Desktop is running and healthy

## 📝 Quick Command Reference

```powershell
# Start system
docker compose up

# Start in background
docker compose up -d

# Stop system
docker compose down

# View logs
docker compose logs -f

# Restart service
docker compose restart api

# Check status
docker compose ps

# Access database
docker compose exec db psql -U trader -d trading

# Run Python command
docker compose exec api python -c "print('Hello')"

# Rebuild after code changes
docker compose up --build
```

---

**System Ready!** 🎉

You should now be able to access the trading dashboard at http://localhost:8501
