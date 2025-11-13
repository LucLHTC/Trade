"""
Setup script for remote access to Streamlit UI via ngrok.
Enables secure external access to the dashboard from anywhere.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyngrok import ngrok, conf
from src.common.logger import get_logger

logger = get_logger(__name__)


def setup_ngrok(auth_token: str = None, port: int = 8501):
    """
    Setup ngrok tunnel for Streamlit UI.

    Args:
        auth_token: Ngrok auth token (get from https://dashboard.ngrok.com)
        port: Local port where Streamlit is running

    Returns:
        Public URL for accessing the dashboard
    """
    if auth_token:
        # Set auth token
        ngrok.set_auth_token(auth_token)
        logger.info("Ngrok auth token configured")
    else:
        logger.warning("No auth token provided - tunnel will be limited to 2 hours")

    try:
        # Open tunnel
        public_url = ngrok.connect(port, "http")
        logger.info(f"✅ Ngrok tunnel established!")
        logger.info(f"🌐 Public URL: {public_url}")

        return public_url

    except Exception as e:
        logger.error(f"Failed to create ngrok tunnel: {e}")
        raise


def main():
    """Main execution."""
    print("="*70)
    print(" "*15 + "ML Trading System - Remote Access Setup")
    print("="*70)
    print()

    # Check for auth token
    auth_token = os.getenv("NGROK_AUTH_TOKEN")

    if not auth_token:
        print("⚠️  No NGROK_AUTH_TOKEN found in environment!")
        print()
        print("To get unlimited tunnels:")
        print("1. Sign up at https://dashboard.ngrok.com")
        print("2. Get your auth token")
        print("3. Set environment variable: NGROK_AUTH_TOKEN=your_token")
        print()
        print("For now, using free tier (2-hour limit)")
        print()

        response = input("Continue without auth token? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    # Setup tunnel
    print("Setting up ngrok tunnel...")
    print()

    try:
        public_url = setup_ngrok(auth_token=auth_token, port=8501)

        print()
        print("="*70)
        print(" " * 20 + "✅ TUNNEL ACTIVE!")
        print("="*70)
        print()
        print(f"🌐 Public URL: {public_url}")
        print()
        print("You can now access your dashboard from anywhere using the URL above!")
        print()
        print("📱 Mobile access: Just open the URL on your phone")
        print("💻 Remote access: Share the URL (with login credentials) for team access")
        print()
        print("⚠️  SECURITY NOTE:")
        print("   - The UI is password-protected via streamlit-authenticator")
        print("   - Default credentials: admin / admin123")
        print("   - CHANGE THE PASSWORD in ui/auth_config.yaml!")
        print()
        print("="*70)
        print()
        print("Press Ctrl+C to stop the tunnel...")

        # Keep tunnel alive
        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nStopping tunnel...")
        ngrok.kill()
        print("Tunnel closed.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return


if __name__ == "__main__":
    main()
