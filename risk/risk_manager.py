"""Risk management guards and automated triggers for BTC Short Straddle."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from strategies.short_straddle import StraddlePosition


@dataclass
class RiskCheckResult:
    """Outcome of risk evaluation on an active position."""
    can_trade: bool
    action: str  # HOLD, TAKE_PROFIT, STOP_LOSS, HEDGE_DELTA, MARGIN_CALL
    reason: str
    net_delta: float = 0.0
    pnl_dollars: float = 0.0
    pnl_pct: float = 0.0


class RiskManager:
    """Monitors and enforces risk boundaries for short straddle trades."""

    def __init__(
        self,
        max_drawdown_pct: float = 10.0,
        delta_tolerance: float = 0.15,
        default_tp_pct: float = 50.0,
        default_sl_pct: float = 150.0,
    ):
        self.max_drawdown_pct = max_drawdown_pct
        self.delta_tolerance = delta_tolerance
        self.default_tp_pct = default_tp_pct
        self.default_sl_pct = default_sl_pct

    def evaluate_position_risk(
        self,
        position: StraddlePosition,
        current_call_price: float,
        current_put_price: float,
        current_spot: float,
        net_delta: float = 0.0,
    ) -> RiskCheckResult:
        """
        Evaluates position against stop-loss, take-profit, and delta neutral limits.
        """
        pnl_dollars, pnl_pct = position.current_unrealized_pnl(current_call_price, current_put_price)

        # 1. Take Profit check (e.g. +50% of premium collected)
        if pnl_pct >= position.take_profit_pct:
            return RiskCheckResult(
                can_trade=True,
                action="TAKE_PROFIT",
                reason=f"Take Profit target achieved (+{pnl_pct:.1f}% >= +{position.take_profit_pct:.1f}%)",
                net_delta=net_delta,
                pnl_dollars=pnl_dollars,
                pnl_pct=pnl_pct,
            )

        # 2. Stop Loss check (e.g. -150% loss of initial premium collected)
        if pnl_pct <= -abs(position.stop_loss_pct):
            return RiskCheckResult(
                can_trade=False,
                action="STOP_LOSS",
                reason=f"Stop Loss breached ({pnl_pct:.1f}% <= -{position.stop_loss_pct:.1f}%)",
                net_delta=net_delta,
                pnl_dollars=pnl_dollars,
                pnl_pct=pnl_pct,
            )

        # 3. Delta drift alert (delta neutral guard)
        if abs(net_delta) > self.delta_tolerance:
            return RiskCheckResult(
                can_trade=True,
                action="HEDGE_DELTA",
                reason=f"Net Delta drift detected ({net_delta:+.3f} exceeds tolerance ±{self.delta_tolerance})",
                net_delta=net_delta,
                pnl_dollars=pnl_dollars,
                pnl_pct=pnl_pct,
            )

        # 4. Breakeven buffer monitor
        if current_spot > position.breakeven_upper:
            return RiskCheckResult(
                can_trade=True,
                action="UPPER_BREACH",
                reason=f"Spot price (${current_spot:,.1f}) breached Upper Breakeven (${position.breakeven_upper:,.1f})",
                net_delta=net_delta,
                pnl_dollars=pnl_dollars,
                pnl_pct=pnl_pct,
            )
        elif current_spot < position.breakeven_lower:
            return RiskCheckResult(
                can_trade=True,
                action="LOWER_BREACH",
                reason=f"Spot price (${current_spot:,.1f}) breached Lower Breakeven (${position.breakeven_lower:,.1f})",
                net_delta=net_delta,
                pnl_dollars=pnl_dollars,
                pnl_pct=pnl_pct,
            )

        return RiskCheckResult(
            can_trade=True,
            action="HOLD",
            reason="Position within nominal risk parameters",
            net_delta=net_delta,
            pnl_dollars=pnl_dollars,
            pnl_pct=pnl_pct,
        )

    def calculate_margin_requirement(self, spot_price: float, contracts: float) -> float:
        """
        Estimate Bybit initial margin requirement for short options:
        Typically ~10% of underlying notional value for ATM options.
        """
        notional = spot_price * contracts
        return notional * 0.12  # 12% margin estimate

