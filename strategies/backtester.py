"""Backtesting and scenario simulation engine for BTC ATM Short Straddle."""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd


@dataclass
class BacktestResult:
    """Statistical summary of backtest performance."""
    initial_balance: float
    final_balance: float
    total_return_dollars: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    equity_curve: pd.DataFrame
    trade_log: pd.DataFrame


class StraddleBacktester:
    """Simulates performance of BTC ATM Short Straddle under configurable market regimes."""

    @staticmethod
    def run_simulation(
        initial_capital: float = 25000.0,
        num_cycles: int = 40,
        dte_days: int = 2,
        take_profit_pct: float = 50.0,
        stop_loss_pct: float = 150.0,
        iv_annual_pct: float = 55.0,
        contracts: float = 0.1,
        regime: str = "Range-bound (Normal Vol)",  # "Range-bound", "High Volatility Breakout", "Low Vol Drift"
        seed: int = 42,
    ) -> BacktestResult:
        """
        Executes an event-driven sequence of ATM short straddles.
        """
        random.seed(seed)
        daily_vol = (iv_annual_pct / 100.0) / math.sqrt(365.0)

        if "Low Vol" in regime:
            vol_multiplier = 0.65
            trend_bias = 0.0002
        elif "High Vol" in regime:
            vol_multiplier = 1.45
            trend_bias = 0.002
        else:
            vol_multiplier = 1.0
            trend_bias = 0.0

        current_balance = initial_capital
        peak_balance = initial_capital
        max_drawdown_pct = 0.0
        equity_records = [{"trade_num": 0, "equity": current_balance, "drawdown_pct": 0.0}]
        trades: List[Dict] = []

        btc_price = 74000.0
        gross_profits = 0.0
        gross_losses = 0.0
        returns_list: List[float] = []

        for cycle in range(1, num_cycles + 1):
            strike = round(btc_price / 250.0) * 250.0
            t_annual = dte_days / 365.0
            vol = (iv_annual_pct / 100.0) * vol_multiplier

            # Approximate straddle initial premium using Brenner-Subrahmanyam formula:
            # ATM Straddle approx = 0.8 * S * sigma * sqrt(T)
            total_premium = 0.7978 * btc_price * vol * math.sqrt(t_annual)
            max_profit = total_premium * contracts
            max_loss_limit = max_profit * (stop_loss_pct / 100.0)
            tp_target = max_profit * (take_profit_pct / 100.0)

            # Simulate intra-cycle path for underlying price
            steps = dte_days * 24  # Hourly steps
            dt = 1.0 / (365.0 * 24.0)
            cur_price = btc_price
            exit_reason = "EXPIRED_ATM"
            realized_pnl = 0.0
            exit_step = steps

            for s in range(1, steps + 1):
                # Geometric Brownian motion step
                z = random.gauss(0.0, 1.0)
                cur_price *= math.exp((trend_bias - 0.5 * vol * vol) * dt + vol * math.sqrt(dt) * z)

                # Time remaining
                t_rem = max(1e-6, (steps - s) / (365.0 * 24.0))

                # Check intrinsic payoff & remaining time value
                intrinsic_loss = (max(0.0, cur_price - strike) + max(0.0, strike - cur_price)) * contracts
                time_decay_factor = math.sqrt(t_rem / t_annual)
                curr_option_cost = (intrinsic_loss + (max_profit - intrinsic_loss) * time_decay_factor)
                curr_pnl = max_profit - curr_option_cost

                # Take Profit hit?
                if curr_pnl >= tp_target:
                    exit_reason = "TAKE_PROFIT"
                    realized_pnl = tp_target
                    exit_step = s
                    break

                # Stop Loss hit?
                if curr_pnl <= -max_loss_limit:
                    exit_reason = "STOP_LOSS"
                    realized_pnl = -max_loss_limit
                    exit_step = s
                    break

            if exit_reason == "EXPIRED_ATM":
                # Final payoff at expiry
                final_loss = (max(0.0, cur_price - strike) + max(0.0, strike - cur_price)) * contracts
                realized_pnl = max_profit - final_loss
                if realized_pnl > 0:
                    exit_reason = "EXPIRED_PROFIT"
                else:
                    exit_reason = "EXPIRED_LOSS"

            # Apply small transaction fee / exchange slippage
            fee = 1.5 * contracts  # ~$0.15 on 0.1 BTC
            realized_pnl -= fee

            current_balance += realized_pnl
            if current_balance > peak_balance:
                peak_balance = current_balance
            dd = ((peak_balance - current_balance) / peak_balance) * 100.0 if peak_balance > 0 else 0.0
            if dd > max_drawdown_pct:
                max_drawdown_pct = dd

            ret = realized_pnl / initial_capital
            returns_list.append(ret)

            if realized_pnl > 0:
                gross_profits += realized_pnl
            else:
                gross_losses += abs(realized_pnl)

            trades.append({
                "Cycle": cycle,
                "Strike": strike,
                "Start_BTC": round(btc_price, 1),
                "End_BTC": round(cur_price, 1),
                "Premium_Collected": round(max_profit, 2),
                "Realized_PnL": round(realized_pnl, 2),
                "Return_Pct": round((realized_pnl / max_profit) * 100 if max_profit > 0 else 0.0, 1),
                "Outcome": exit_reason,
                "Duration_Hrs": exit_step,
            })

            equity_records.append({
                "trade_num": cycle,
                "equity": round(current_balance, 2),
                "drawdown_pct": round(dd, 2),
            })

            # Next cycle spot starts from cur_price
            btc_price = cur_price

        # Statistics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["Realized_PnL"] > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0
        profit_factor = (gross_profits / gross_losses) if gross_losses > 0 else 9.99

        # Sharpe ratio
        if returns_list:
            avg_ret = sum(returns_list) / len(returns_list)
            variance = sum((r - avg_ret) ** 2 for r in returns_list) / len(returns_list)
            std_ret = math.sqrt(variance) if variance > 0 else 1e-6
            annualized_sharpe = (avg_ret / std_ret) * math.sqrt(365.0 / dte_days)
        else:
            annualized_sharpe = 0.0

        total_return_dollars = current_balance - initial_capital
        total_return_pct = (total_return_dollars / initial_capital) * 100.0

        return BacktestResult(
            initial_balance=initial_capital,
            final_balance=current_balance,
            total_return_dollars=total_return_dollars,
            total_return_pct=total_return_pct,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=annualized_sharpe,
            equity_curve=pd.DataFrame(equity_records),
            trade_log=pd.DataFrame(trades),
        )

