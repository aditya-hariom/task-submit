"""Configuration settings for BTC ATM Short Straddle strategy and application."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Base project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class BybitSettings:
    """Bybit connection and API configuration."""
    api_key: str = os.getenv("BYBIT_TESTNET_API_KEY", "")
    api_secret: str = os.getenv("BYBIT_TESTNET_API_SECRET", "")
    testnet: bool = True
    
    # Public endpoints
    mainnet_rest_url: str = "https://api.bybit.com"
    testnet_rest_url: str = "https://api-testnet.bybit.com"
    
    @property
    def base_url(self) -> str:
        return self.testnet_rest_url if self.testnet else self.mainnet_rest_url


@dataclass
class StrategySettings:
    """Short Straddle strategy configuration parameters."""
    underlying: str = "BTC"
    settlement_currency: str = "USDT"
    default_order_size: float = 0.1  # BTC contracts
    default_take_profit_pct: float = 50.0  # % of collected premium
    default_stop_loss_pct: float = 150.0  # % of collected premium
    delta_tolerance: float = 0.15  # Max allowable net delta drift before re-hedge alert
    max_drawdown_pct: float = 10.0  # Max account drawdown allowed
    initial_paper_balance: float = 25000.0  # Initial paper trading USDT balance


bybit_settings = BybitSettings()
strategy_settings = StrategySettings()

