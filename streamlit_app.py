import streamlit as st
import pandas as pd
from datetime import datetime
import ccxt
import numpy as np
from database.supabase import get_all_data_live, send_chat_message

st.set_page_config(page_title="🦅 KI-Learning-Cockpit", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 18px; border-radius: 10px; border-left: 5px solid #00ff66; margin-bottom: 15px; }
    .hit { color: #00ff66; font-weight: bold; }
    .miss { color: #ff4d4d; font-weight: bold; }
    .dataframe th { background-color: #1e222d !important; color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

MONITORED_ASSETS = ["BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "TRX-USD", "LINK-USD", "SUI-USD"]

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices); seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=15)
def get_market_overview(assets):
    results = []
    try:
        exchange = ccxt.kraken()
        for symbol in assets:
            ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
            row = {"Symbol": symbol, "Kurs (USD)": f"${ticker['last']:,.2f}"}
            timeframes = ['5m', '15m', '1h', '4h', '1d']
            for tf in timeframes:
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=tf, limit=50)
                    if ohlcv:
                        closes = [c[4] for c in ohlcv]
                        rsi_values = []
                        for i in range(len(closes)):
                            if i >= 14: rsi_values.append(calculate_rsi(closes[:i+1]))
                        if len(rsi_values) >= 2:
                            current_rsi = rsi_values[-1]
                            prev_rsi = rsi_values[-2]
                            trend = "⬆️" if current_rsi > prev_rsi else "⬇️"
                        else: current_rsi, trend = 50, "➖"
                        
                        sig = "LONG" if current_rsi < 30 else ("SELL" if current_rsi > 70 else "HOLD")
                        row[f"{tf}_RSI"] = f"{trend} {current_rsi:.1f}"
                        row[f"{tf}_Sig"] = sig
                    else:
                        row[f"{tf}_RSI"] = "N/A"; row[f"{tf}_Sig"] = "N/A"
                except: row[f"{tf}_RSI"] = "N/A"; row[f"{tf}_Sig"] = "N/A"
            results.append(row)
    except: pass
    return pd.DataFrame(results) if results else pd.DataFrame()

trades, chat, risiko, knowledge = get_all_data_live()

guthaben = 200.0
win_trades, loss_trades = 0, 0
if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if isinstance(t, dict) and t.get("Status") == "CLOSED":
            pnl = float(t.get("net_pnl") or 0.0); guthaben += pnl
            if pnl > 0: win_trades += 1
            else: loss_trades += 1
total = win_trades + loss_trades
win_rate = (win_trades / total * 100) if total > 0 else 0.0

dynamic_risk = max(0.5, min(3.0, (2 * (win_rate / 100) - 1) * 5))
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Depotwert", f"${guthaben:.2f}")
col2.metric("📊 Trefferquote", f"{win_rate:.1f}%")
col3.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "KRITISCH")
col4.metric("⚡ Dynamisches Risiko", f"{dynamic_risk:.1f}%", help="Prozentsatz des Guthabens pro Trade (0.5% - 3%)")
st.markdown("---")

st.subheader(f"📊 Live-Übersicht (Alle Assets & Signale)")
df_market = get_market_overview(MONITORED_ASSETS)
if not df_market.empty:
    def highlight_cells(val):
        if "LONG" in str(val): return "background-color: #1a3b1a; color: #00ff66; font-weight: bold;"
        elif "SELL" in str(val): return "background-color: #3b1a1a; color: #ff4d4d; font-weight: bold;"
        elif "HOLD" in str(val): return "background-color: #2a2a2a; color: #ffcc00; font-weight: bold;"
        if "⬆️" in str(val): return "color: #00ff66; font-weight: bold;"
        elif "⬇️" in str(val): return "color: #ff4d4d; font-weight: bold;"
        elif "N/A" in str(val): return "color: #555555;"
        return ""
    signal_cols = [f"{tf}_Sig" for tf in ['5m', '15m', '1h', '4h', '1d']]
    rsi_cols = [f"{tf}_RSI" for tf in ['5m', '15m', '1h', '4h', '1d']]
    styled_df = df_market.style.map(highlight_cells, subset=signal_cols + rsi_cols)
    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=600)
else: st.info("Marktdaten werden geladen...")
st.markdown("---")

left_col, right_col = st.columns([2, 1])
with left_col:
    st.subheader("🧠 Selbst-Reflexion des Bots")
    if isinstance(chat, list):
        sys_msgs = [m for m in chat if m.get("role") == "system" and "📘" in m.get("content", "")]
        if sys_msgs: st.info(sys_msgs[-1].get("content", ""))
        else: st.write("Der Bot wertet gerade seine Trades aus...")

    st.subheader("📊 Aktive Positionen")
    active = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    if active:
        for pos in active:
            with st.expander(f"📈 {pos.get('Vermögenswert')} – {pos.get('Richtung')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Einstieg", f"${pos.get('Eintrittspreis')}")
                c2.metric("Stop-Loss", f"${pos.get('Stop_Loss_Preis')}", delta_color="inverse")
                c3.metric("Take-Profit", f"${pos.get('Take_Profit_Preis')}")
                target = float(pos.get('target_price') or 0.0)
                st.markdown(f"🎯 Erwartetes Kursziel: ${target:,.2f}")
    else: st.success("✅ Keine offenen Positionen.")

with right_col:
    st.subheader("💬 Live-Diskurs")
    chat_container = st.container(height=400)
    with chat_container:
        if isinstance(chat, list):
            sorted_chat = sorted(chat, key=lambda x: x.get('id', 0), reverse=True)[:15]
            for msg in reversed(sorted_chat):
                role, content = msg.get("role"), msg.get("content", "")
                if role == "system": st.markdown(f"<span style='color:#ffcc00;'>🧠 {content}</span>", unsafe_allow_html=True)
                elif role == "user": st.markdown(f"<span style='color:#4da6ff;'>🧑‍💻 {content}</span>", unsafe_allow_html=True)
                elif role == "assistant": st.markdown(f"<span style='color:#00ff66;'>🤖 {content}</span>", unsafe_allow_html=True)

st.markdown("---")
prompt = st.chat_input("Befehl an den Broker...", key="broker_input")
if prompt:
    if send_chat_message("user", prompt):
        st.success("✅ Gesendet"); st.cache_data.clear(); st.rerun()

st.caption("⚙️ Modus: Learning-Cockpit | 24/7 Selbstreflektion aktiv")
