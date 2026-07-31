import os
import streamlit as st

# WICHTIG: Streamlit Cloud Secrets landen in st.secrets, NICHT automatisch in
# os.environ. config/settings.py liest aber os.getenv(...) -> hier einmalig
# bruecken, BEVOR irgendetwas aus database/config importiert wird.
for _k, _v in st.secrets.items():
    os.environ.setdefault(_k, str(_v))

import pandas as pd
from database.supabase import (
    get_all_data_live, send_chat_message, get_bot_thoughts,
    get_market_snapshot, get_current_balance_and_winrate,
)
from config.settings import MAX_TOTAL_BUDGET_USD

st.set_page_config(page_title="🦅 KI-Learning-Cockpit", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 18px; border-radius: 10px; border-left: 5px solid #00ff66; margin-bottom: 15px; }
    .hit { color: #00ff66; font-weight: bold; }
    .miss { color: #ff4d4d; font-weight: bold; }
    .dataframe th { background-color: #1e222d !important; color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# --- Live-Daten laden (alles kommt aus Supabase, keine eigenen Kraken-Anfragen mehr) ---
trades, chat, risiko, knowledge = get_all_data_live()
balance, win_rate_frac, total_closed = get_current_balance_and_winrate(base_balance=MAX_TOTAL_BUDGET_USD)
win_rate = win_rate_frac * 100

exploration_trades = sum(
    1 for t in trades if isinstance(t, dict) and "Exploration" in str(t.get("Erwartete_Bewegung", ""))
)

dynamic_risk = max(0.5, min(3.0, (2 * win_rate_frac - 1) * 5))
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💰 Depotwert", f"${balance:.2f}")
col2.metric("📊 Trefferquote", f"{win_rate:.1f}%", help=f"Basis: letzte {total_closed} geschlossene Trades")
col3.metric("🛡️ Risiko-Status", "NORMAL" if balance > MAX_TOTAL_BUDGET_USD * 0.9 else "KRITISCH")
col4.metric("⚡ Dynamisches Risiko", f"{dynamic_risk:.1f}%", help="Prozentsatz des Guthabens pro regulärem Trade")
col5.metric("🧪 Explorations-Trades", exploration_trades, help="Bewusst schwächere Signale, um mehr Trainingsdaten zu sammeln")
st.markdown("---")

# --- PROFI-LIVE-ÜBERSICHT: für jedes Asset die aktuelle Einschätzung über alle Zeitfenster ---
st.subheader("📊 Live-Marktübersicht: Halten / Kaufen (Long) / Verkaufen (Short)")
snapshot = get_market_snapshot()

if snapshot:
    rows = []
    for s in snapshot:
        direction = s.get("direction", "HOLD")
        label = {"BUY": "🟢 LONG", "SELL": "🔴 SHORT", "HOLD": "🟠 HALTEN"}.get(direction, direction)
        conf = float(s.get("confidence") or 0.0)
        rows.append({
            "Asset": s.get("symbol"),
            "Preis": f"${float(s.get('last_price') or 0):,.4f}",
            "Signal": label,
            "Konfidenz": conf,
            "5m RSI": s.get("rsi_5m"),
            "15m RSI": s.get("rsi_15m"),
            "1h RSI": s.get("rsi_1h"),
            "4h RSI": s.get("rsi_4h"),
            "1d RSI": s.get("rsi_1d"),
            "Begründung": s.get("reasons", ""),
            "_sort": conf if direction != "HOLD" else -1,
        })

    df_live = pd.DataFrame(rows).sort_values("_sort", ascending=False).drop(columns=["_sort"])
    df_live["Konfidenz"] = df_live["Konfidenz"].apply(lambda x: f"{x*100:.0f}%")

    def highlight_signal(val):
        if "LONG" in str(val): return "background-color: #1a3b1a; color: #00ff66; font-weight: bold;"
        if "SHORT" in str(val): return "background-color: #3b1a1a; color: #ff4d4d; font-weight: bold;"
        if "HALTEN" in str(val): return "background-color: #2a2a2a; color: #ffcc00;"
        return ""

    styled = df_live.style.map(highlight_signal, subset=["Signal"])
    st.dataframe(styled, use_container_width=True, hide_index=True, height=650)
    st.caption("Sortiert nach Konfidenz. Diese Tabelle kommt direkt aus dem Worker (kein Live-Nachladen nötig) und aktualisiert sich bei jedem Seiten-Refresh.")
else:
    st.info("Noch keine Live-Übersicht vorhanden – der Worker schreibt sie bei der ersten Analyserunde (kann 1-2 Minuten nach dem Start dauern).")

st.markdown("---")

left_col, right_col = st.columns([2, 1])
with left_col:
    st.subheader("🧠 Denkprotokoll (letzte Analysen, chronologisch)")
    thoughts = get_bot_thoughts(limit=20)
    if thoughts:
        for t in thoughts:
            direction = t.get("direction", "HOLD")
            color = {"BUY": "#00ff66", "SELL": "#ff4d4d", "HOLD": "#ffcc00"}.get(direction, "#ffffff")
            conf = float(t.get("confidence") or 0.0)
            st.markdown(
                f"<span style='color:{color};'>**{t.get('symbol')}** → {direction} ({conf*100:.0f}%)</span> "
                f"– {t.get('reasons','')}",
                unsafe_allow_html=True,
            )
    else:
        st.write("Noch keine Einträge im Denkprotokoll.")

    st.subheader("📈 Trefferquote-Verlauf")
    closed_sorted = [t for t in trades if isinstance(t, dict) and t.get("Status") == "CLOSED"]
    closed_sorted.sort(key=lambda x: x.get("id", 0))
    if closed_sorted:
        rolling, wins_running = [], 0
        for i, t in enumerate(closed_sorted, start=1):
            if float(t.get("net_pnl") or 0.0) > 0:
                wins_running += 1
            rolling.append(wins_running / i)
        st.line_chart(rolling)
    else:
        st.info("Noch keine geschlossenen Trades für den Trefferquote-Verlauf.")

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
                st.markdown(f"🎯 Erwartetes Kursziel: ${target:,.2f} | Modus: {pos.get('Erwartete_Bewegung', '-')}")
    else:
        st.success("✅ Keine offenen Positionen.")

with right_col:
    st.subheader("🧠 Selbst-Reflexion des Bots")
    if isinstance(chat, list):
        sys_msgs = [m for m in chat if m.get("role") == "system" and "📘" in m.get("content", "")]
        if sys_msgs:
            st.info(sys_msgs[-1].get("content", ""))
        else:
            st.write("Der Bot wertet gerade seine Trades aus...")

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

st.caption("⚙️ Modus: Learning-Cockpit | 24/7 Analyse + Explorations-Modus aktiv")
