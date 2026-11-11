"""Unit tests for BTC ATM Short Straddle components."""

import pytest
from strategies.short_straddle import (
    BlackScholes,
    StraddlePayoffCalculator,
    StraddlePosition,
)
from risk.risk_manager import RiskManager
from execution.paper_engine import PaperExecutionEngine
from data.bybit_client import BybitMarketClient


def test_black_scholes_at_expiration():
    """At expiration (T=0), option price equals intrinsic value."""
    # Call option in the money
    call = BlackScholes.calculate(spot=75000, strike=74000, time_to_expiry_years=0, volatility=0.5, is_call=True)
    assert call.price == 1000.0
    assert call.delta == 1.0

    # Put option in the money
    put = BlackScholes.calculate(spot=73000, strike=74000, time_to_expiry_years=0, volatility=0.5, is_call=False)
    assert put.price == 1000.0
    assert put.delta == -1.0


def test_payoff_calculator_breakevens_and_max_profit():
    """Test ATM straddle payoff calculation, breakevens, and max profit."""
    strike = 74000.0
    call_prem = 600.0
    put_prem = 550.0
    total_prem = call_prem + put_prem
    contracts = 1.0

    res = StraddlePayoffCalculator.calculate_payoff_curves(
        spot=74000.0,
        strike=strike,
        call_premium=call_prem,
        put_premium=put_prem,
        days_to_expiry=2.0,
        contracts=contracts,
    )

    assert res["max_profit"] == total_prem * contracts
    assert res["breakeven_upper"] == strike + total_prem
    assert res["breakeven_lower"] == strike - total_prem


def test_risk_manager_tp_and_sl():
    """Test RiskManager triggers TP and SL appropriately."""
    rm = RiskManager(default_tp_pct=50.0, default_sl_pct=150.0)

    pos = StraddlePosition(
        position_id="TEST-1",
        strike=74000.0,
        expiry="12NOV26",
        call_symbol="BTC-12NOV26-74000-C",
        put_symbol="BTC-12NOV26-74000-P",
        entry_spot=74000.0,
        entry_call_premium=500.0,
        entry_put_premium=500.0,
        contracts=0.1,
        take_profit_pct=50.0,
        stop_loss_pct=150.0,
    )

    # 1. Nominal price -> HOLD
    res_hold = rm.evaluate_position_risk(pos, current_call_price=450.0, current_put_price=450.0, current_spot=74000.0)
    assert res_hold.action == "HOLD"

    # 2. Premiums decayed from 1000 total to 400 total -> +60% profit -> TAKE_PROFIT
    res_tp = rm.evaluate_position_risk(pos, current_call_price=200.0, current_put_price=200.0, current_spot=74000.0)
    assert res_tp.action == "TAKE_PROFIT"

    # 3. Market exploded, combined premiums doubled from 1000 to 2600 -> -160% loss -> STOP_LOSS
    res_sl = rm.evaluate_position_risk(pos, current_call_price=2000.0, current_put_price=600.0, current_spot=76500.0)
    assert res_sl.action == "STOP_LOSS"


def test_paper_execution_engine():
    """Test simulated order execution and portfolio PnL."""
    engine = PaperExecutionEngine(initial_balance=20000.0)

    pos = engine.open_short_straddle(
        strike=74000.0,
        expiry="12NOV26",
        call_symbol="BTC-12NOV26-74000-C-USDT",
        put_symbol="BTC-12NOV26-74000-P-USDT",
        entry_spot=74000.0,
        call_premium=500.0,
        put_premium=500.0,
        contracts=0.1,
    )

    # Premium collected = (500 + 500) * 0.1 = 100 USDT
    assert engine.balance == 20100.0
    assert len(engine.positions) == 1

    # Buyback when premium is decayed to 200 + 200 = 400 total (buyback cost = 40 USDT)
    closed = engine.close_position(pos.position_id, current_call_price=200.0, current_put_price=200.0, reason="TAKE_PROFIT")
    assert closed is not None
    assert closed.status == "TAKE_PROFIT"
    # Realized PnL should be +60 USDT (100 - 40)
    assert pytest.approx(closed.realized_pnl, 0.01) == 60.0
    assert pytest.approx(engine.balance, 0.01) == 20060.0


def test_bybit_market_client_expiry_parsing():
    """Test date parsing logic."""
    dt = BybitMarketClient.parse_expiry_date("12NOV26")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 11
    assert dt.day == 12

