# BTC ATM Short Straddle

An algorithmic options trading project building a **Bitcoin (BTC) At-The-Money (ATM) Short Straddle** strategy using the **NautilusTrader** framework and the **Bybit** exchange adapter, managed with **uv**.

---

## 1. Project Introduction

This project is an automated cryptocurrency options trading application. It is designed to implement an **ATM Short Straddle** on Bitcoin (BTC). 

A Short Straddle is an options strategy where a trader simultaneously sells (writes) both a **Call option** and a **Put option** for the same underlying asset (BTC), with the same strike price (closest to the current market price, or "At-The-Money"), and the same expiration date. The strategy aims to profit from time decay (theta) when the underlying price remains relatively stable within a range.

---

## 2. Internship Assignment Objective

The primary objective of this internship assignment is to:
1. Build a clean, professional, and reliable options trading system using **NautilusTrader**.
2. Integrate with the **Bybit Testnet** for live market data and paper/testnet trade execution.
3. Successfully configure, manage risk for, and execute a BTC ATM Short Straddle strategy.

> **Current Scope:** This repository is currently in **Phase 1 (Foundation & Setup)**. No live exchange connections, real funds, or trading execution logic have been started yet.

---

## 3. Technology Stack

- **Package & Project Manager:** [uv](https://github.com/astral-sh/uv) (v0.10.2)
- **Programming Language:** Python 3.12 (CPython 64-bit, pinned in `.python-version`)
- **Project Configuration:** `pyproject.toml` (PEP 517 / PEP 621) with locked dependencies in `uv.lock`
- **User Interface & Visualization:** Streamlit (v1.67.0) & Plotly (v7.1.0)
  - Interactive web dashboard for option chain visualization, multi-horizon payoff profiling, order execution, position monitoring, and backtesting.
- **Trading Framework:** [NautilusTrader](https://nautilustrader.io/) (v1.231.0)
  - Ultra-high-performance, event-driven algorithmic trading engine.
  - Native Bybit adapter (`nautilus_trader.adapters.bybit`) written in Rust for fast WebSocket feeds and REST execution.
- **Market Data & HTTP:** `requests` (v2.34.2)
- **Configuration Management:** `python-dotenv` (v1.2.4)
- **Testing Suite:** `pytest` (v9.2.0)
- **Version Control:** Git

---

## 4. Project Folder Structure

```text
btc-short-straddle/
│
├── config/                 # System configuration, API settings, and trading node parameters
│   ├── __init__.py
│   └── settings.py
│
├── strategies/             # Strategy logic, Black-Scholes Greeks, payoff modeling, backtester
│   ├── __init__.py
│   ├── short_straddle.py
│   └── backtester.py
│
├── data/                   # Bybit market client, option chain parser, ATM finder
│   ├── __init__.py
│   └── bybit_client.py
│
├── execution/              # Paper trading engine, order lifecycle, Nautilus adapter bridge
│   ├── __init__.py
│   ├── paper_engine.py
│   └── nautilus_adapter.py
│
├── risk/                   # Risk management guards, TP/SL monitoring, margin check
│   ├── __init__.py
│   └── risk_manager.py
│
├── tests/                  # Pytest unit and integration test suite
│   ├── __init__.py
│   └── test_straddle.py
│
├── app.py                  # Full-featured Streamlit trading web dashboard
├── main.py                 # Application launcher (launches Streamlit or diagnostics)
├── verify_env.py           # Standalone environment and adapter verification script
├── .env.example            # Template for environment variables (safe to commit)
├── .gitignore              # Git exclusion rules
├── .python-version         # Pinned Python version (3.12)
├── pyproject.toml          # Project metadata & dependencies managed by uv
├── uv.lock                 # Deterministic dependency lockfile
├── requirements.txt        # Pip requirements file
└── README.md               # Project documentation and guide
```

---

## 5. Python Environment & Dependency Management with `uv`

The project is initialized as a native `uv` project. `uv` handles Python version pinning (`.python-version`), virtual environments, and reproducible dependency locks (`uv.lock`).

### Fast Setup (One Command)
Inside `btc-short-straddle/`:
```powershell
uv sync
```
This automatically sets up the `.venv` with Python 3.12 and installs all dependencies exactly as locked in `uv.lock`.

### Launching the Streamlit UI

#### Method 1: Using Virtual Environment Directly (Recommended)
```powershell
# Windows (PowerShell)
.\.venv\Scripts\python.exe main.py

# Or directly through Streamlit executable:
.\.venv\Scripts\streamlit.exe run app.py
```

#### Method 2: Using `uv run`
```powershell
uv run streamlit run app.py
```

The Streamlit UI runs at `http://localhost:8501`.

### Running Verification & Tests
```powershell
# Run environment & Bybit adapter verification check
.\.venv\Scripts\python.exe verify_env.py

# Run test suite
.\.venv\Scripts\python.exe -m pytest
```

---

## 6. Manual Activation (Optional)

If you prefer activating the virtual environment in your terminal:

### Windows (PowerShell)
```powershell
.\.venv\Scripts\Activate.ps1
```

### Windows (Command Prompt - CMD)
```cmd
.\.venv\Scripts\activate.bat
```

### Linux / macOS (bash/zsh)
```bash
source .venv/bin/activate
```

Once activated, standard commands work directly:
```bash
python main.py
python verify_env.py
```

---

## 7. How to Verify NautilusTrader Installation

Run the dedicated verification script:
```powershell
uv run python verify_env.py
```

### Expected Output:
```text
============================================================
  BTC ATM Short Straddle - Environment Verification
============================================================
[x] Python Version:       3.12.12
[x] Virtual Environment:  Active (...)
[x] NautilusTrader:       v1.231.0 (Installed & Importable)
[x] Bybit Adapter:        Available (BybitDataClient & BybitExecClient ready)
[x] python-dotenv:        v1.2.4 (Installed & Importable)
[x] pytest:               v9.2.0 (Installed & Importable)
============================================================
 SUCCESS: uv environment & dependencies verified successfully!
============================================================
```

Or run quick one-liners:
```powershell
uv run python -c "import nautilus_trader; print(nautilus_trader.__version__)"
uv run python -c "from nautilus_trader.adapters.bybit.config import BybitDataClientConfig, BybitExecClientConfig; print('Bybit adapter ready!')"
```

---

## 8. Security Instructions

1. **Never Commit Secrets:** Real API keys and private secrets must **never** be hard-coded or committed to version control.
2. **Environment File (`.env`):**
   - Copy `.env.example` to `.env` when setting up credentials.
   - The `.env` file is excluded in `.gitignore` to prevent accidental commits.
3. **Testnet Only:**
   - Always use **Bybit Testnet** credentials during development and internship testing.
   - Never enter real mainnet credentials or risk real capital during development.

---

## 9. Current Project Status

- **Status:** Phase 1 Complete (Foundation & Setup)
- **Project Structure:** Initialized with `uv init` (`pyproject.toml`, `.python-version`, `uv.lock`)
- **Dependencies:** Managed via `uv add` (`nautilus-trader==1.231.0`, `python-dotenv==1.2.4`, `pytest==9.2.0`)
- **Bybit Integration:** Verified available in NautilusTrader adapter module
- **Verification Script:** Decoupled into [`verify_env.py`](file:///d:/nov/btc-short-straddle/verify_env.py), leaving [`main.py`](file:///d:/nov/btc-short-straddle/main.py) clean.
- **Exchange Connection:** None initiated (deliberately isolated per Phase 1 specification)

---

## 10. Next Development Phase (Phase 2 Preview)

In **Phase 2**, we will:
1. Define configuration settings for Bybit Testnet in `config/`.
2. Model Bybit BTC Option instrument IDs and subscription to the BTC option chain.
3. Implement ATM strike price detection logic based on real-time BTC index/spot feed.
4. Prepare the `TradingNode` and strategy scaffold for short straddle order submission.
