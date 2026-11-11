"""Entry point for BTC ATM Short Straddle Application.

Supports running the Streamlit web UI, environment verification, or headless execution.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_streamlit_ui(port: int = 8501) -> None:
    """Launch the Streamlit web interface using the current Python environment."""
    app_path = Path(__file__).resolve().parent / "app.py"
    print(f"[*] Launching BTC ATM Short Straddle Streamlit UI on port {port}...")
    print(f"[*] Python interpreter: {sys.executable}")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    subprocess.run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="BTC ATM Short Straddle Trading System")
    parser.add_argument(
        "--ui",
        action="store_true",
        default=True,
        help="Launch the interactive Streamlit user interface (default: True)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port for Streamlit UI (default: 8501)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run environment verification diagnostics without starting the UI",
    )

    args = parser.parse_args()

    if args.verify:
        from verify_env import main as verify_main
        verify_main()
    else:
        run_streamlit_ui(port=args.port)


if __name__ == "__main__":
    main()
