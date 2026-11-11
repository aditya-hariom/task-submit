"""Bybit market data client for BTC spot and options data."""

import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import requests


class BybitMarketClient:
    """Client for retrieving public market data from Bybit REST API."""

    def __init__(self, base_url: str = "https://api.bybit.com", timeout: int = 6):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "NautilusTrader-BTCShortStraddle/1.0",
            "Accept": "application/json",
        })

    def get_btc_price(self) -> Dict[str, Any]:
        """Fetch current BTC/USDT spot and 24h market stats."""
        try:
            url = f"{self.base_url}/v5/market/tickers"
            params = {"category": "linear", "symbol": "BTCUSDT"}
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("result", {}).get("list", [])
            if items:
                item = items[0]
                price = float(item.get("lastPrice", 0.0))
                change_24h = float(item.get("price24hPcnt", 0.0)) * 100
                high_24h = float(item.get("highPrice24h", 0.0))
                low_24h = float(item.get("lowPrice24h", 0.0))
                volume_24h = float(item.get("volume24h", 0.0))
                return {
                    "price": price,
                    "change_24h": change_24h,
                    "high_24h": high_24h,
                    "low_24h": low_24h,
                    "volume_24h": volume_24h,
                    "status": "LIVE",
                }
        except Exception as e:
            # Fallback mock price if network issue
            return {
                "price": 74500.0,
                "change_24h": 1.25,
                "high_24h": 75800.0,
                "low_24h": 73200.0,
                "volume_24h": 12850.5,
                "status": f"FALLBACK ({type(e).__name__})",
            }
        return {"price": 74500.0, "change_24h": 0.0, "high_24h": 75000.0, "low_24h": 74000.0, "volume_24h": 0.0, "status": "DEFAULT"}

    def get_option_tickers(self) -> List[Dict[str, Any]]:
        """Fetch all BTC options tickers from Bybit."""
        try:
            url = f"{self.base_url}/v5/market/tickers"
            params = {"category": "option", "baseCoin": "BTC"}
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", {}).get("list", [])
        except Exception:
            return []

    @staticmethod
    def parse_expiry_date(expiry_str: str) -> Optional[datetime]:
        """Convert '12NOV26' into a datetime object for sorting."""
        try:
            return datetime.strptime(expiry_str, "%d%b%y")
        except Exception:
            return None

    def get_organized_option_chain(self) -> Tuple[List[str], Dict[str, Dict[float, Dict[str, Any]]]]:
        """
        Organizes option tickers by expiration date and strike.
        
        Returns:
            sorted_expiries: List of expiry strings (e.g. ['12NOV26', '13NOV26', ...])
            chain_by_expiry: {expiry: {strike: {'call': {...}, 'put': {...}}}}
        """
        raw_tickers = self.get_option_tickers()
        chain: Dict[str, Dict[float, Dict[str, Any]]] = {}

        for ticker in raw_tickers:
            symbol = ticker.get("symbol", "")
            # Typical format: BTC-12NOV26-74000-C-USDT
            parts = symbol.split("-")
            if len(parts) < 4:
                continue

            expiry = parts[1]
            try:
                strike = float(parts[2])
            except ValueError:
                continue

            opt_type = parts[3].upper()  # 'C' or 'P'

            if expiry not in chain:
                chain[expiry] = {}
            if strike not in chain[expiry]:
                chain[expiry][strike] = {"call": None, "put": None}

            bid = float(ticker.get("bid1Price") or 0.0)
            ask = float(ticker.get("ask1Price") or 0.0)
            mark = float(ticker.get("markPrice") or 0.0)
            mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else mark
            iv = float(ticker.get("markIv") or 0.0) * 100.0  # as percentage
            delta = float(ticker.get("delta") or 0.0)
            gamma = float(ticker.get("gamma") or 0.0)
            vega = float(ticker.get("vega") or 0.0)
            theta = float(ticker.get("theta") or 0.0)
            volume = float(ticker.get("volume24h") or 0.0)
            oi = float(ticker.get("openInterest") or 0.0)

            contract_data = {
                "symbol": symbol,
                "expiry": expiry,
                "strike": strike,
                "type": "Call" if opt_type == "C" else "Put",
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "mark": mark,
                "iv": iv,
                "delta": delta,
                "gamma": gamma,
                "vega": vega,
                "theta": theta,
                "volume": volume,
                "oi": oi,
            }

            if opt_type == "C":
                chain[expiry][strike]["call"] = contract_data
            else:
                chain[expiry][strike]["put"] = contract_data

        # Sort expiries chronologically
        expiries = list(chain.keys())
        expiries.sort(key=lambda x: self.parse_expiry_date(x) or datetime.max)

        return expiries, chain

    def get_atm_straddle(
        self, spot_price: float, expiry: str, chain_by_expiry: Dict[str, Dict[float, Dict[str, Any]]]
    ) -> Optional[Dict[str, Any]]:
        """
        Finds the ATM strike closest to spot_price and packages the short straddle details.
        """
        if expiry not in chain_by_expiry or not chain_by_expiry[expiry]:
            return None

        strikes = sorted(list(chain_by_expiry[expiry].keys()))
        if not strikes:
            return None

        # Find strike with minimum absolute difference from spot price
        atm_strike = min(strikes, key=lambda k: abs(k - spot_price))
        strike_data = chain_by_expiry[expiry][atm_strike]
        call_leg = strike_data.get("call")
        put_leg = strike_data.get("put")

        call_premium = (call_leg["mid"] if call_leg and call_leg["mid"] > 0 else (call_leg["mark"] if call_leg else 0.0))
        put_premium = (put_leg["mid"] if put_leg and put_leg["mid"] > 0 else (put_leg["mark"] if put_leg else 0.0))
        total_premium = call_premium + put_premium

        # Upper and lower breakevens for ATM Short Straddle
        breakeven_upper = atm_strike + total_premium
        breakeven_lower = max(0.0, atm_strike - total_premium)
        max_profit = total_premium

        # Net Greeks for the combined Short Straddle position:
        # Since we SELL the Call and SELL the Put, our position greeks are -1 * leg_greek
        call_delta = call_leg["delta"] if call_leg else 0.5
        put_delta = put_leg["delta"] if put_leg else -0.5
        net_delta = -1.0 * (call_delta + put_delta)

        call_gamma = call_leg["gamma"] if call_leg else 0.0
        put_gamma = put_leg["gamma"] if put_leg else 0.0
        net_gamma = -1.0 * (call_gamma + put_gamma)

        call_theta = call_leg["theta"] if call_leg else 0.0
        put_theta = put_leg["theta"] if put_leg else 0.0
        # Bybit theta is negative for long, so for short straddle we collect positive theta
        net_theta = -1.0 * (call_theta + put_theta)

        call_vega = call_leg["vega"] if call_leg else 0.0
        put_vega = put_leg["vega"] if put_leg else 0.0
        net_vega = -1.0 * (call_vega + put_vega)

        # Average IV
        avg_iv = ((call_leg["iv"] if call_leg else 50.0) + (put_leg["iv"] if put_leg else 50.0)) / 2.0

        return {
            "expiry": expiry,
            "strike": atm_strike,
            "spot_price": spot_price,
            "distance_from_spot": atm_strike - spot_price,
            "distance_pct": ((atm_strike - spot_price) / spot_price) * 100,
            "call_leg": call_leg,
            "put_leg": put_leg,
            "call_premium": call_premium,
            "put_premium": put_premium,
            "total_premium": total_premium,
            "breakeven_upper": breakeven_upper,
            "breakeven_lower": breakeven_lower,
            "max_profit": max_profit,
            "avg_iv": avg_iv,
            "net_delta": net_delta,
            "net_gamma": net_gamma,
            "net_theta": net_theta,
            "net_vega": net_vega,
        }

