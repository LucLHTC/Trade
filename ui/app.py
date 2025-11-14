"""
Streamlit dashboard for the ML Trading System.
Provides real-time monitoring, visualization, and control interface.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import get_settings
from src.common.db import get_db
from src.common.logger import get_logger
from src.visualization.charts import (
    create_live_price_chart,
    create_backtest_chart,
    create_equity_curve_chart,
)
from src.features.technical import calculate_all_features

# Initialize
settings = get_settings()
logger = get_logger(__name__)
db = get_db()

# Page configuration
st.set_page_config(
    page_title="ML Trading System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== Main Dashboard ====================

# Sidebar
with st.sidebar:
    st.title("📈 ML Trading System")
    st.write("**Real-time Trading Dashboard**")

    st.divider()

    # Navigation
    page = st.radio(
        "Navigation",
        ["📊 Overview", "🤖 Paper Trading", "📈 Performance", "⚙️ Settings"],
    )

    st.divider()

    # System status
    st.subheader("System Status")

    # Check database
    if db.health_check():
        st.success("✅ Database Connected")
    else:
        st.error("❌ Database Offline")

    # Check latest data
    try:
        result = db.execute_query(
            "SELECT MAX(timestamp) as latest FROM candles WHERE symbol = 'EURUSD'"
        )
        if result and result[0]["latest"]:
            latest_time = result[0]["latest"]
            st.info(f"📅 Latest data: {latest_time}")
        else:
            st.warning("No data available")
    except Exception as e:
        st.error(f"Error: {e}")

# ==================== Main Content ====================

if page == "📊 Overview":
    st.title("📊 Market Overview")

    # Live Price Chart
    st.header("Live EUR/USD Chart")

    try:
        # Load recent candles
        query = """
            SELECT timestamp, open, high, low, close, volume, interval
            FROM candles
            WHERE symbol = 'EURUSD'
            ORDER BY timestamp DESC
            LIMIT 200
        """
        candles_result = db.execute_query(query)

        if candles_result:
            candles_df = pd.DataFrame(candles_result)
            candles_df["timestamp"] = pd.to_datetime(candles_df["timestamp"])
            candles_df.set_index("timestamp", inplace=True)
            candles_df.sort_index(inplace=True)

            # Calculate features for indicators
            candles_df = calculate_all_features(candles_df)

            # Load predictions
            pred_query = """
                SELECT timestamp, prediction, confidence_short, confidence_long
                FROM predictions
                WHERE symbol = 'EURUSD'
                  AND timestamp >= NOW() - INTERVAL '7 days'
                ORDER BY timestamp DESC
            """
            pred_result = db.execute_query(pred_query)
            predictions_df = pd.DataFrame(pred_result) if pred_result else None

            # Create chart
            fig = create_live_price_chart(
                candles_df=candles_df,
                indicators=["ema_20", "ema_50", "rsi_14", "macd", "bb_upper", "bb_lower"],
                predictions_df=predictions_df,
                height=800,
            )

            st.plotly_chart(fig, use_container_width=True)

            # Current price info
            col1, col2, col3, col4 = st.columns(4)

            latest = candles_df.iloc[-1]

            with col1:
                st.metric("Current Price", f"{latest['close']:.5f}")
            with col2:
                change = ((latest['close'] - candles_df.iloc[-2]['close']) / candles_df.iloc[-2]['close'] * 100)
                st.metric("Change", f"{change:+.2f}%", delta=f"{change:+.2f}%")
            with col3:
                if 'rsi_14' in latest:
                    st.metric("RSI (14)", f"{latest['rsi_14']:.1f}")
            with col4:
                if 'atr_14' in latest:
                    st.metric("ATR (14)", f"{latest['atr_14']:.5f}")

        else:
            st.warning("No candle data available. Run data collection first.")

    except Exception as e:
        st.error(f"Error loading chart: {e}")
        logger.error(f"Chart error: {e}", exc_info=True)

    st.divider()

    # Quick stats
    st.header("Quick Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data Coverage")
        try:
            stats_query = """
                SELECT
                    COUNT(*) as total_candles,
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest
                FROM candles
                WHERE symbol = 'EURUSD'
            """
            stats = db.execute_query(stats_query)
            if stats:
                st.write(f"**Total Candles:** {stats[0]['total_candles']:,}")
                st.write(f"**Earliest:** {stats[0]['earliest']}")
                st.write(f"**Latest:** {stats[0]['latest']}")
        except Exception as e:
            st.error(f"Error loading stats: {e}")

    with col2:
        st.subheader("Model Predictions")
        try:
            pred_stats_query = """
                SELECT
                    COUNT(*) as total_predictions,
                    SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) as long_signals,
                    SUM(CASE WHEN prediction = -1 THEN 1 ELSE 0 END) as short_signals,
                    SUM(CASE WHEN prediction = 0 THEN 1 ELSE 0 END) as neutral_signals
                FROM predictions
                WHERE symbol = 'EURUSD'
                  AND timestamp >= NOW() - INTERVAL '7 days'
            """
            pred_stats = db.execute_query(pred_stats_query)
            if pred_stats and pred_stats[0]['total_predictions']:
                st.write(f"**Total (7d):** {pred_stats[0]['total_predictions']}")
                st.write(f"**Long Signals:** {pred_stats[0]['long_signals']}")
                st.write(f"**Short Signals:** {pred_stats[0]['short_signals']}")
                st.write(f"**Neutral:** {pred_stats[0]['neutral_signals']}")
            else:
                st.info("No predictions yet")
        except Exception as e:
            st.error(f"Error loading prediction stats: {e}")

elif page == "🤖 Paper Trading":
    st.title("🤖 Paper Trading Dashboard")

    # Portfolio Summary
    st.header("Portfolio Summary")

    try:
        # Get latest portfolio snapshot
        portfolio_query = """
            SELECT * FROM paper_portfolio
            ORDER BY timestamp DESC
            LIMIT 1
        """
        portfolio = db.execute_query(portfolio_query)

        if portfolio:
            p = portfolio[0]

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                equity = float(p['equity'])
                st.metric("Current Equity", f"${equity:,.2f}")

            with col2:
                total_pnl = float(p['total_pnl']) if p['total_pnl'] else 0
                st.metric("Total P&L", f"${total_pnl:+,.2f}", delta=f"{total_pnl:+,.2f}")

            with col3:
                win_rate = float(p['win_rate']) if p['win_rate'] else 0
                st.metric("Win Rate", f"{win_rate:.1f}%")

            with col4:
                total_trades = p['total_trades']
                st.metric("Total Trades", f"{total_trades}")

            # Additional metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Open Positions", f"{p['open_positions']}")
            with col2:
                st.metric("Winning Trades", f"{p['winning_trades']}")
            with col3:
                st.metric("Losing Trades", f"{p['losing_trades']}")
            with col4:
                pf = float(p['profit_factor']) if p['profit_factor'] else 0
                st.metric("Profit Factor", f"{pf:.2f}")

            # Drawdown
            max_dd = float(p['max_drawdown_pct']) if p['max_drawdown_pct'] else 0
            st.metric("Max Drawdown", f"{max_dd:.2f}%")

        else:
            st.info("No paper trading data yet. System will start trading on the next hourly cycle.")
            st.write("**Initial Equity:** $10,000.00")

    except Exception as e:
        st.error(f"Error loading portfolio: {e}")
        logger.error(f"Portfolio error: {e}", exc_info=True)

    st.divider()

    # Open Positions
    st.header("Open Positions")

    try:
        open_pos_query = """
            SELECT * FROM paper_positions
            WHERE status = 'open'
            ORDER BY entry_time DESC
        """
        open_positions = db.execute_query(open_pos_query)

        if open_positions:
            for pos in open_positions:
                with st.expander(f"Position #{pos['position_id']} - {'LONG' if pos['direction'] == 1 else 'SHORT'} @ {pos['entry_price']:.5f}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Symbol:** {pos['symbol']}")
                        st.write(f"**Direction:** {'LONG' if pos['direction'] == 1 else 'SHORT'}")
                        st.write(f"**Entry Time:** {pos['entry_time']}")
                        st.write(f"**Entry Price:** {pos['entry_price']:.5f}")
                        st.write(f"**Position Size:** {float(pos['position_size']):.2f} units")
                        st.write(f"**Position Value:** ${float(pos['position_value']):.2f}")

                    with col2:
                        st.write(f"**Take Profit:** {pos['take_profit']:.5f}")
                        st.write(f"**Stop Loss:** {pos['stop_loss']:.5f}")
                        st.write(f"**Risk Amount:** ${float(pos['risk_amount']):.2f}")
                        st.write(f"**Confidence:** {float(pos['confidence'])*100:.1f}%")
                        st.write(f"**Regime:** {pos['regime']}")

                        # Calculate current P&L (would need current price)
                        # st.write(f"**Unrealized P&L:** TBD")
        else:
            st.info("No open positions")

    except Exception as e:
        st.error(f"Error loading positions: {e}")

    st.divider()

    # Recent Closed Trades
    st.header("Recent Closed Trades")

    try:
        closed_query = """
            SELECT * FROM paper_positions
            WHERE status = 'closed'
            ORDER BY exit_time DESC
            LIMIT 10
        """
        closed_trades = db.execute_query(closed_query)

        if closed_trades:
            trades_df = pd.DataFrame(closed_trades)

            # Format for display
            display_df = trades_df[[
                'position_id', 'direction', 'entry_time', 'entry_price',
                'exit_time', 'exit_price', 'exit_reason', 'pnl', 'pnl_pct', 'holding_hours'
            ]].copy()

            display_df['direction'] = display_df['direction'].apply(lambda x: 'LONG' if x == 1 else 'SHORT')
            display_df['pnl'] = display_df['pnl'].apply(lambda x: f"${float(x):+,.2f}")
            display_df['pnl_pct'] = display_df['pnl_pct'].apply(lambda x: f"{float(x):+.2f}%")
            display_df['holding_hours'] = display_df['holding_hours'].apply(lambda x: f"{float(x):.1f}h")

            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No closed trades yet")

    except Exception as e:
        st.error(f"Error loading trades: {e}")

    st.divider()

    # Equity Curve
    st.header("Equity Curve")

    try:
        equity_query = """
            SELECT timestamp, equity
            FROM paper_portfolio
            ORDER BY timestamp ASC
        """
        equity_data = db.execute_query(equity_query)

        if equity_data and len(equity_data) > 1:
            equity_df = pd.DataFrame(equity_data)
            equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
            equity_df.set_index('timestamp', inplace=True)

            # Load trades for markers
            all_trades_query = """
                SELECT * FROM paper_positions
                WHERE status = 'closed'
                ORDER BY exit_time ASC
            """
            all_trades = db.execute_query(all_trades_query)
            trades_df = pd.DataFrame(all_trades) if all_trades else None

            fig = create_equity_curve_chart(equity_df, trades_df, height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for equity curve yet")

    except Exception as e:
        st.error(f"Error loading equity curve: {e}")

elif page == "📈 Performance":
    st.title("📈 Performance Analysis")

    # Backtest selector
    st.header("Backtest Visualization")

    st.info("""
    This section shows backtest results with detailed trade markers.
    To run a new backtest, use the API endpoint or run the backtest script.
    """)

    # For now, show paper trading performance
    st.subheader("Paper Trading Performance")

    try:
        # Load all closed trades
        trades_query = """
            SELECT * FROM paper_positions
            WHERE status = 'closed'
            ORDER BY entry_time ASC
        """
        trades_result = db.execute_query(trades_query)

        if trades_result and len(trades_result) > 0:
            trades_df = pd.DataFrame(trades_result)
            trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
            trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])

            # Load candles for the period
            start_date = trades_df['entry_time'].min()
            end_date = trades_df['exit_time'].max()

            candles_query = """
                SELECT timestamp, open, high, low, close, volume
                FROM candles
                WHERE symbol = 'EURUSD'
                  AND timestamp >= %s
                  AND timestamp <= %s
                ORDER BY timestamp ASC
            """
            candles_result = db.execute_query(candles_query, (start_date, end_date))

            if candles_result:
                candles_df = pd.DataFrame(candles_result)
                candles_df['timestamp'] = pd.to_datetime(candles_df['timestamp'])
                candles_df.set_index('timestamp', inplace=True)

                # Load equity curve
                equity_query = """
                    SELECT timestamp, equity
                    FROM paper_portfolio
                    ORDER BY timestamp ASC
                """
                equity_result = db.execute_query(equity_query)
                equity_df = pd.DataFrame(equity_result) if equity_result else None
                if equity_df is not None:
                    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
                    equity_df.set_index('timestamp', inplace=True)

                # Create backtest chart
                fig = create_backtest_chart(
                    candles_df=candles_df,
                    trades_df=trades_df,
                    equity_curve=equity_df,
                    height=1000,
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No candle data for trade period")
        else:
            st.info("No trades to visualize yet. System will start trading on the next hourly cycle.")

    except Exception as e:
        st.error(f"Error creating backtest chart: {e}")
        logger.error(f"Backtest chart error: {e}", exc_info=True)

    st.divider()

    # Performance Metrics
    st.header("Performance Metrics")

    try:
        # Get latest portfolio for metrics
        portfolio_query = """
            SELECT * FROM paper_portfolio
            ORDER BY timestamp DESC
            LIMIT 1
        """
        portfolio = db.execute_query(portfolio_query)

        if portfolio and portfolio[0]['total_trades'] > 0:
            p = portfolio[0]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.subheader("Returns")
                total_return = (float(p['equity']) - 10000) / 10000 * 100
                st.metric("Total Return", f"{total_return:+.2f}%")
                st.metric("Total P&L", f"${float(p['total_pnl']):+,.2f}")
                st.metric("Max Drawdown", f"{float(p['max_drawdown_pct']) if p['max_drawdown_pct'] else 0:.2f}%")

            with col2:
                st.subheader("Trade Statistics")
                st.metric("Total Trades", f"{p['total_trades']}")
                st.metric("Win Rate", f"{float(p['win_rate']) if p['win_rate'] else 0:.1f}%")

                # Calculate average win/loss
                if p['total_trades'] > 0:
                    avg_pnl = float(p['total_pnl']) / p['total_trades']
                    st.metric("Avg P&L per Trade", f"${avg_pnl:+,.2f}")

            with col3:
                st.subheader("Risk Metrics")
                st.metric("Profit Factor", f"{float(p['profit_factor']) if p['profit_factor'] else 0:.2f}")

                # Sharpe ratio would require returns series
                st.info("Sharpe Ratio: TBD")
                st.info("Sortino Ratio: TBD")
        else:
            st.info("No performance data available yet")

    except Exception as e:
        st.error(f"Error loading metrics: {e}")

elif page == "⚙️ Settings":
    st.title("⚙️ System Settings")

    st.header("Configuration")

    # Display current config
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Trading Parameters")
        st.write(f"**Initial Equity:** ${settings.initial_equity:,.2f}")
        st.write(f"**Risk per Trade:** {settings.risk_per_trade*100:.1f}%")
        st.write(f"**Max Trades per Week:** {settings.max_trades_per_week}")

    with col2:
        st.subheader("Model Parameters")
        st.write(f"**Training Window:** {settings.training_window_days} days")
        st.write(f"**Validation Window:** {settings.validation_window_days} days")
        st.write(f"**Drift PSI Threshold:** {settings.drift_psi_threshold}")

    st.divider()

    st.header("Security")

    st.subheader("Change Password")
    st.info("""
    To change your password:
    1. Edit `ui/auth_config.yaml`
    2. Generate a new hashed password using:
       ```python
       import streamlit_authenticator as stauth
       hashed = stauth.Hasher(['your_new_password']).generate()
       print(hashed[0])
       ```
    3. Replace the password hash in the config file
    4. Restart the UI container
    """)

    st.divider()

    st.header("System Information")

    st.write(f"**Database:** {settings.postgres_host}:{settings.postgres_port}")
    st.write(f"**API URL:** {settings.api_base_url}")
    st.write(f"**Timezone:** {settings.tz}")
    st.write(f"**Log Level:** {settings.log_level}")

    st.divider()

    st.header("Actions")

    st.subheader("1. Data Collection")
    col1, col2 = st.columns(2)

    with col1:
        days = st.number_input("Days of data", min_value=1, max_value=365, value=90)

    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("🔄 Collect EUR/USD Data", type="primary"):
            with st.spinner(f"Collecting {days} days of data..."):
                try:
                    # Call API endpoint or run directly
                    from src.data_collection.forex import ForexCollector
                    collector = ForexCollector()
                    collector.fetch_and_store("EURUSD", days=days)
                    st.success(f"✅ Data collection complete! Collected {days} days.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Data collection failed: {e}")
                    logger.error(f"Data collection error: {e}")

    st.divider()

    st.subheader("2. Feature Engineering")
    if st.button("⚙️ Generate Features", type="primary"):
        with st.spinner("Generating technical features..."):
            try:
                from src.features.manager import FeatureManager
                manager = FeatureManager()
                manager.generate_features_from_candles("EURUSD")
                st.success("✅ Features generated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Feature generation failed: {e}")
                logger.error(f"Feature generation error: {e}")

    st.divider()

    st.subheader("3. Model Training")
    if st.button("🤖 Train ML Model", type="primary"):
        with st.spinner("Training ensemble model (this may take 10-15 minutes)..."):
            try:
                from src.labeling.manager import LabelManager
                from src.training.trainer import ModelTrainer

                # Generate labels first
                label_mgr = LabelManager()
                label_mgr.generate_and_save("EURUSD")

                # Train model
                trainer = ModelTrainer()
                trainer.train_and_save("EURUSD")

                st.success("✅ Model training complete!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Model training failed: {e}")
                logger.error(f"Model training error: {e}")

    st.divider()

    st.subheader("4. System Maintenance")
    if st.button("🗑️ Clear Cache"):
        st.cache_data.clear()
        st.success("✅ Cache cleared!")

    st.info("""
    **Scheduler Status:** The scheduler runs automatically in the background.
    Check docker logs for `trading_scheduler` container to see activity.

    **Quick Start Guide:**
    1. Click "Collect EUR/USD Data" to fetch historical data
    2. Click "Generate Features" to calculate technical indicators
    3. Click "Train ML Model" to train the trading model
    4. View results in Overview and Paper Trading tabs
    """)

# Footer
st.divider()
st.caption(f"ML Trading System v1.0 | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
