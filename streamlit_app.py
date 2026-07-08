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

MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRX-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "NIGHT-USD"  
]

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
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
                        rsi = calculate_rsi([c[4] for c in ohlcv])
                        sig = "LONG" if rsi < 30 else ("SHORT" if rsi > 70 else "WARTEN")
                        row[f"{tf}_RSI"] = f"{rsi:.1f}"
                        row[f"{tf}_Sig"] = sig
                    else:
                        row[f"{tf}_RSI"] = "N/A"
                        row[f"{tf}_Sig"] = "N/A"
                except:
                    row[f"{tf}_RSI"] = "N/A"
                    row[f"{tf}_Sig"] = "N/A"
            results.append(row)
    except: pass
    return pd.DataFrame(results) if results else pd.DataFrame()

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
col4.metric("⚡ Hebel", "10x FIX")

st.markdown("---")

# --- MARKTÜBERSICHT ---
st.subheader(f"📊 Live-Übersicht (Alle Assets & Signale)")
df_market = get_market_overview(MONITORED_ASSETS)
if not df_market.empty:
    st.dataframe(df_market, use_container_width=True, hide_index=True, height=600)
else:
    st.info("Marktdaten werden geladen...")

st.markdown("---")
left_col, right_col = st.columns([2, 1])

with left_col:
    st.subheader("🧠 Selbst-Reflexion des Bots")
    if isinstance(chat, list):
        # Zeige die neueste System-Nachricht, die eine Selbstreflexion (🤔) enthält
        sys_msgs = [m for m in chat if m.get("role") == "system" and "🤔" in m.get("content", "")]
        if sys_msgs:
            st.info(sys_msgs[-1].get("content", ""))
        else:
            st.write("Der Bot wertet gerade seine Trades aus...")

    st.subheader("📊 Aktive Positionen (mit Prognosen)")
    active = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    if active:
        for pos in active:
            with st.expander(f"📈 {pos.get('Vermögenswert')} – {pos.get('Richtung')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Einstieg", f"${pos.get('Eintrittspreis')}")
                c2.metric("Stop-Loss", f"${pos.get('Stop_Loss_Preis')}", delta_color="inverse")
                c3.metric("Take-Profit", f"${pos.get('Take_Profit_Preis')}")
                
                # WICHTIG: Target-Preis anzeigen
                target = float(pos.get('target_price') or 0.0)
                if target > 0:
                    st.markdown(f"🎯 **Erwartetes Kursziel:** ${target:,.2f}")
                else:
                    st.markdown(f"🎯 **Erwartetes Kursziel:** *Wird vom Bot berechnet...*")
                st.info(f"💡 Begründung: {pos.get('Begründung', 'Analyse läuft...')}")
    else:
        st.success("✅ Keine offenen Positionen.")

    st.subheader("📜 Geschlossene Trades (Lern-Tabelle)")
    closed = [t for t in trades if isinstance(t, dict) and t.get("Status") == "CLOSED"]
    if closed:
        df = pd.DataFrame(closed)
        # Logik für die Prognose-Qualität
        if "target_price" in df.columns and "Austrittspreis" in df.columns:
            df['Prognose erfüllt?'] = df.apply(
                lambda row: "✅ JA" if abs(float(row.get('Austrittspreis', 0)) - float(row.get('target_price', 0))) < 1.0 else "❌ NEIN",
                axis=1
            )
            cols = ["Vermögenswert", "Richtung", "Eintrittspreis", "target_price", "Austrittspreis", "net_pnl", "Prognose erfüllt?"]
            available_cols = [c for c in cols if c in df.columns]
            st.dataframe(df[available_cols].sort_index(ascending=False), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.caption("Noch keine abgeschlossenen Trades in der Historie.")

with right_col:
    st.subheader("💬 Live-Diskurs")
    chat_container = st.container(height=400)
    with chat_container:
        if isinstance(chat, list):
            sorted_chat = sorted(chat, key=lambda x: x.get('id', 0), reverse=True)[:15]
            for msg in reversed(sorted_chat):
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "system":
                    st.markdown(f"<span style='color:#ffcc00;'>🧠 {content}</span>", unsafe_allow_html=True)
                elif role == "user":
                    st.markdown(f"<span style='color:#4da6ff;'>🧑‍💻 {content}</span>", unsafe_allow_html=True)
                elif role == "assistant":
                    st.markdown(f"<span style='color:#00ff66;'>🤖 {content}</span>", unsafe_allow_html=True)

st.markdown("---")
prompt = st.chat_input("Befehl an den Broker...", key="broker_input")
if prompt:
    if send_chat_message("user", prompt):
        st.success("✅ Gesendet")
        st.cache_data.clear()
        st.rerun()

st.caption("⚙️ Modus: Learning-Cockpit | 24/7 Selbstreflektion aktiv")
