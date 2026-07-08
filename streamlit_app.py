import streamlit as st
import pandas as pd
from datetime import datetime
import ccxt
import numpy as np
from database.supabase import get_all_data_live, send_chat_message

st.set_page_config(page_title="🦅 10x KI-Profi-Cockpit", layout="wide", initial_sidebar_state="expanded")

# --- CSS (für die schönen farbigen Karten) ---
st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 18px; border-radius: 10px; border-left: 5px solid #00ff66; margin-bottom: 15px; }
    .signal-box { padding: 6px 10px; border-radius: 5px; text-align: center; font-weight: bold; font-size: 0.85rem; margin-bottom: 2px;}
    .signal-long { background-color: #1a3b1a; color: #00ff66; border: 1px solid #00ff66; }
    .signal-short { background-color: #3b1a1a; color: #ff4d4d; border: 1px solid #ff4d4d; }
    .signal-wait { background-color: #2a2a2a; color: #888888; border: 1px solid #888888; }
    .rsi-text { font-size: 0.75rem; color: #848e9c; text-align: center; }
    .asset-row { background-color: #0e1117; padding: 10px 0; border-bottom: 1px solid #262730; }
    </style>
""", unsafe_allow_html=True)

# --- DEINE 19 KRAKEN-ASSETS ---
MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRX-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "NIGHT-USD"
]

TIMEFRAMES = ['5m', '15m', '1h', '4h', '1d']

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0:
        return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

# --- FEHLERTOLERANTE DATENABFRAGE ---
def get_market_overview(assets):
    results = []
    try:
        exchange = ccxt.kraken()
        for symbol in assets:
            row = {"Asset": symbol, "Kurs": "Fehler", "Orderbuch": "N/A"}
            for tf in TIMEFRAMES:
                row[f"{tf}_RSI"] = "N/A"
                row[f"{tf}_Sig"] = "N/A"

            try:
                ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
                row["Kurs"] = f"${ticker['last']:,.2f}"
                
                # Orderbuch (Unterstützung / Widerstand)
                try:
                    orderbook = exchange.fetch_order_book(symbol.replace("-", "/"), limit=3)
                    bids = orderbook['bids'][0][0] if orderbook['bids'] else 0
                    asks = orderbook['asks'][0][0] if orderbook['asks'] else 0
                    row["Orderbuch"] = f"Stütze: ${bids:,.2f} | Widerstand: ${asks:,.2f}"
                except:
                    row["Orderbuch"] = "Orderbuch nicht verfügbar"

                # RSIs für alle 5 Zeitfenster
                for tf in TIMEFRAMES:
                    try:
                        ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=tf, limit=50)
                        if ohlcv:
                            rsi = calculate_rsi([c[4] for c in ohlcv])
                            sig = "LONG" if rsi < 30 else ("SHORT" if rsi > 70 else "WARTEN")
                            row[f"{tf}_RSI"] = f"{rsi:.1f}"
                            row[f"{tf}_Sig"] = sig
                    except:
                        pass # Bei Fehlern bleibt N/A erhalten
            except:
                pass # Bei Asset-Fehlern bleibt Zeile mit "Fehler" erhalten

            results.append(row)
    except Exception as e:
        st.error(f"Kraken-Verbindungsfehler: {e}")
        return pd.DataFrame()

    return pd.DataFrame(results)


trades, chat, risiko, knowledge = get_all_data_live()

# --- METRIKEN ---
guthaben = 200.0
win_trades = 0
loss_trades = 0
if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if isinstance(t, dict) and t.get("Status") == "CLOSED":
            pnl = float(t.get("net_pnl") or 0.0)
            guthaben += pnl
            if pnl > 0:
                win_trades += 1
            else:
                loss_trades += 1
total = win_trades + loss_trades
win_rate = (win_trades / total * 100) if total > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Depotwert", f"${guthaben:.2f}")
col2.metric("📊 Trefferquote", f"{win_rate:.1f}%")
col3.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "KRITISCH")
col4.metric("⚡ Hebel", "10x FIX")

st.markdown("---")

# --- DASHBOARD: ZEILENWEISE ANZEIGE (WIE DU ES LIEBST) ---
st.subheader(f"🔥 Live-Marktübersicht ({len(MONITORED_ASSETS)} Assets)")

df_market = get_market_overview(MONITORED_ASSETS)

if df_market.empty:
    st.warning("Marktdaten werden noch geladen oder Kraken ist kurzzeitig nicht erreichbar...")
else:
    # Kopfzeile für die Tabelle (visualisiert)
    header_cols = st.columns([2, 2, 1.3, 1.3, 1.3, 1.3, 1.3, 3])
    header_cols[0].markdown("**Asset**")
    header_cols[1].markdown("**Kurs**")
    for i, tf in enumerate(TIMEFRAMES):
        header_cols[2+i].markdown(f"**{tf}**")
    header_cols[-1].markdown("**Orderbuch**")

    # Assets durchgehen und Zeilen zeichnen
    for _, row in df_market.iterrows():
        cols = st.columns([2, 2, 1.3, 1.3, 1.3, 1.3, 1.3, 3])
        cols[0].write(f"**{row['Asset']}**")
        cols[1].write(row['Kurs'])

        # Zeitfenster-Karten generieren
        for i, tf in enumerate(TIMEFRAMES):
            sig = row[f"{tf}_Sig"]
            rsi = row[f"{tf}_RSI"]
            
            # CSS-Klasse bestimmen
            if sig == "LONG":
                cls = "signal-long"
            elif sig == "SHORT":
                cls = "signal-short"
            else:
                cls = "signal-wait"

            cols[2+i].markdown(f"""
                <div class='signal-box {cls}'>{sig}</div>
                <div class='rsi-text'>RSI {rsi}</div>
            """, unsafe_allow_html=True)
        
        cols[-1].caption(row['Orderbuch'])

st.markdown("---")

# --- UNTERER BEREICH ---
left_col, right_col = st.columns([2, 1])
with left_col:
    st.subheader("🧠 Live-Denkprotokoll")
    if isinstance(chat, list):
        sys_msgs = [m for m in chat if m.get("role") == "system"]
        if sys_msgs:
            st.markdown(f"<div style='background:#0c0d14; padding:15px; border-radius:8px; height:200px; overflow-y:scroll;'>{sys_msgs[-1].get('content', '')}</div>", unsafe_allow_html=True)
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
                st.caption(f"⚙️ Marge: ${pos.get('Marge in USD', 0):.2f} | Hebel: {pos.get('Hebelwirkung', 1)}x")
    else:
        st.success("✅ Keine offenen Positionen.")

with right_col:
    st.subheader("💬 Live-Diskurs")
    chat_container = st.container(height=300)
    with chat_container:
        if isinstance(chat, list):
            sorted_chat = sorted(chat, key=lambda x: x.get('id', 0), reverse=True)[:10]
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
        st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🧠 KI-Gedächtnis")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge:
            st.caption(f"📌 **{k.get('kategorie')}**: {k.get('inhalt')}")
    st.caption("⚙️ Status: LIVE | 10x Hebel | 19 Assets")
