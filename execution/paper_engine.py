"""Paper trading execution engine and simulated order lifecycle."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from strategies.short_straddle import StraddlePosition


class PaperExecutionEngine:
    """Manages paper trading orders, positions, and simulated PnL."""

    def __init__(self, initial_balance: float = 25000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, StraddlePosition] = {}
        self.trade_history: List[Dict] = []
        self.order_logs: List[Dict] = []

    def log_event(self, message: str, level: str = "INFO") -> None:
        """Record an execution event with timestamp."""
        self.order_logs.insert(0, {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "level": level,
            "message": message,
        })

    def open_short_straddle(
        self,
        strike: float,
        expiry: str,
        call_symbol: str,
        put_symbol: str,
        entry_spot: float,
        call_premium: float,
        put_premium: float,
        contracts: float = 0.1,
        take_profit_pct: float = 50.0,
        stop_loss_pct: float = 150.0,
    ) -> StraddlePosition:
        """
        Executes paper sell order for both Call and Put legs at ATM strike.
        """
        pos_id = f"STRADDLE-{uuid.uuid4().hex[:6].upper()}"
        pos = StraddlePosition(
            position_id=pos_id,
            strike=strike,
            expiry=expiry,
            call_symbol=call_symbol,
            put_symbol=put_symbol,
            entry_spot=entry_spot,
            entry_call_premium=call_premium,
            entry_put_premium=put_premium,
            contracts=contracts,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            entry_time=datetime.now(timezone.utc),
            status="OPEN",
        )

        total_premium_collected = (call_premium + put_premium) * contracts
        self.balance += total_premium_collected
        self.positions[pos_id] = pos

        self.log_event(
            f"OPENED SHORT STRADDLE [{pos_id}]: Sell {contracts}x {call_symbol} @ ${call_premium:,.2f} "
            f"& {put_symbol} @ ${put_premium:,.2f}. Premium collected: +${total_premium_collected:,.2f} USDT",
            level="SUCCESS",
        )
        return pos

    def close_position(
        self,
        position_id: str,
        current_call_price: float,
        current_put_price: float,
        reason: str = "MANUAL_CLOSE",
    ) -> Optional[StraddlePosition]:
        """
        Closes an open short straddle position by buying back both legs.
        """
        if position_id not in self.positions:
            return None

        pos = self.positions[position_id]
        if pos.status != "OPEN":
            return pos

        pnl_dollars, pnl_pct = pos.current_unrealized_pnl(current_call_price, current_put_price)
        buyback_cost = (current_call_price + current_put_price) * pos.contracts
        self.balance -= buyback_cost

        pos.status = reason
        pos.exit_time = datetime.now(timezone.utc)
        pos.exit_call_price = current_call_price
        pos.exit_put_price = current_put_price
        pos.realized_pnl = pnl_dollars

        self.trade_history.insert(0, {
            "id": pos.position_id,
            "strike": pos.strike,
            "expiry": pos.expiry,
            "contracts": pos.contracts,
            "entry_premium": pos.total_entry_premium,
            "exit_premium": current_call_price + current_put_price,
            "pnl_dollars": pnl_dollars,
            "pnl_pct": pnl_pct,
            "reason": reason,
            "entry_time": pos.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_time": pos.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
        })

        level = "SUCCESS" if pnl_dollars >= 0 else "WARNING"
        self.log_event(
            f"CLOSED STRADDLE [{pos.position_id}]: Reason: {reason}. Buyback: ${buyback_cost:,.2f}. "
            f"Realized PnL: {pnl_dollars:+,.2f} USDT ({pnl_pct:+.1f}%)",
            level=level,
        )

        return pos

    def close_all(self, current_call_price: float, current_put_price: float, reason: str = "EMERGENCY_FLATTEN") -> int:
        """Close all open positions immediately."""
        closed_count = 0
        open_ids = [pid for pid, p in self.positions.items() if p.status == "OPEN"]
        for pid in open_ids:
            self.close_position(pid, current_call_price, current_put_price, reason=reason)
            closed_count += 1
        return closed_count

    def get_account_summary(self, current_call_price: float, current_put_price: float, spot_price: float) -> Dict:
        """Compute portfolio equity, unrealized PnL, and margin."""
        unrealized_pnl = 0.0
        locked_margin = 0.0
        open_count = 0

        for pos in self.positions.values():
            if pos.status == "OPEN":
                pnl, _ = pos.current_unrealized_pnl(current_call_price, current_put_price)
                unrealized_pnl += pnl
                locked_margin += (spot_price * pos.contracts * 0.12)
                open_count += 1

        total_equity = self.balance + unrealized_pnl
        net_return_pct = ((total_equity - self.initial_balance) / self.initial_balance) * 100.0

        return {
            "initial_balance": self.initial_balance,
            "cash_balance": self.balance,
            "unrealized_pnl": unrealized_pnl,
            "total_equity": total_equity,
            "locked_margin": locked_margin,
            "available_margin": max(0.0, total_equity - locked_margin),
            "net_return_pct": net_return_pct,
            "open_positions_count": open_count,
        }
