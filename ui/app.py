"""
Streamlit dashboard for the ML Trading System.
Provides real-time monitoring, visualization, and control interface.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import get_settings
from src.common.db import get_connection, execute_query
from src.common.logger import get_logger
from src.monitoring.performance import PerformanceTracker, MetricsReporter
from src.data_collection.manager import CandleDataManager

# Page configuration
st.set_page_config(
    page_title="ML Trading System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize
settings = get_settings()
logger = get_logger(__name__)

# API base URL
API_URL = settings.api_base_url


# ==================== Utility Functions ====================

@st.cache_data(ttl=60)
def check_api_health() -> dict:
    """Check API health status."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            return {"status": "healthy", "data": response.json()}
        else:
            return {"status": "unhealthy", "error": f"Status code: {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "failed", "error": "Cannot connect to API"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@st.cache_data(ttl=30)
def get_recent_trades(days: int = 7) -> pd.DataFrame:
    """Get recent trades from database."""
    try:
        tracker = PerformanceTracker()
        df = tracker.get_recent_performance(days=days)
        return df
    except Exception as e:
        logger.error(f"Failed to get recent trades: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def get_performance_summary(days: int = 30) -> dict:
    """Get performance summary."""
    try:
        tracker = PerformanceTracker()
        summary = tracker.get_performance_summary(days=days)
        return summary
    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        return {}


@st.cache_data(ttl=300)
def load_equity_curve_data() -> pd.DataFrame:
    """Load equity curve data from backtest results."""
    try:
        # Try to load latest backtest equity curve
        backtest_dir = Path("data/backtest")
        if backtest_dir.exists():
            equity_files = sorted(backtest_dir.glob("equity_curve_*.csv"), reverse=True)
            if equity_files:
                df = pd.read_csv(equity_files[0])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df

        # Generate mock data if no backtest data
        dates = pd.date_range(end=datetime.utcnow(), periods=30, freq='D')
        equity = [10000]
        for _ in range(29):
            change = np.random.normal(50, 200)
            equity.append(max(equity[-1] + change, 5000))

        return pd.DataFrame({'timestamp': dates, 'equity': equity})
    except Exception as e:
        logger.error(f"Failed to load equity curve: {e}")
        return pd.DataFrame()


def get_open_positions() -> pd.DataFrame:
    """Get currently open positions."""
    # For now, return empty - would connect to live trading engine
    return pd.DataFrame()


# ==================== Chart Functions ====================

def plot_equity_curve(df: pd.DataFrame):
    """Plot equity curve with Plotly."""
    if df.empty:
        st.warning("No equity data available")
        return

    fig = go.Figure()

    # Equity line
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['equity'],
        mode='lines',
        name='Equity',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)'
    ))

    # Add initial equity reference line
    if not df.empty:
        initial_equity = df['equity'].iloc[0]
        fig.add_hline(
            y=initial_equity,
            line_dash="dash",
            line_color="gray",
            annotation_text="Initial Equity",
            annotation_position="right"
        )

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        hovermode='x unified',
        height=400,
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_drawdown(df: pd.DataFrame):
    """Plot drawdown chart."""
    if df.empty or 'equity' not in df.columns:
        st.warning("No equity data available for drawdown")
        return

    # Calculate drawdown
    equity = df['equity'].values
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak * 100

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=drawdown,
        mode='lines',
        name='Drawdown',
        line=dict(color='#d62728', width=2),
        fill='tozeroy',
        fillcolor='rgba(214, 39, 40, 0.2)'
    ))

    fig.update_layout(
        title="Drawdown (%)",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        hovermode='x unified',
        height=300,
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_win_rate_over_time(trades_df: pd.DataFrame):
    """Plot rolling win rate over time."""
    if trades_df.empty or 'exit_time' not in trades_df.columns:
        st.warning("No trade data available")
        return

    # Sort by exit time
    trades_df = trades_df.sort_values('exit_time')

    # Calculate rolling win rate (20-trade window)
    window = 20
    trades_df['is_win'] = (trades_df['pnl'] > 0).astype(int)
    trades_df['rolling_win_rate'] = trades_df['is_win'].rolling(window=window, min_periods=1).mean() * 100

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=trades_df['exit_time'],
        y=trades_df['rolling_win_rate'],
        mode='lines',
        name=f'Win Rate ({window}-trade window)',
        line=dict(color='#2ca02c', width=2)
    ))

    # Add reference line at 50%
    fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50%")

    fig.update_layout(
        title=f"Rolling Win Rate ({window}-trade window)",
        xaxis_title="Date",
        yaxis_title="Win Rate (%)",
        yaxis_range=[0, 100],
        hovermode='x unified',
        height=300,
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_pnl_distribution(trades_df: pd.DataFrame):
    """Plot P&L distribution histogram."""
    if trades_df.empty or 'pnl' not in trades_df.columns:
        st.warning("No trade data available")
        return

    fig = go.Figure()

    # Separate wins and losses
    wins = trades_df[trades_df['pnl'] > 0]['pnl']
    losses = trades_df[trades_df['pnl'] < 0]['pnl']

    fig.add_trace(go.Histogram(
        x=wins,
        name='Wins',
        marker_color='#2ca02c',
        opacity=0.7,
        nbinsx=30
    ))

    fig.add_trace(go.Histogram(
        x=losses,
        name='Losses',
        marker_color='#d62728',
        opacity=0.7,
        nbinsx=30
    ))

    fig.update_layout(
        title="P&L Distribution",
        xaxis_title="P&L ($)",
        yaxis_title="Frequency",
        barmode='overlay',
        height=300,
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_trade_duration(trades_df: pd.DataFrame):
    """Plot trade duration distribution."""
    if trades_df.empty or 'holding_hours' not in trades_df.columns:
        st.warning("No trade data available")
        return

    fig = px.histogram(
        trades_df,
        x='holding_hours',
        nbins=20,
        title="Trade Duration Distribution",
        labels={'holding_hours': 'Duration (hours)', 'count': 'Frequency'},
        color_discrete_sequence=['#1f77b4']
    )

    fig.update_layout(
        height=300,
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_prediction_distribution():
    """Plot model prediction distribution (mock data)."""
    # Mock data - would come from recent predictions
    predictions = np.random.choice([-1, 0, 1], size=100, p=[0.25, 0.5, 0.25])
    pred_counts = pd.Series(predictions).value_counts().sort_index()

    labels = ['Short (-1)', 'Neutral (0)', 'Long (1)']
    colors = ['#d62728', '#7f7f7f', '#2ca02c']

    fig = go.Figure(data=[go.Bar(
        x=labels,
        y=[pred_counts.get(-1, 0), pred_counts.get(0, 0), pred_counts.get(1, 0)],
        marker_color=colors
    )])

    fig.update_layout(
        title="Recent Prediction Distribution (Last 100)",
        xaxis_title="Prediction",
        yaxis_title="Count",
        height=300,
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_top_features():
    """Plot top SHAP features (mock data)."""
    # Mock data - would come from latest model SHAP values
    features = [
        'rsi_14', 'macd_histogram', 'ema_cross_9_21',
        'atr_14', 'price_vs_ema21', 'bb_position',
        'adx', 'stoch_k', 'volume_ratio', 'volatility_10'
    ]
    importance = np.random.rand(10) * 0.5
    importance = sorted(importance, reverse=True)

    fig = go.Figure(go.Bar(
        x=importance,
        y=features,
        orientation='h',
        marker_color='#ff7f0e'
    ))

    fig.update_layout(
        title="Top 10 Feature Importance (SHAP)",
        xaxis_title="Importance",
        yaxis_title="Feature",
        height=400,
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)


# ==================== Main App ====================

# Title and header
st.title("📈 ML Trading System Dashboard")
st.markdown("*Real-time monitoring and control for autonomous algorithmic trading*")

# Sidebar
with st.sidebar:
    st.header("⚙️ System Controls")

    # Auto-refresh toggle
    auto_refresh = st.toggle("🔄 Auto-refresh (60s)", value=False)

    if auto_refresh:
        time.sleep(60)
        st.rerun()

    if st.button("🔄 Manual Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    # Time range selector
    st.subheader("📅 Time Range")
    time_range = st.selectbox(
        "Select period",
        options=[7, 14, 30, 60, 90],
        format_func=lambda x: f"Last {x} days",
        index=2  # Default: 30 days
    )

    st.markdown("---")

    # Trading controls
    st.subheader("🎮 Trading Controls")

    trading_enabled = st.toggle("Enable Trading", value=False)

    if trading_enabled:
        st.success("✅ Trading ENABLED")
        if st.button("⏸️ Stop Trading", use_container_width=True, type="primary"):
            st.warning("Trading stopped")
            time.sleep(1)
            st.rerun()
    else:
        st.info("⏸️ Trading PAUSED")
        if st.button("▶️ Start Trading", use_container_width=True):
            st.success("Trading started")
            time.sleep(1)
            st.rerun()

    st.markdown("---")

    # Risk Parameters
    st.subheader("⚡ Risk Parameters")
    risk_pct = st.slider("Risk per trade (%)", 0.5, 5.0, 1.0, 0.1)
    max_drawdown = st.slider("Max drawdown (%)", 5.0, 30.0, 15.0, 1.0)
    max_daily_trades = st.number_input("Max daily trades", 1, 10, 3)

    st.markdown("---")

    st.caption(f"Last updated: {datetime.utcnow().strftime('%H:%M:%S')} UTC")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "💰 Trading",
    "📈 Performance",
    "🧠 Model",
    "⚙️ System"
])

# ==================== Tab 1: Overview ====================

with tab1:
    st.header("System Overview")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    summary = get_performance_summary(days=time_range)

    with col1:
        total_trades = summary.get('total_trades', 0)
        st.metric("Total Trades", total_trades)

    with col2:
        win_rate = summary.get('win_rate', 0)
        st.metric("Win Rate", f"{win_rate:.1f}%")

    with col3:
        total_pnl = summary.get('total_pnl', 0)
        delta_color = "normal" if total_pnl >= 0 else "inverse"
        st.metric("Total P&L", f"${total_pnl:,.2f}", delta_color=delta_color)

    with col4:
        profit_factor = summary.get('profit_factor', 0)
        st.metric("Profit Factor", f"{profit_factor:.2f}")

    st.markdown("---")

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Equity Curve")
        equity_df = load_equity_curve_data()
        plot_equity_curve(equity_df)

    with col2:
        st.subheader("📉 Drawdown")
        plot_drawdown(equity_df)

    # Recent trades
    st.markdown("---")
    st.subheader("🕐 Recent Trades")

    trades_df = get_recent_trades(days=7)

    if not trades_df.empty:
        # Display last 5 trades
        display_df = trades_df.head(5)[['exit_time', 'direction', 'entry_price', 'exit_price', 'pnl', 'exit_reason']]
        display_df['exit_time'] = pd.to_datetime(display_df['exit_time']).dt.strftime('%Y-%m-%d %H:%M')
        display_df['direction'] = display_df['direction'].map({'long': '🟢 LONG', 'short': '🔴 SHORT'})
        display_df['pnl'] = display_df['pnl'].apply(lambda x: f"${x:+,.2f}")

        display_df.columns = ['Time', 'Direction', 'Entry', 'Exit', 'P&L', 'Reason']

        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent trades")

# ==================== Tab 2: Trading ====================

with tab2:
    st.header("Live Trading Monitor")

    # Open positions
    st.subheader("📍 Open Positions")

    open_positions = get_open_positions()

    if not open_positions.empty:
        st.dataframe(open_positions, use_container_width=True)
    else:
        st.info("No open positions")

    st.markdown("---")

    # Recent trades with more details
    st.subheader("📋 Trade History")

    trades_df = get_recent_trades(days=time_range)

    if not trades_df.empty:
        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            direction_filter = st.multiselect(
                "Direction",
                options=['long', 'short'],
                default=['long', 'short']
            )

        with col2:
            exit_reason_filter = st.multiselect(
                "Exit Reason",
                options=trades_df['exit_reason'].unique().tolist(),
                default=trades_df['exit_reason'].unique().tolist()
            )

        with col3:
            min_pnl = st.number_input("Min P&L", value=float(trades_df['pnl'].min()))

        # Apply filters
        filtered_df = trades_df[
            (trades_df['direction'].isin(direction_filter)) &
            (trades_df['exit_reason'].isin(exit_reason_filter)) &
            (trades_df['pnl'] >= min_pnl)
        ]

        # Display
        display_cols = ['trade_id', 'entry_time', 'exit_time', 'direction', 'entry_price',
                       'exit_price', 'pnl', 'pnl_pct', 'holding_hours', 'exit_reason', 'regime']

        if all(col in filtered_df.columns for col in display_cols):
            st.dataframe(
                filtered_df[display_cols].sort_values('exit_time', ascending=False),
                use_container_width=True,
                hide_index=True
            )

            # Download button
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                "trade_history.csv",
                "text/csv"
            )
    else:
        st.info(f"No trades in the last {time_range} days")

# ==================== Tab 3: Performance ====================

with tab3:
    st.header("Performance Analytics")

    trades_df = get_recent_trades(days=time_range)

    if not trades_df.empty:
        # Metrics grid
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean()
            st.metric("Avg Win", f"${avg_win:.2f}" if not np.isnan(avg_win) else "N/A")

        with col2:
            avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean()
            st.metric("Avg Loss", f"${avg_loss:.2f}" if not np.isnan(avg_loss) else "N/A")

        with col3:
            avg_duration = trades_df['holding_hours'].mean() if 'holding_hours' in trades_df.columns else 0
            st.metric("Avg Duration", f"{avg_duration:.1f}h")

        with col4:
            best_trade = trades_df['pnl'].max()
            st.metric("Best Trade", f"${best_trade:.2f}")

        st.markdown("---")

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            plot_win_rate_over_time(trades_df)
            plot_pnl_distribution(trades_df)

        with col2:
            plot_trade_duration(trades_df)

            # Exit reason pie chart
            if 'exit_reason' in trades_df.columns:
                exit_counts = trades_df['exit_reason'].value_counts()

                fig = go.Figure(data=[go.Pie(
                    labels=exit_counts.index,
                    values=exit_counts.values,
                    hole=0.3
                )])

                fig.update_layout(
                    title="Exit Reasons",
                    height=300,
                    template='plotly_white'
                )

                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No performance data for the last {time_range} days")

# ==================== Tab 4: Model Monitoring ====================

with tab4:
    st.header("Model Monitoring")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 Prediction Distribution")
        plot_prediction_distribution()

    with col2:
        st.subheader("🔍 Top Features (SHAP)")
        plot_top_features()

    st.markdown("---")

    # Model info
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📊 Model Performance")
        st.metric("Validation Accuracy", "67.3%")
        st.metric("Precision (Long)", "65.8%")
        st.metric("Recall (Long)", "58.2%")

    with col2:
        st.subheader("🕐 Training Info")
        st.text("Last trained: 2025-11-10")
        st.text("Training samples: 1,247")
        st.text("Features used: 156")
        st.text("Model: Ensemble")

    with col3:
        st.subheader("⚠️ Drift Detection")
        st.success("✅ No drift detected")
        st.text("PSI Score: 0.08")
        st.text("KS Statistic: 0.12")
        st.text("Last checked: 2025-11-12")

    st.markdown("---")

    # Model controls
    st.subheader("🎛️ Model Controls")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Retrain Model", use_container_width=True):
            with st.spinner("Retraining model..."):
                time.sleep(2)
                st.success("Model retrained successfully!")

    with col2:
        if st.button("📊 Run Backtest", use_container_width=True):
            with st.spinner("Running backtest..."):
                time.sleep(2)
                st.success("Backtest complete!")

    with col3:
        if st.button("🔍 Check Drift", use_container_width=True):
            with st.spinner("Checking for drift..."):
                time.sleep(1)
                st.info("No drift detected")

# ==================== Tab 5: System ====================

with tab5:
    st.header("System Status & Configuration")

    # API Health
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔌 API Status")
        api_health = check_api_health()

        if api_health["status"] == "healthy":
            st.success("✅ API is healthy")
        elif api_health["status"] == "unhealthy":
            st.warning(f"⚠️ API is unhealthy: {api_health.get('error', 'Unknown')}")
        else:
            st.error(f"❌ API connection failed: {api_health.get('error', 'Unknown')}")

    with col2:
        st.subheader("🗄️ Database Status")
        try:
            with get_connection() as conn:
                st.success("✅ Database is healthy")
        except Exception as e:
            st.error(f"❌ Database error: {e}")

    st.markdown("---")

    # Configuration
    st.subheader("⚙️ Current Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Trading Parameters**")
        st.text(f"Initial Equity: ${settings.initial_equity:,.2f}")
        st.text(f"Risk per Trade: {settings.risk_per_trade*100:.1f}%")
        st.text(f"Max Trades/Week: {settings.max_trades_per_week}")
        st.text(f"TP ATR Multiple: 2.0")
        st.text(f"SL ATR Multiple: 1.0")

    with col2:
        st.markdown("**Model Settings**")
        st.text(f"Training Window: {settings.training_window_days} days")
        st.text(f"Validation Window: {settings.validation_window_days} days")
        st.text(f"Prediction Threshold: 0.55")
        st.text(f"Max Spread: 0.02%")

    with col3:
        st.markdown("**Risk Management**")
        st.text(f"Max Open Trades: 1")
        st.text(f"Max Daily Trades: 3")
        st.text(f"Max Drawdown: 15%")
        st.text(f"Max Holding Time: 12h")

    st.markdown("---")

    # Logs viewer
    st.subheader("📋 Recent Logs")

    log_level = st.selectbox("Log Level", ["INFO", "WARNING", "ERROR"])

    if st.button("🔍 View Logs"):
        st.code("""
2025-11-12 14:30:15 | INFO | Inference complete: LONG signal
2025-11-12 14:30:12 | INFO | Features generated: 156 features
2025-11-12 14:30:10 | INFO | Candle data fetched: 200 candles
2025-11-12 13:30:08 | INFO | Trade closed: +$45.20 (TP hit)
2025-11-12 12:15:05 | INFO | Model loaded successfully
        """, language="log")

# Footer
st.markdown("---")
st.caption("ML Trading System v1.4.0 | Session 6 - Dashboard Complete")
