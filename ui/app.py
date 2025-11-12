"""
Streamlit dashboard for the ML Trading System.
Provides real-time monitoring, visualization, and control interface.
"""

import streamlit as st
import requests
import sys
from pathlib import Path
from datetime import datetime
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import get_settings
from src.common.db import get_db
from src.common.logger import get_logger

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


def check_db_health() -> dict:
    """Check database health status."""
    try:
        db = get_db()
        if db.health_check():
            return {"status": "healthy"}
        else:
            return {"status": "unhealthy", "error": "Health check failed"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def get_api_status() -> dict:
    """Get detailed API status."""
    try:
        response = requests.get(f"{API_URL}/api/status", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        logger.error(f"Failed to get API status: {e}")
        return None


# Title and header
st.title("📈 ML Trading System")
st.markdown("*Autonomous algorithmic trading with machine learning*")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ System Controls")

    if st.button("🔄 Refresh Status", use_container_width=True):
        st.rerun()

    st.markdown("---")

    st.subheader("Configuration")
    st.text(f"Environment: {settings.tz}")
    st.text(f"Initial Equity: ${settings.initial_equity:,.2f}")
    st.text(f"Risk/Trade: {settings.risk_per_trade*100:.1f}%")
    st.text(f"Max Trades/Week: {settings.max_trades_per_week}")

    st.markdown("---")
    st.caption(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

# Main content area
tab1, tab2, tab3 = st.tabs(["🏠 System Health", "📊 Dashboard", "⚙️ Settings"])

# Tab 1: System Health
with tab1:
    st.header("System Health Status")

    col1, col2 = st.columns(2)

    # API Health
    with col1:
        st.subheader("🔌 API Status")
        api_health = check_api_health()

        if api_health["status"] == "healthy":
            st.success("✅ API is healthy")
            if "data" in api_health:
                with st.expander("View Details"):
                    st.json(api_health["data"])
        elif api_health["status"] == "unhealthy":
            st.warning(f"⚠️ API is unhealthy: {api_health.get('error', 'Unknown')}")
        else:
            st.error(f"❌ API connection failed: {api_health.get('error', 'Unknown')}")

    # Database Health
    with col2:
        st.subheader("🗄️ Database Status")
        db_health = check_db_health()

        if db_health["status"] == "healthy":
            st.success("✅ Database is healthy")
        elif db_health["status"] == "unhealthy":
            st.warning(f"⚠️ Database is unhealthy: {db_health.get('error', 'Unknown')}")
        else:
            st.error(f"❌ Database connection failed: {db_health.get('error', 'Unknown')}")

    st.markdown("---")

    # Detailed Status
    st.subheader("📋 Detailed System Status")

    status_data = get_api_status()
    if status_data:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**API Information**")
            st.text(f"Version: {status_data['api']['version']}")
            st.text(f"Status: {status_data['api']['status']}")

            st.markdown("**Database Information**")
            st.text(f"Host: {status_data['database']['host']}")
            st.text(f"Port: {status_data['database']['port']}")
            st.text(f"Database: {status_data['database']['database']}")
            st.text(f"Status: {status_data['database']['status']}")

        with col2:
            st.markdown("**Configuration**")
            config = status_data['configuration']
            st.text(f"Initial Equity: ${config['initial_equity']:,.2f}")
            st.text(f"Risk/Trade: {config['risk_per_trade']*100:.1f}%")
            st.text(f"Max Trades/Week: {config['max_trades_per_week']}")
            st.text(f"Training Window: {config['training_window_days']} days")
            st.text(f"Drift PSI Threshold: {config['drift_psi_threshold']}")
    else:
        st.error("❌ Unable to retrieve system status")

    # Connection Test
    st.markdown("---")
    st.subheader("🔗 Connection Test")

    if st.button("Test API Connection"):
        with st.spinner("Testing connection..."):
            try:
                response = requests.get(f"{API_URL}/api/ping", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ Connection successful! Response: {data['message']}")
                else:
                    st.error(f"❌ Connection failed with status code: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Connection error: {e}")

# Tab 2: Dashboard (Placeholder for future sessions)
with tab2:
    st.header("Trading Dashboard")
    st.info("📊 Trading dashboard will be implemented in Session 6")

    st.markdown("**Upcoming Features:**")
    st.markdown("- Live equity curve")
    st.markdown("- Active trades monitor")
    st.markdown("- Performance metrics (Sharpe, Win Rate, Profit Factor)")
    st.markdown("- SHAP interpretation plots")
    st.markdown("- Macro event calendar")

# Tab 3: Settings (Placeholder for future sessions)
with tab3:
    st.header("System Settings")
    st.info("⚙️ Settings panel will be implemented in Session 6")

    st.markdown("**Upcoming Features:**")
    st.markdown("- Adjust risk parameters")
    st.markdown("- Configure thresholds")
    st.markdown("- Model selection (live vs shadow)")
    st.markdown("- Trigger manual retraining")
    st.markdown("- View and download logs")

# Footer
st.markdown("---")
st.caption("ML Trading System v1.0.0 | Session 1 - Foundation")
