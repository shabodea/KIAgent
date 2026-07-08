import streamlit as st
import pandas as pd
from datetime import datetime
import ccxt
import numpy as np
import yfinance as yf
from database.supabase import get_all_data_live, send_chat_message

st.set_page_config(page_title="🦅 KI-Profi-Trading-Cockpit (Multi-Timeframe)", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 18px; border-radius: 10px; border-left: 5px solid #00ff66; margin-bottom: 15px; }
    .thought-box { background-color: #0c0d14; padding: 20px; border-radius: 8px; border: 1px solid #333; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; height: 250px; overflow-y: scroll; }
    .system_msg { color: #ffcc00; }
    .user_msg { color: #4da6ff; }
    .assistant_msg { color: #00ff66; }
    </style>
""", unsafe_allow_html=True)

# --- AKTUALISIERTE ASSET-LISTE (INKL. TAO & MIDNIGHT) ---
MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRON-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "CHAINLINK-USD", "SUI-USD", "NILLION-USD", "TAO-USD", "MIDNIGHT-USD", 
    "SPCE", "GOOGL", "NVDA", "MRVL", "ORCL"
]
TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]

# --- HELFER: RSI BERECHNEN ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

# --- ROBUSTE DATENABFRAGE (AKTIEN + KRYPTO) ---
def fetch_data_robust(symbol, tf):
    # Aktien (mit 3-stufigem Fallback)
    if symbol in ["SPCE", "GOOGL", "NVDA", "MRVL", "ORCL"]:
        try:
            data = yf.download(symbol, period="1d", interval=tf, progress=False)
            if data.empty:
                # Fallback: 5m -> 15m -> 1h
                if tf == "5m":
                    data = yf.download(symbol, period="1d", interval="15m", progress=False)
                if data.empty:
                    data = yf.download(symbol, period="5d", interval="1h", progress=False)
            if data.empty:
                return None
            closes = data['Close'].tolist()
            volume = data['Volume'].iloc[-1]
            vol_prev = data['Volume'].iloc[-2] if len(data) > 1 else volume
            return closes, volume, vol_prev
        except:
            return None
    # Krypto (CCXT)
    else:
        try:
            exchange = ccxt.kraken()
            # Aufpassen: TAO/USD ist auf Kraken verfügbar
            ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=tf, limit=50)
            if not ohlcv: return None
            closes = [c[4] for c in ohlcv]
            volume = ohlcv[-1][5]
            vol_prev = ohlcv[-2][5] if len(ohlcv) > 1 else volume
            return closes, volume, vol_prev
        except:
            return None

# --- MARKTÜBERSICHT ZUSAMMENBAUEN ---
@st.cache_data(ttl=30)
def get_market_overview_multi_tf(assets):
    results = []
    for symbol in assets:
        row = {"Symbol": symbol}
        signals = []
        try:
            for tf in TIMEFRAMES:
                data = fetch_data_robust(symbol, tf)
                if data:
                    closes, vol, vol_prev = data
                    rsi = calculate_rsi(closes)
                    sig = "BUY" if rsi < 30 else ("SELL" if rsi > 70 else "HOLD")
                    vol_trend = "📈 Steigend" if vol > vol_prev else "📉 Fallend"
                    row[f"{tf}_Sig"] = sig
                    row[f"{tf}_Vol"] = vol_trend
                    signals.append(sig)
                else:
                    row[f"{tf}_Sig"] = "N/A"
                    row[f"{tf}_Vol"] = "N/A"
                    signals.append("HOLD")
            
            buy_cnt = signals.count("BUY")
            sell_cnt = signals.count("SELL")
            if buy_cnt >= 4: feedback = "🟢 Stark Kaufsignal"
            elif buy_cnt >= 2: feedback = "🟡 Kaufneigung"
            elif sell_cnt >= 4: feedback = "🔴 Stark Verkaufssignal"
            elif sell_cnt >= 2: feedback = "🟡 Verkaufsneigung"
            else: feedback = "⚪ Uneinheitlich"
            
            row["Gesamt-Feedback"] = feedback
            results.append(row)
        except:
            continue
    return pd.DataFrame(results) if results else pd.DataFrame()

# --- DATEN ABRUFEN ---
trades, chat, risiko, knowledge = get_all_data_live()

# --- METRIKEN ---
guthaben = 200.0
win_trades, loss_trades = 0, 0
if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if isinstance(t, dict) and t.get("Status") == "CLOSED":
            pnl = float(t.get("net_pnl") or 0.0)
            guthaben += pnl
            if pnl > 0: win_trades += 1
            else: loss_trades += 1
total = win_trades + loss_trades
win_rate = (win_trades / total * 100) if total > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Depotwert", f"${guthaben:.2f}")
col2.metric("📊 Trefferquote", f"{win_rate:.1f}%")
col3.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "KRITISCH")
col4.metric("⚡ Schutzschild", risiko[0].get("status") if isinstance(risiko, list) and len(risiko) > 0 else "OFFEN")

st.markdown("---")

# --- TABELLE ANZEIGEN ---
st.subheader(f"📊 Live-Marktübersicht ({len(MONITORED_ASSETS)} Assets)")
df_market = get_market_overview_multi_tf(MONITORED_ASSETS)

if not df_market.empty:
    def highlight_signals(val):
        if "BUY" in str(val): return "color: #00ff66; font-weight: bold;"
        elif "SELL" in str(val): return "color: #ff4d4d; font-weight: bold;"
        elif "HOLD" in str(val): return "color: #888888;"
        return ""
    st.dataframe(
        df_market.style.map(highlight_signals, subset=[f"{tf}_Sig" for tf in TIMEFRAMES]),
        use_container_width=True,
        hide_index=True,
        height=600
    )
else:
    st.info("Marktdaten werden geladen (bitte 1 Minute warten)...")

st.markdown("---")

# --- REST (GEDANKEN, HANDELSPLATZ, CHAT) ---
left_col, right_col = st.columns([2, 1])
with left_col:
    st.subheader("🧠 Live-Denkprotokoll")
    if isinstance(chat, list):
        sys_msgs = [m for m in chat if m.get("role") == "system"]
        if sys_msgs:
            st.markdown(f"<div class='thought-box'>{sys_msgs[-1].get('content', '')}</div>", unsafe_allow_html=True)
        else:
            st.info("Der Bot denkt noch...")

    st.subheader("📊 Handelsplatz – Aktive Positionen")
    active = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    if active:
        for pos in active:
            with st.expander(f"📈 {pos.get('Vermögenswert')} – {pos.get('Richtung')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Einstieg", f"${pos.get('Eintrittspreis')}")
                c2.metric("Stop-Loss", f"${pos.get('Stop_Loss_Preis')}", delta_color="inverse")
                c3.metric("Take-Profit", f"${pos.get('Take_Profit_Preis')}")
                st.info(f"💡 Begründung: {pos.get('Begründung', '...')}")
    else:
        st.success("✅ Keine offenen Positionen.")

with right_col:
    st.subheader("💬 Live-Diskurs")
    chat_container = st.container(height=350)
    with chat_container:
        if isinstance(chat, list):
            sorted_chat = sorted(chat, key=lambda x: x.get('id', 0), reverse=True)[:10]
            for msg in reversed(sorted_chat):
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "system":
                    st.markdown(f"<div class='system_msg'>🧠 <b>BOT:</b> {content}</div>", unsafe_allow_html=True)
                elif role == "user":
                    st.markdown(f"<div class='user_msg'>🧑‍💻 <b>Du:</b> {content}</div>", unsafe_allow_html=True)
                elif role == "assistant":
                    st.markdown(f"<div class='assistant_msg'>🤖 <b>KI:</b> {content}</div>", unsafe_allow_html=True)

st.markdown("---")
prompt = st.chat_input("Befehl an den Broker...", key="broker_input")
if prompt:
    if send_chat_message("user", prompt):
        st.success("✅ Gesendet")
        st.cache_data.clear()
        st.rerun()

with st.sidebar:
    st.header("🧠 KI-Gedächtnis")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge: st.caption(f"📌 **{k.get('kategorie')}**: {k.get('inhalt')}")
    st.caption("⚙️ Status: LIVE | 24/7 | Multi-Asset")
