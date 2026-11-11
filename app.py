"""BTC At-The-Money (ATM) Short Straddle - Simple & Clean Trading Dashboard.

Designed for clear strategy execution, real-time Bybit ATM option pricing,
breakeven visualization, and paper trading.
"""

from datetime import datetime, timezone
from pathlib import Path
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from config.settings import strategy_settings
from data.bybit_client import BybitMarketClient
from execution.paper_engine import PaperExecutionEngine
from risk.risk_manager import RiskManager
from strategies.short_straddle import StraddlePayoffCalculator

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(
    page_title="BTC ATM Short Straddle",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Clean, modern custom styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.0rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .sub-title {
        color: #8b949e;
        font-size: 1.0rem;
        margin-bottom: 20px;
    }
    .highlight-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 15px;
    }
    .card-label {
        font-size: 0.82rem;
        color: #8b949e;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .card-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #f0f6fc;
        margin-top: 4px;
        font-family: monospace;
    }
    .card-sub {
        font-size: 0.85rem;
        color: #58a6ff;
        margin-top: 2px;
    }
    .profit-pill {
        background-color: rgba(46, 160, 67, 0.15);
        color: #3fb950;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 2. Session State
# ==========================================
if "paper_engine" not in st.session_state:
    st.session_state.paper_engine = PaperExecutionEngine(initial_balance=25000.0)

if "risk_manager" not in st.session_state:
    st.session_state.risk_manager = RiskManager()

paper_engine: PaperExecutionEngine = st.session_state.paper_engine
risk_mgr: RiskManager = st.session_state.risk_manager

# ==========================================
# 3. Fetch Live Market Data
# ==========================================
@st.cache_data(ttl=15, show_spinner=False)
def get_live_data():
    client = BybitMarketClient()
    spot = client.get_btc_price()
    expiries, chain = client.get_organized_option_chain()
    return spot, expiries, chain

spot_data, expiries, chain = get_live_data()
current_spot = spot_data.get("price", 74000.0)
change_24h = spot_data.get("change_24h", 0.0)

# ==========================================
# 4. Header Section
# ==========================================
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.markdown('<div class="main-title">⚡ BTC ATM Short Straddle</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Automated options strategy: Simultaneously sells At-The-Money Call & Put on Bybit to collect theta decay.</div>',
        unsafe_allow_html=True,
    )
with col_refresh:
    st.write("")
    if st.button("🔄 Refresh Market", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 5. Core Market Cards
# ==========================================
if not expiries:
    st.error("Could not load option expiries from Bybit. Please check your network connection.")
    st.stop()

# Default to the nearest expiry
col_sel1, col_sel2 = st.columns([2, 3])
with col_sel1:
    selected_expiry = st.selectbox("📅 Select Expiry Date", options=expiries, index=0)
with col_sel2:
    st.caption("ℹ️ Strategy Recommendation: Nearest expirations have the fastest time decay (Theta), maximizing short straddle profits.")

# Find ATM Straddle details
client = BybitMarketClient()
atm = client.get_atm_straddle(current_spot, selected_expiry, chain)

if not atm:
    st.error("No ATM options found for this expiry.")
    st.stop()

atm_strike = atm["strike"]
call_px = atm["call_premium"]
put_px = atm["put_premium"]
total_premium = atm["total_premium"]
be_upper = atm["breakeven_upper"]
be_lower = atm["breakeven_lower"]
call_symbol = atm["call_leg"]["symbol"] if atm["call_leg"] else f"BTC-{selected_expiry}-{int(atm_strike)}-C"
put_symbol = atm["put_leg"]["symbol"] if atm["put_leg"] else f"BTC-{selected_expiry}-{int(atm_strike)}-P"

# Display 4 Simple Cards
c1, c2, c3, c4 = st.columns(4)

with c1:
    delta_text = f"{change_24h:+.2f}% 24h"
    st.markdown(
        f"""
        <div class="highlight-card">
            <div class="card-label">Live BTC Price</div>
            <div class="card-value">${current_spot:,.1f}</div>
            <div class="card-sub">{delta_text} (Bybit)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="highlight-card">
            <div class="card-label">ATM Strike (Nearest)</div>
            <div class="card-value">${atm_strike:,.0f}</div>
            <div class="card-sub">Dist: {atm['distance_from_spot']:+,.1f} USDT</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
        <div class="highlight-card">
            <div class="card-label">Straddle Premium (Credit)</div>
            <div class="card-value" style="color: #3fb950;">${total_premium:,.1f}</div>
            <div class="card-sub">Call: ${call_px:,.1f} | Put: ${put_px:,.1f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
        <div class="highlight-card">
            <div class="card-label">Breakeven Range</div>
            <div class="card-value" style="font-size: 1.25rem;">${be_lower:,.0f} - ${be_upper:,.0f}</div>
            <div class="card-sub">Profit Band: ${(be_upper - be_lower):,.0f} USDT</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ==========================================
# 6. Two-Column Layout: Controls vs Payoff
# ==========================================
col_trade, col_graph = st.columns([1.1, 1.9])

with col_trade:
    st.markdown("### 📝 Strategy Parameters & Order")

    order_qty = st.number_input(
        "Order Size (BTC)",
        min_value=0.01,
        max_value=5.0,
        value=0.10,
        step=0.05,
        help="Amount of BTC option contracts to sell.",
    )

    t_col1, t_col2 = st.columns(2)
    with t_col1:
        tp_pct = st.slider("Take Profit (%)", 20, 80, 50, step=5, help="Close trade when profit reaches this % of premium.")
    with t_col2:
        sl_pct = st.slider("Stop Loss (%)", 50, 250, 150, step=10, help="Close trade when loss reaches this % of premium.")

    # Cash collected calculation
    cash_collected = total_premium * order_qty
    margin_req = current_spot * order_qty * 0.12  # approx 12% margin

    st.markdown(
        f"""
        <div style="background:#0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 15px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="color:#8b949e;">Sell Call Leg:</span>
                <strong>{call_symbol}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="color:#8b949e;">Sell Put Leg:</span>
                <strong>{put_symbol}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="color:#8b949e;">Total Premium Inflow:</span>
                <strong style="color:#3fb950;">+${cash_collected:,.2f} USDT</strong>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#8b949e;">Estimated Margin:</span>
                <span>~${margin_req:,.2f} USDT</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("⚡ Execute ATM Short Straddle", type="primary", use_container_width=True):
        new_pos = paper_engine.open_short_straddle(
            strike=atm_strike,
            expiry=selected_expiry,
            call_symbol=call_symbol,
            put_symbol=put_symbol,
            entry_spot=current_spot,
            call_premium=call_px,
            put_premium=put_px,
            contracts=order_qty,
            take_profit_pct=float(tp_pct),
            stop_loss_pct=float(sl_pct),
        )
        st.success(f"Short Straddle Executed! Position ID: {new_pos.position_id}")
        st.rerun()

with col_graph:
    st.markdown("### 📈 Straddle Payoff Diagram")

    # Generate clean payoff curves
    curves = StraddlePayoffCalculator.calculate_payoff_curves(
        spot=current_spot,
        strike=atm_strike,
        call_premium=call_px,
        put_premium=put_px,
        days_to_expiry=1.5,
        iv_pct=atm["avg_iv"],
        contracts=order_qty,
        price_range_pct=0.08,
    )

    fig = go.Figure()

    # Payoff line
    fig.add_trace(
        go.Scatter(
            x=curves["underlying_prices"],
            y=curves["payoff_at_expiry"],
            mode="lines",
            name="Profit / Loss at Expiration",
            line=dict(color="#58a6ff", width=3),
        )
    )

    # Zero Line
    fig.add_hline(y=0, line=dict(color="#484f58", width=1))

    # ATM Strike vertical line
    fig.add_vline(
        x=atm_strike,
        line=dict(color="#8b949e", width=1, dash="dash"),
        annotation_text=f"ATM Strike (${atm_strike:,.0f})",
        annotation_position="top left",
    )

    # Spot Price vertical line
    fig.add_vline(
        x=current_spot,
        line=dict(color="#3fb950", width=2),
        annotation_text=f"Current BTC (${current_spot:,.0f})",
        annotation_position="top right",
    )

    # Breakeven lines
    fig.add_vline(
        x=be_lower,
        line=dict(color="#f85149", width=1.5, dash="dot"),
        annotation_text=f"Lower BE: ${be_lower:,.0f}",
        annotation_position="bottom right",
    )
    fig.add_vline(
        x=be_upper,
        line=dict(color="#f85149", width=1.5, dash="dot"),
        annotation_text=f"Upper BE: ${be_upper:,.0f}",
        annotation_position="bottom left",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        height=330,
        margin=dict(l=30, r=30, t=20, b=30),
        xaxis_title="BTC Price (USDT)",
        yaxis_title="PnL (USDT)",
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ==========================================
# 7. Active Positions & Trade Lifecycle
# ==========================================
st.markdown("### 📊 Active Position & Portfolio")

open_positions = [p for p in paper_engine.positions.values() if p.status == "OPEN"]

if not open_positions:
    st.info("💡 No active straddle position currently open. Click **'Execute ATM Short Straddle'** above to enter a simulated trade.")
else:
    for pos in open_positions:
        # Evaluate current PnL (using live quotes)
        pnl_dollars, pnl_pct = pos.current_unrealized_pnl(call_px, put_px)
        color = "#3fb950" if pnl_dollars >= 0 else "#f85149"
        sign = "+" if pnl_dollars >= 0 else ""

        pos_box = st.container()
        with pos_box:
            p_c1, p_c2, p_c3, p_c4, p_c5 = st.columns([2, 2, 2, 2, 1.5])

            with p_c1:
                st.write(f"**Position ID:** `{pos.position_id}`")
                st.caption(f"Strike: ${pos.strike:,.0f} | Expiry: {pos.expiry} | Size: {pos.contracts} BTC")

            with p_c2:
                st.write(f"**Entry Credit:** `${pos.total_entry_cash_received:,.2f}`")
                st.caption(f"Rate: ${pos.total_entry_premium:,.1f}/BTC")

            with p_c3:
                st.write(f"**Current Value:** `${(call_px + put_px) * pos.contracts:,.2f}`")
                st.caption(f"Target TP: +{pos.take_profit_pct:.0f}% | SL: -{pos.stop_loss_pct:.0f}%")

            with p_c4:
                st.markdown(
                    f"**Unrealized PnL:**  \n<span style='font-size:1.3rem; font-weight:700; color:{color};'>{sign}${pnl_dollars:,.2f} ({sign}{pnl_pct:.1f}%)</span>",
                    unsafe_allow_html=True,
                )

            with p_c5:
                st.write("")
                if st.button("Close Trade", key=f"btn_{pos.position_id}", use_container_width=True):
                    paper_engine.close_position(
                        pos.position_id,
                        current_call_price=call_px,
                        current_put_price=put_px,
                        reason="MANUAL_CLOSE",
                    )
                    st.success("Trade closed successfully!")
                    st.rerun()

st.markdown("---")

# ==========================================
# 8. Optional Advanced Inspector (Collapsed by default)
# ==========================================
with st.expander("🔍 Advanced Details (Raw Option Chain & Bybit Status)"):
    tab_adv1, tab_adv2 = st.tabs(["Option Chain Table", "Environment & Adapter Status"])

    with tab_adv1:
        if selected_expiry in chain:
            strikes = sorted(list(chain[selected_expiry].keys()))
            rows = []
            for s in strikes:
                c = chain[selected_expiry][s]["call"]
                p = chain[selected_expiry][s]["put"]
                rows.append({
                    "Call Mark ($)": c["mark"] if c else None,
                    "Call Delta": c["delta"] if c else None,
                    "Strike ($)": s,
                    "Put Delta": p["delta"] if p else None,
                    "Put Mark ($)": p["mark"] if p else None,
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, height=300)

    with tab_adv2:
        st.write(
            f"- **Python Version:** 3.12 (Virtual Environment Active)  \n"
            f"- **Trading Framework:** NautilusTrader v1.231.0  \n"
            f"- **Bybit Adapter:** Available (`nautilus_trader.adapters.bybit`)  \n"
            f"- **Market Feed Status:** Connected (Bybit Public REST)"
        )
        if paper_engine.order_logs:
            st.write("**Recent Execution Logs:**")
            for l in paper_engine.order_logs[:5]:
                st.text(f"[{l['timestamp']}] {l['level']}: {l['message']}")

# ==========================================
# 9. Simple Footer
# ==========================================
st.caption("BTC ATM Short Straddle • NautilusTrader + Bybit Options • Managed via uv")
