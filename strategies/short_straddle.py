"""BTC At-The-Money (ATM) Short Straddle Strategy Logic & Payoff Modeling."""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def standard_normal_cdf(x: float) -> float:
    """Cumulative distribution function for standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def standard_normal_pdf(x: float) -> float:
    """Probability density function for standard normal distribution."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


@dataclass
class BlackScholesGreeks:
    """Black-Scholes analytical Greeks and theoretical pricing."""
    price: float
    delta: float
    gamma: float
    theta: float
    vega: float


class BlackScholes:
    """Black-Scholes-Merton model for European options pricing and Greeks."""

    @staticmethod
    def calculate(
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        volatility: float,
        risk_free_rate: float = 0.04,
        is_call: bool = True,
    ) -> BlackScholesGreeks:
        """
        Calculate price and Greeks using Black-Scholes formula.
        """
        if time_to_expiry_years <= 1e-6:
            # At expiration
            if is_call:
                val = max(0.0, spot - strike)
                d = 1.0 if spot > strike else 0.0
            else:
                val = max(0.0, strike - spot)
                d = -1.0 if spot < strike else 0.0
            return BlackScholesGreeks(price=val, delta=d, gamma=0.0, theta=0.0, vega=0.0)

        vol = max(0.01, volatility)
        t = max(1e-6, time_to_expiry_years)
        sqrt_t = math.sqrt(t)

        d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * vol * vol) * t) / (vol * sqrt_t)
        d2 = d1 - vol * sqrt_t

        pdf_d1 = standard_normal_pdf(d1)
        cdf_d1 = standard_normal_cdf(d1)
        cdf_d2 = standard_normal_cdf(d2)

        gamma = pdf_d1 / (spot * vol * sqrt_t)
        vega = spot * pdf_d1 * sqrt_t * 0.01  # 1% vol change

        if is_call:
            price = spot * cdf_d1 - strike * math.exp(-risk_free_rate * t) * cdf_d2
            delta = cdf_d1
            theta_annual = -(spot * pdf_d1 * vol) / (2 * sqrt_t) - risk_free_rate * strike * math.exp(
                -risk_free_rate * t
            ) * cdf_d2
        else:
            cdf_neg_d1 = standard_normal_cdf(-d1)
            cdf_neg_d2 = standard_normal_cdf(-d2)
            price = strike * math.exp(-risk_free_rate * t) * cdf_neg_d2 - spot * cdf_neg_d1
            delta = cdf_d1 - 1.0
            theta_annual = -(spot * pdf_d1 * vol) / (2 * sqrt_t) + risk_free_rate * strike * math.exp(
                -risk_free_rate * t
            ) * cdf_neg_d2

        theta_daily = theta_annual / 365.0
        return BlackScholesGreeks(
            price=max(0.0, price),
            delta=delta,
            gamma=gamma,
            theta=theta_daily,
            vega=vega,
        )


@dataclass
class StraddlePosition:
    """Represents an active or historical BTC ATM Short Straddle trade."""
    position_id: str
    strike: float
    expiry: str
    call_symbol: str
    put_symbol: str
    entry_spot: float
    entry_call_premium: float
    entry_put_premium: float
    contracts: float  # e.g., 0.1 BTC
    take_profit_pct: float = 50.0
    stop_loss_pct: float = 150.0
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "OPEN"  # OPEN, CLOSED_TP, CLOSED_SL, CLOSED_MANUAL, EXPIRED
    exit_time: Optional[datetime] = None
    exit_call_price: float = 0.0
    exit_put_price: float = 0.0
    realized_pnl: float = 0.0

    @property
    def total_entry_premium(self) -> float:
        return self.entry_call_premium + self.entry_put_premium

    @property
    def total_entry_cash_received(self) -> float:
        return self.total_entry_premium * self.contracts

    @property
    def breakeven_upper(self) -> float:
        return self.strike + self.total_entry_premium

    @property
    def breakeven_lower(self) -> float:
        return max(0.0, self.strike - self.total_entry_premium)

    def current_unrealized_pnl(self, current_call_price: float, current_put_price: float) -> Tuple[float, float]:
        """
        Calculates unrealized PnL ($) and return on premium (%).
        Because we sold options:
        PnL = (Entry Premium - Current Market Price) * contracts
        """
        call_diff = self.entry_call_premium - current_call_price
        put_diff = self.entry_put_premium - current_put_price
        pnl_dollars = (call_diff + put_diff) * self.contracts
        total_entry = self.total_entry_cash_received
        pnl_pct = (pnl_dollars / total_entry * 100.0) if total_entry > 0 else 0.0
        return pnl_dollars, pnl_pct


class StraddlePayoffCalculator:
    """Calculates multi-horizon payoffs and Greek profiles for Short Straddles."""

    @staticmethod
    def calculate_payoff_curves(
        spot: float,
        strike: float,
        call_premium: float,
        put_premium: float,
        days_to_expiry: float = 2.0,
        iv_pct: float = 50.0,
        contracts: float = 1.0,
        price_range_pct: float = 0.12,  # +/- 12% around spot
        num_points: int = 100,
    ) -> Dict[str, Any]:
        """
        Generates payoff curves:
        1. At Expiration Payoff (Intrinsic payoff)
        2. T+0 (Current Theoretical Payoff with time value)
        3. T+50% (Halfway to expiry payoff)
        """
        total_premium = call_premium + put_premium
        min_price = spot * (1.0 - price_range_pct)
        max_price = spot * (1.0 + price_range_pct)
        step = (max_price - min_price) / (num_points - 1)

        prices: List[float] = [min_price + i * step for i in range(num_points)]
        payoff_expiry: List[float] = []
        payoff_t0: List[float] = []
        payoff_half: List[float] = []

        t_annual = max(days_to_expiry / 365.0, 1e-6)
        vol = iv_pct / 100.0

        for s in prices:
            # At Expiration:
            # Payoff = Total Premium - max(0, S - K) - max(0, K - S)
            call_payoff = max(0.0, s - strike)
            put_payoff = max(0.0, strike - s)
            p_expiry = (total_premium - call_payoff - put_payoff) * contracts
            payoff_expiry.append(p_expiry)

            # At T+0:
            bs_call_t0 = BlackScholes.calculate(s, strike, t_annual, vol, is_call=True)
            bs_put_t0 = BlackScholes.calculate(s, strike, t_annual, vol, is_call=False)
            p_t0 = (total_premium - (bs_call_t0.price + bs_put_t0.price)) * contracts
            payoff_t0.append(p_t0)

            # At T + 50%:
            bs_call_half = BlackScholes.calculate(s, strike, t_annual * 0.5, vol, is_call=True)
            bs_put_half = BlackScholes.calculate(s, strike, t_annual * 0.5, vol, is_call=False)
            p_half = (total_premium - (bs_call_half.price + bs_put_half.price)) * contracts
            payoff_half.append(p_half)

        breakeven_upper = strike + total_premium
        breakeven_lower = max(0.0, strike - total_premium)
        max_profit = total_premium * contracts

        return {
            "underlying_prices": prices,
            "payoff_at_expiry": payoff_expiry,
            "payoff_t0": payoff_t0,
            "payoff_half": payoff_half,
            "breakeven_upper": breakeven_upper,
            "breakeven_lower": breakeven_lower,
            "max_profit": max_profit,
            "strike": strike,
            "spot": spot,
        }
