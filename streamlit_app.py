import streamlit as st
import pandas as pd
from datetime import datetime
from database.supabase import get_all_data_live, send_chat_message

st.set_page_config(page_title="🦅 KI-Profi-Trading-Cockpit", layout="wide", initial_sidebar_state="expanded")

# Custom CSS für Profi-Look
st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 18px; border-radius: 10px; border-left: 5px solid #00ff66; margin-bottom: 15px; }
    .metric-value { font-size: 1.6rem; font-weight: bold; color: #ffffff; }
    .metric-label { color: #848e9c; font-size: 0.9rem; }
    .thought-box { background-color: #0c0d14; padding: 20px; border-radius: 8px; border: 1px solid #333; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; height: 250px; overflow-y: scroll; margin-bottom: 20px; }
    .step-item { margin-bottom: 8px; display: flex; gap: 10px; }
    .step-num { color: #00ff66; font-weight: bold; }
    .trade-table { font-size: 0.9rem; }
    .chat-container { border: 1px solid #333; border-radius: 8px; padding: 10px; background-color: #0c0d14; height: 300px; overflow-y: scroll; margin-bottom: 10px; }
    .system_msg { color: #ffcc00; }
    .user_msg { color: #4da6ff; }
    .assistant_msg { color: #00ff66; }
    </style>
""", unsafe_allow_html=True)

st.title("🦅 KI-BROKER PROFESSIONAL COCKPIT")
st.caption("Autonomer KI-Trading-Agent 24/7 – Echtzeit-Denkprotokoll & Paper-Trading")

# --- DATEN ABRUFEN ---
trades, chat, risiko, knowledge = get_all_data_live()

# --- 1. METRIKEN ---
guthaben = 200.0
win_trades = 0
loss_trades = 0
if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if isinstance(t, dict) and t.get("Status") == "CLOSED":
            pnl = float(t.get("net_pnl") or 0.0)
            guthaben += pnl
            if pnl > 0: win_trades += 1
            else: loss_trades += 1
total_closed = win_trades + loss_trades
win_rate = (win_trades / total_closed * 100) if total_closed > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Depotwert", f"${guthaben:.2f}", help="Aktuelles Gesamtkapital im Paper-Modus")
col2.metric("📊 Trefferquote", f"{win_rate:.1f}%", help="Gewinnende Trades im Verhältnis zu Verlusten")
col3.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "KRITISCH", help="Überwachung der Gesamtrisikolage")
col4.metric("⚡ Schutzschild", risiko[0].get("status") if isinstance(risiko, list) and len(risiko) > 0 else "OFFEN", help="Sperrt Trades bei hohem Tagesverlust")

st.markdown("---")

# --- 2. HAUPTLAYOUT: ZWEI SPALTEN ---
left_col, right_col = st.columns([2, 1])

with left_col:
    # --- BOT DENKPROTOKOLL ---
    st.subheader("🧠 Live-Denkprotokoll des KI-Bots")
    thought_container = st.container(height=260)
    with thought_container:
        # Suche nach der neuesten System-Nachricht (das sind die Gedanken des Bots)
        bot_thoughts = []
        if isinstance(chat, list):
            # Filtere nur Systemnachrichten
            system_msgs = [m for m in chat if m.get("role") == "system"]
            if system_msgs:
                last_thought = system_msgs[-1].get("content", "")
                # Zeige die Gedanken strukturiert an, falls sie als Liste geschrieben wurden
                st.markdown(f"<div class='thought-box'>{last_thought}</div>", unsafe_allow_html=True)
            else:
                st.info("🤖 Der Bot denkt gerade über die nächste Marktanalyse nach... (Noch keine Live-Gedanken verfügbar)")

    # --- AKTIVE POSITIONEN ---
    st.subheader("📊 Handelsplatz – Aktive Positionen")
    active = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    if active:
        for pos in active:
            with st.expander(f"📈 {pos.get('Vermögenswert')} – {pos.get('Richtung')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Einstiegspreis", f"${pos.get('Eintrittspreis')}")
                c2.metric("Stop-Loss", f"${pos.get('Stop_Loss_Preis')}", delta_color="inverse")
                c3.metric("Take-Profit", f"${pos.get('Take_Profit_Preis')}")
                
                # Laienverständliche Begründung
                st.info(f"💡 **Warum hat der Bot diesen Trade eröffnet?**\n{pos.get('Begründung', 'Analyse läuft...')}")
                st.caption(f"⚙️ Indikatoren: {pos.get('Indikatoren_Setup', 'Warte auf Daten')} | 🎯 Erwartete Bewegung: {pos.get('Erwartete_Bewegung', '–')}")
    else:
        st.success("✅ Keine offenen Positionen. Der Bot wartet geduldig auf ein profitables Setup.")

    # --- LETZTE BUCHUNGEN ---
    st.subheader("📜 Letzte abgeschlossene Trades")
    closed = [t for t in trades if isinstance(t, dict) and t.get("Status") == "CLOSED"]
    if closed:
        df = pd.DataFrame(closed)
        cols = ["Vermögenswert", "Richtung", "Eintrittspreis", "Take_Profit_Preis", "net_pnl", "Begründung"]
        available_cols = [c for c in cols if c in df.columns]
        st.dataframe(df[available_cols].sort_index(ascending=False), use_container_width=True, hide_index=True)
    else:
        st.caption("Noch keine abgeschlossenen Trades in der Historie.")

with right_col:
    # --- TAKTISCHER LIVE-DISKURS ---
    st.subheader("💬 Live-Diskurs")
    chat_container = st.container(height=350)
    with chat_container:
        if isinstance(chat, list):
            # Sortieren und anzeigen
            sorted_chat = sorted(chat, key=lambda x: x.get('id', 0), reverse=True)[:10] # Zeige nur die letzten 10
            for msg in reversed(sorted_chat):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    st.markdown(f"<div class='system_msg'>🧠 <b>BOT-DENKEN:</b> {content}</div>", unsafe_allow_html=True)
                elif role == "user":
                    st.markdown(f"<div class='user_msg'>🧑‍💻 <b>Du:</b> {content}</div>", unsafe_allow_html=True)
                elif role == "assistant":
                    st.markdown(f"<div class='assistant_msg'>🤖 <b>Ki-Bot:</b> {content}</div>", unsafe_allow_html=True)
        else:
            st.info("Warte auf Konversation...")

    # --- TELEMETRIE ---
    st.markdown("#### 📡 System-Telemetrie")
    st.markdown(f"""
    <div style="background-color: #0c0d14; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 0.8rem; color: #888;">
        [{datetime.now().strftime('%H:%M:%S')}] 🔗 Kraken-API verbunden<br>
        [{datetime.now().strftime('%H:%M:%S')}] 🔢 Berechne RSI, MACD, ATR...<br>
        [{datetime.now().strftime('%H:%M:%S')}] 📊 Prüfe Indikatoren-Setup...
    </div>
    """, unsafe_allow_html=True)

# --- 3. CHAT-EINGABE (GANZ UNTEN) ---
st.markdown("---")
st.subheader("⌨️ Taktische Befehlszeile")
prompt = st.chat_input("Gib dem Broker eine Anweisung... (z.B. 'Prüfe das RSI-Signal für BTC')", key="broker_input_2026")
if prompt:
    success = send_chat_message("user", prompt)
    if success:
        st.success("✅ Befehl an den KI-Bot gesendet.")
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("❌ Fehler beim Senden der Nachricht.")

# --- SIDEBAR: KI-GEDÄCHTNIS ---
with st.sidebar:
    st.header("🧠 KI-Gedächtnis (Dauerspeicher)")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge:
            st.caption(f"📌 **{k.get('kategorie')}**: {k.get('inhalt')}")
    else:
        st.caption("Gedächtnis wird geladen...")
        
    st.markdown("---")
    st.caption("⚙️ Systemstatus: **LIVE** | Modus: **Paper-Trading** | KI: **Groq**")
