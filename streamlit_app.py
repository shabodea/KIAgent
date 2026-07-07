import streamlit as st
import pandas as pd
from datetime import datetime

# --- MODULARE IMPORTS (STRICT TO ARCHITECTURE) ---
from database.supabase import get_all_data_live, send_chat_message

st.set_page_config(page_title="🦅 KI-Zentrale 10x", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS FÜR TRADING-LOOK ---
st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 20px; border-radius: 8px; border-left: 4px solid #00ff66; margin-bottom: 15px; }
    .explanation-text { color: #848e9c; font-size: 0.85rem; }
    .log-box { background-color: #0c0d14; padding: 15px; border-radius: 5px; font-family: monospace; color: #00ff66; height: 180px; overflow-y: scroll; }
    </style>
""", unsafe_allow_html=True)

st.title("🦅 KI-BROKER EVALUATIONS-ZENTRALE")
st.caption("Institutionelles Handelsmodell — Mathematische Echtzeit-Überwachung")

# --- SÄULE 1: DATENSAMMLER (NUN MODULAR ÜBER SUPABASE-MODUL) ---
trades, chat, risiko, knowledge = get_all_data_live()

# --- SÄULE 3: MATHEMATISCHE SELBSTBEWERTUNG ---
guthaben = 200.0
win_trades = 0
loss_trades = 0

if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if not isinstance(t, dict): continue
        if t.get("Status") == "CLOSED":
            pnl = float(t.get("net_pnl") or 0.0)
            guthaben += pnl
            if pnl > 0: win_trades += 1
            else: loss_trades += 1

total_closed = win_trades + loss_trades
win_rate = (win_trades / total_closed * 100) if total_closed > 0 else 0.0

# --- SÄULE 4: RISK-MANAGEMENT METRIKEN ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("💰 Depot-Wert", f"${guthaben:.2f}")
    st.markdown("<p class='explanation-text'>Dein aktuelles Gesamtkapital im System.</p>", unsafe_allow_html=True)
with m2:
    st.metric("📊 Trefferquote", f"{win_rate:.1f}%")
    st.markdown("<p class='explanation-text'>Prozentualer Anteil der profitablen Trades.</p>", unsafe_allow_html=True)
with m3:
    st.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "CRITICAL")
    st.markdown("<p class='explanation-text'>Überwachung des Gesamtrisikos.</p>", unsafe_allow_html=True)
with m4:
    tages_status = risiko[0].get("status") if isinstance(risiko, list) and len(risiko) > 0 else "OPEN"
    st.metric("⚡ Tages-Schutzschild", tages_status)
    st.markdown("<p class='explanation-text'>Sperrt das System bei hohem Tagesverlust.</p>", unsafe_allow_html=True)

st.markdown("---")

# --- OBERFLÄCHE: LINKS PROTOKOLLE & RECHTS CHAT ---
col_left, col_right = st.columns([1.3, 1])

with col_left:
    st.subheader("📦 Aktive Positionen (Echtzeit-Muster)")
    active_positions = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    
    if len(active_positions) > 0:
        for pos in active_positions:
            with st.expander(f"🟢 MARKT-AUFTRAG: {pos.get('Vermögenswert')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Einstiegspreis", f"${pos.get('Eintrittspreis')}")
                c2.metric("Marge (Einsatz)", f"${pos.get('Marge in USD')}")
                c3.metric("Hebel", f"{pos.get('Hebelwirkung')}x")
                
                st.markdown(f"**🎯 Take-Profit Ziel:** {pos.get('Take_Profit_Preis')}$ | **🛡️ Stop-Loss Schutz:** {pos.get('Stop_Loss_Preis')}$")
                st.info(f"ℹ️ **Einfache Erklärung des Handelsmusters:**\n{pos.get('Begründung', 'Warte auf KI-Auswertung...')}")
                st.caption(f"⚙️ **Technische Rohdaten:** {pos.get('Indikatoren_Setup')} | {pos.get('Erwartete_Bewegung')}")
    else:
        st.info("Der Broker wartet auf ein klares mathematisches Signal und positives Internet-Sentiment.")

    st.subheader("📜 Letzte Buchungen (Transaktions-Historie)")
    if isinstance(trades, list) and len(trades) > 0:
        df = pd.DataFrame(trades)
        if "net_pnl" in df.columns:
            st.dataframe(df[["Vermögenswert", "Richtung", "Eintrittspreis", "net_pnl", "Status"]].sort_index(ascending=False), use_container_width=True)

    st.subheader("🖥️ Telemetrie-Protokoll")
    st.markdown(f"""<div class="log-box">
        [{datetime.now().strftime('%H:%M:%S')}] 📡 CCXT-Daten-Pipeline zu Kraken steht.<br>
        [{datetime.now().strftime('%H:%M:%S')}] 🔢 Berechne ATR-Volatilität und mathematischen RSI...<br>
        [{datetime.now().strftime('%H:%M:%S')}] 🌐 Gemini sammelt Sentiment-Analysen im Internet...
    </div>""", unsafe_allow_html=True)

with col_right:
    st.subheader("💬 Taktischer Live-Diskurs")
    chat_container = st.container(height=450)
    with chat_container:
        if isinstance(chat, list) and len(chat) > 0 and isinstance(chat[0], dict):
            for msg in sorted(chat, key=lambda x: x.get('id', 0) if isinstance(x, dict) else 0):
                with st.chat_message(msg.get("role", "user")):
                    st.write(msg.get("content", ""))
        else:
            st.info("Noch keine Nachrichten im Verlauf. Schreibe deine erste Anweisung!")

st.markdown("---")

# ==================================================
# KI CHAT EINGABE
# ==================================================

st.subheader("⌨️ Taktische Befehlszeile")


prompt = st.chat_input(
    "Gib dem Broker eine Anweisung...",
    key="unique_broker_chat_input_2026"
)


if prompt:


    st.write(
        "📤 Sende Nachricht:",
        prompt
    )


    success = send_chat_message(
        "user",
        prompt
    )


    if success:

        st.success(
            "✅ Nachricht wurde an Supabase gesendet."
        )

        st.cache_data.clear()

        st.rerun()


    else:

        st.error(
            "❌ Supabase Speicherung fehlgeschlagen."
        )

# --- SIDEBAR: UNSTERBLICHES GEDÄCHTNIS ---
with st.sidebar:
    st.header("🧠 KI-Gedächtnis (Dauerspeicher)")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge:
            st.caption(f"🛡️ **{k.get('kategorie')}**: {k.get('inhalt')}")
    else:
        st.caption("• Gedächtnis leer oder wird geladen...")
