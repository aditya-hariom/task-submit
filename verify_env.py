"""Environment and dependency verification script for BTC Short Straddle.

Run this script at any time to verify that Python, NautilusTrader, Bybit adapter,
and supporting packages are correctly installed in your uv environment.
"""

import sys
from importlib.metadata import version


def verify_environment() -> bool:
    """Check the runtime environment and installed packages."""
    print("=" * 60)
    print("  BTC ATM Short Straddle - Environment Verification")
    print("=" * 60)

    # 1. Check Python version
    py_ver = sys.version.split()[0]
    in_venv = sys.prefix != sys.base_prefix
    print(f"[x] Python Version:       {py_ver}")
    print(f"[x] Virtual Environment:  {'Active (' + sys.prefix + ')' if in_venv else 'NOT active (using global Python)'}")

    all_passed = True

    # 2. Check NautilusTrader installation
    try:
        import nautilus_trader

        nt_version = nautilus_trader.__version__
        print(f"[x] NautilusTrader:       v{nt_version} (Installed & Importable)")
    except ImportError as e:
        print(f"[!] NautilusTrader:       FAILED to import ({e})")
        all_passed = False

    # 3. Check Bybit adapter availability inside NautilusTrader
    try:
        from nautilus_trader.adapters.bybit.config import (
            BybitDataClientConfig,
            BybitExecClientConfig,
        )
        from nautilus_trader.adapters.bybit.factories import (
            BybitLiveDataClientFactory,
            BybitLiveExecClientFactory,
        )

        print("[x] Bybit Adapter:        Available (BybitDataClient & BybitExecClient ready)")
    except ImportError as e:
        print(f"[!] Bybit Adapter:        FAILED to load ({e})")
        all_passed = False

    # 4. Check python-dotenv
    try:
        import dotenv

        dotenv_ver = version("python-dotenv")
        print(f"[x] python-dotenv:        v{dotenv_ver} (Installed & Importable)")
    except ImportError as e:
        print(f"[!] python-dotenv:        FAILED to import ({e})")
        all_passed = False

    # 5. Check pytest
    try:
        import pytest

        pytest_ver = version("pytest")
        print(f"[x] pytest:               v{pytest_ver} (Installed & Importable)")
    except ImportError as e:
        print(f"[!] pytest:               FAILED to import ({e})")
        all_passed = False

    # 6. Check Streamlit & Plotly
    try:
        import streamlit
        import plotly

        st_ver = version("streamlit")
        pl_ver = version("plotly")
        print(f"[x] Streamlit UI:         v{st_ver} (Installed & Importable)")
        print(f"[x] Plotly Engine:        v{pl_ver} (Installed & Importable)")
    except ImportError as e:
        print(f"[!] Streamlit/Plotly:     FAILED to import ({e})")
        all_passed = False

    print("=" * 60)
    if all_passed:
        print(" SUCCESS: uv environment & dependencies verified successfully!")
    else:
        print(" ERROR: One or more components failed verification.")
    print("=" * 60)

    return all_passed


def main() -> None:
    """Entry point for environment verification."""
    success = verify_environment()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

