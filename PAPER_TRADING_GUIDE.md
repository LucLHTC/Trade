# 📊 Paper Trading System - Complete Guide

## Overview

The ML Trading System now includes a **fully automated 24/7 paper trading engine** that simulates real trading with your machine learning models. This guide explains everything you need to know.

---

## 🎯 Features

### 1. **Automated Trading**
- ✅ Runs every hour automatically
- ✅ Fetches latest market data
- ✅ Generates predictions using your ML model
- ✅ Opens/closes positions based on signals
- ✅ Tracks performance metrics

### 2. **Risk Management**
- ✅ Position sizing based on Kelly Criterion
- ✅ Stop-loss and take-profit levels (ATR-based)
- ✅ Maximum holding time limits
- ✅ Daily trade limits
- ✅ Maximum open positions control

### 3. **Advanced Visualizations**
- ✅ **Live Price Chart**: TradingView-style with indicators (EMA, RSI, MACD, Bollinger Bands)
- ✅ **Signal Markers**: Visual Long/Short signals on chart
- ✅ **Backtest Chart**: Entry/exit markers with P&L visualization
- ✅ **Equity Curve**: Portfolio performance over time
- ✅ **Interactive Charts**: Hover for details, zoom, pan

### 4. **Remote Access**
- ✅ Password-protected dashboard
- ✅ Ngrok tunneling for external access
- ✅ Mobile-friendly interface
- ✅ Secure authentication

---

## 🚀 Quick Start

### Option 1: Standard Start (Local Only)

```bash
# Windows
ONE_CLICK_SETUP.bat

# Linux/Mac
chmod +x one_click_setup.sh
./one_click_setup.sh
```

**Access:** http://localhost:8501

### Option 2: With Remote Access

```bash
# Windows
START_WITH_REMOTE_ACCESS.bat

# Linux/Mac
chmod +x start_with_remote_access.sh
./start_with_remote_access.sh
```

**Access:**
- Local: http://localhost:8501
- Remote: Check ngrok output for public URL

---

## 🔐 Authentication

### First Time Login

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

⚠️ **IMPORTANT**: Change the password immediately!

### Changing Password

1. Generate a new hashed password:
   ```python
   import streamlit_authenticator as stauth
   hashed = stauth.Hasher(['your_new_password']).generate()
   print(hashed[0])
   ```

2. Edit `ui/auth_config.yaml`:
   ```yaml
   credentials:
     usernames:
       admin:
         name: Administrator
         password: YOUR_NEW_HASH_HERE
   ```

3. Restart UI container:
   ```bash
   docker compose restart ui
   ```

---

## 📱 Remote Access Setup

### Step 1: Get Ngrok Auth Token

1. Sign up at https://dashboard.ngrok.com
2. Get your auth token from dashboard
3. Set environment variable:
   ```bash
   # Windows
   set NGROK_AUTH_TOKEN=your_token_here

   # Linux/Mac
   export NGROK_AUTH_TOKEN=your_token_here
   ```

### Step 2: Start with Remote Access

Run the startup script with remote access enabled:
```bash
START_WITH_REMOTE_ACCESS.bat   # Windows
./start_with_remote_access.sh  # Linux/Mac
```

### Step 3: Access from Anywhere

- The script will output a public URL (e.g., `https://abc123.ngrok.io`)
- Open this URL on any device
- Login with your credentials
- Full dashboard access from anywhere!

---

## 🤖 How Paper Trading Works

### Hourly Cycle

Every hour at :05 past the hour, the system:

1. **Fetches Data** (1 min)
   - Latest EUR/USD candles from Alpha Vantage
   - Saves to database and parquet files

2. **Generates Features** (every 6h)
   - 50+ technical indicators
   - Event-based features
   - Regime classification

3. **Makes Predictions** (30 sec)
   - Loads ensemble model (XGBoost, LightGBM, RandomForest)
   - Generates Long/Short/Neutral signal
   - Calculates confidence scores

4. **Executes Trades** (instant)
   - Checks risk management rules
   - Opens position if signal is strong
   - Closes existing positions if TP/SL hit
   - Updates portfolio metrics

### Position Management

**Opening a Trade:**
- Requires confidence > 55%
- Checks max open positions (1)
- Checks daily trade limit (3)
- Calculates position size (1% risk per trade)
- Sets ATR-based TP (2×ATR) and SL (1×ATR)

**Closing a Trade:**
- Take Profit hit
- Stop Loss hit
- Maximum holding time (12 hours)

### Performance Tracking

Every trade completion updates:
- Total equity
- Win rate
- Profit factor
- Max drawdown
- Sharpe ratio (ongoing)

---

## 📊 Dashboard Tabs

### 1. Overview Tab
- **Live Price Chart**: Real-time EUR/USD with indicators
- **Current Metrics**: Price, RSI, ATR, change %
- **Data Coverage**: Total candles, date range
- **Prediction Stats**: Recent signals count

### 2. Paper Trading Tab
- **Portfolio Summary**: Equity, P&L, win rate, profit factor
- **Open Positions**: Real-time position details
- **Recent Trades**: Last 10 closed trades
- **Equity Curve**: Portfolio growth over time

### 3. Performance Tab
- **Backtest Chart**: All trades with entry/exit markers
- **Trade Analysis**: Color-coded wins (green) and losses (red)
- **Performance Metrics**: Returns, risk, trade statistics

### 4. Settings Tab
- **Configuration**: Trading and model parameters
- **Security**: Password management
- **System Info**: Database, API, scheduler status

---

## 🗄️ Database Structure

### paper_positions
Stores all paper trading positions (open and closed).

**Key Fields:**
- `position_id`: Unique identifier
- `symbol`: Trading pair (EURUSD)
- `direction`: 1 (LONG) or -1 (SHORT)
- `entry_time`, `entry_price`: When/where entered
- `stop_loss`, `take_profit`: Exit levels
- `status`: 'open' or 'closed'
- `exit_time`, `exit_price`, `exit_reason`: Exit details
- `pnl`, `pnl_pct`: Profit/loss
- `holding_hours`: Trade duration

### paper_portfolio
Snapshots of portfolio state over time.

**Key Fields:**
- `timestamp`: When snapshot taken
- `equity`: Current total equity
- `total_trades`: Cumulative trades
- `win_rate`: Percentage of winning trades
- `profit_factor`: (Total Wins / Total Losses)
- `max_drawdown_pct`: Maximum equity decline

### predictions
Model predictions log for visualization.

**Key Fields:**
- `timestamp`: When prediction made
- `prediction`: -1 (SHORT), 0 (NEUTRAL), 1 (LONG)
- `confidence_short`, `confidence_long`: Model confidence
- `regime`: Market regime classification
- `signal_strength`: 'strong', 'moderate', 'weak'

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Trading Parameters
INITIAL_EQUITY=10000.0
RISK_PER_TRADE=0.01          # 1% risk per trade
MAX_TRADES_PER_WEEK=3

# API Keys
ALPHAVANTAGE_API_KEY=your_key_here
NGROK_AUTH_TOKEN=your_token_here  # Optional

# Database
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=trading
POSTGRES_USER=trader
POSTGRES_PASSWORD=traderpwd

# Scheduler
SCHEDULER_ENABLED=true
HOURLY_JOBS_ENABLED=true
DAILY_JOBS_ENABLED=true
```

### Adjusting Risk

**Conservative (0.5% per trade):**
```bash
RISK_PER_TRADE=0.005
MAX_TRADES_PER_WEEK=2
```

**Moderate (1% per trade):**
```bash
RISK_PER_TRADE=0.01
MAX_TRADES_PER_WEEK=3
```

**Aggressive (2% per trade):**
```bash
RISK_PER_TRADE=0.02
MAX_TRADES_PER_WEEK=5
```

---

## 🔍 Monitoring

### Check Scheduler Logs

```bash
docker logs -f trading_scheduler
```

**What to look for:**
- `✅ Paper trading cycle complete` - Successful execution
- `🔵 PAPER ENTRY` - Position opened
- `🟢 PAPER EXIT` or `🔴 PAPER EXIT` - Position closed

### Check Database

```bash
# Connect to database
docker exec -it trading_db psql -U trader -d trading

# View open positions
SELECT * FROM paper_positions WHERE status = 'open';

# View recent trades
SELECT position_id, direction, entry_price, exit_price, pnl, exit_reason
FROM paper_positions
WHERE status = 'closed'
ORDER BY exit_time DESC
LIMIT 10;

# View portfolio history
SELECT timestamp, equity, total_trades, win_rate
FROM paper_portfolio
ORDER BY timestamp DESC
LIMIT 10;
```

### API Health Check

```bash
curl http://localhost:8000/health
```

---

## 📈 Performance Expectations

### Realistic Targets (with good model)

- **Win Rate**: 55-65%
- **Profit Factor**: 1.5-2.5
- **Max Drawdown**: < 15%
- **Monthly Return**: 3-8%

### What to Watch

⚠️ **Red Flags:**
- Win rate < 45%
- Profit factor < 1.0
- Max drawdown > 20%
- Long losing streaks (> 5 trades)

✅ **Good Signs:**
- Consistent positive returns
- Profit factor > 1.5
- Smooth equity curve
- Quick recovery from drawdowns

---

## 🐛 Troubleshooting

### No Trades Being Executed

**Check:**
1. Scheduler is running: `docker ps` should show `trading_scheduler`
2. Scheduler logs: `docker logs trading_scheduler`
3. Model is trained: Check `models/current/` directory
4. API is running: `curl http://localhost:8000/health`

**Solution:**
```bash
# Restart scheduler
docker compose restart scheduler

# Check if model exists
docker exec trading_scheduler ls -la /app/models/current/

# If no model, train one
docker exec trading_api python -c "from src.training.trainer import ModelTrainer; t = ModelTrainer(); t.train_and_save('EURUSD')"
```

### Dashboard Not Loading

**Check:**
1. UI container running: `docker ps | grep trading_ui`
2. UI logs: `docker logs trading_ui`
3. Port 8501 not occupied: `netstat -ano | findstr 8501` (Windows)

**Solution:**
```bash
# Restart UI
docker compose restart ui

# If port conflict, change in docker-compose.yml
ports:
  - "8502:8501"  # Use different port
```

### Remote Access Not Working

**Check:**
1. Python installed: `python --version`
2. pyngrok installed: `pip list | grep pyngrok`
3. Ngrok tunnel running: Check ngrok window

**Solution:**
```bash
# Install pyngrok
pip install pyngrok

# Set auth token (for unlimited tunnels)
set NGROK_AUTH_TOKEN=your_token

# Run remote access script
python scripts/setup_remote_access.py
```

---

## 🎓 Best Practices

### 1. Start Small
- Begin with default $10,000 equity
- Use 1% risk per trade
- Monitor for at least 2 weeks before increasing risk

### 2. Monitor Regularly
- Check dashboard daily
- Review trades weekly
- Analyze performance monthly

### 3. Iterate on Model
- Monitor drift detection alerts
- Retrain when performance degrades
- A/B test new models with shadow deployment

### 4. Keep Logs
- Export trade history monthly
- Document parameter changes
- Track what works and what doesn't

### 5. Stay Disciplined
- Don't manually intervene (defeats the purpose)
- Let the system run its course
- Make changes based on data, not emotions

---

## 📞 Support

**Issues:** https://github.com/LucLHTC/Trade/issues

**Documentation:** Check other .md files in repository

**Logs:** All logs in `logs/` directory

---

## 🎯 Next Steps

1. ✅ Start the system with remote access
2. ✅ Change default password
3. ✅ Monitor first few trades
4. ✅ Adjust risk parameters if needed
5. ✅ Let it run for at least 1 month
6. ✅ Analyze performance and iterate

**Happy Trading! 🚀📈**
