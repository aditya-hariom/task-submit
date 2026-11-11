"""NautilusTrader adapter integration for Bybit exchange."""

from typing import Any, Dict, Optional


def check_nautilus_bybit_adapter() -> Dict[str, Any]:
    """
    Validates NautilusTrader framework and Bybit adapter availability.
    """
    status = {
        "nautilus_trader_installed": False,
        "nautilus_version": None,
        "bybit_adapter_available": False,
        "data_client_config": False,
        "exec_client_config": False,
        "error": None,
    }

    try:
        import nautilus_trader
        status["nautilus_trader_installed"] = True
        status["nautilus_version"] = getattr(nautilus_trader, "__version__", "1.231.0")

        from nautilus_trader.adapters.bybit.config import (
            BybitDataClientConfig,
            BybitExecClientConfig,
        )
        from nautilus_trader.adapters.bybit.factories import (
            BybitLiveDataClientFactory,
            BybitLiveExecClientFactory,
        )

        status["bybit_adapter_available"] = True
        status["data_client_config"] = True
        status["exec_client_config"] = True
    except Exception as e:
        status["error"] = str(e)

    return status


def create_nautilus_bybit_node_config(
    api_key: str,
    api_secret: str,
    testnet: bool = True,
) -> Dict[str, Any]:
    """
    Builds the configuration schema for NautilusTrader TradingNode with Bybit adapter.
    """
    try:
        from nautilus_trader.adapters.bybit.config import (
            BybitDataClientConfig,
            BybitExecClientConfig,
        )

        data_config = BybitDataClientConfig(
            api_key=api_key or None,
            api_secret=api_secret or None,
            testnet=testnet,
        )
        exec_config = BybitExecClientConfig(
            api_key=api_key or None,
            api_secret=api_secret or None,
            testnet=testnet,
        )

        return {
            "status": "CONFIG_BUILT_SUCCESSFULLY",
            "testnet": testnet,
            "data_config": repr(data_config),
            "exec_config": repr(exec_config),
        }
    except Exception as e:
        return {
            "status": "CONFIG_ERROR",
            "error": str(e),
            "testnet": testnet,
        }

