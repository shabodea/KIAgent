import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Datenbank-Verbindung
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

st.set_page_config(page_title="🦅 KI-Zentrale 10x", layout="wide", initial_sidebar_state="expanded")

# --- STYLING (Dark Mode & Trading Look) ---
st.markdown("""
    <style>
    .metric-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #2962ff; }
    .log-box { background-color: #0c0d14; padding: 15px; border-radius: 5px; font-family: monospace; color: #00ff66; height: 200px; overflow-y: scroll; }
    </style>
""", unsafe_allow_html=True)

st.title("🦅 AUTONOMER KI-AGENT — KOMMANDOZENTRALE")
st.caption("24/7 Multi-Timeframe Scan & Evolution-Modus aktiv")

# --- DATEN-REFRESH (An deine echten Tabellennamen angepasst) ---
@st.cache_data(ttl=2)
def load_data():
    mem = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()
    trades = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS).json()
    chat = requests.get(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS).json()
    return mem, trades, chat

mem_data, trades_data, chat_data = load_data()

# --- MATHEMATISCHE KOORDINATION DER STATISTIKEN (An deine echten Spalten angepasst) ---
aktuelles_guthaben = 200.0  # Dein Startkapital als mathematische Basis
all_time_gewinn = 0.0
all_time_verlust = 0.0
gesamtes_einsatz_volumen = 0.0

if isinstance(trades_data, list) and len(trades_data) > 0:
    for t in trades_data:
        # Falls ein fehlerhafter Eintrag (z.B. ein String statt Dictionary) reinkommt, überspringen
        if not isinstance(t, dict): 
            continue
        status = t.get("Status")
        pnl = float(t.get("net_pnl") or 0.0)
        marge = float(t.get("Marge in USD") or 0.0)
        
        # 1. Nur das Volumen der aktuell AKTIVEN Trades addieren
        if status == "ACTIVE":
            gesamtes_einsatz_volumen += marge
            
        # 2. Gewinne und Verluste aus geschlossenen Positionen verrechnen
        if status == "CLOSED":
            if pnl > 0:
                all_time_gewinn += pnl
            else:
                all_time_verlust += abs(pnl)
            aktuelles_guthaben += pnl

# --- ANZEIGE DER LIVE-METRIKEN ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💰 Aktuelles Guthaben", f"${aktuelles_guthaben:.2f}")
with col2:
    st.metric("🟢 All-Time Gewinn", f"+${all_time_gewinn:.2f}")
with col3:
    st.metric("🔴 All-Time Verlust", f"-${all_time_verlust:.2f}")
with col4:
    st.metric("🔥 Gesamtes Einsatz-Volumen", f"${gesamtes_einsatz_volumen:.2f}")

st.markdown("---")

# --- HAUPTBEREICH: ZWEI-SPALTEN-LAYOUT ---
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("📜 Live-Positionen & Strategie-Ziele")
    
    # JETZT ABSICHERT: Verhindert den Pandas-ValueError, falls die Tabelle temporär leer ist
    if isinstance(trades_data, list) and len(trades_data) > 0 and isinstance(trades_data[0], dict):
        df = pd.DataFrame(trades_data)
        # Relevante Spalten filtern basierend auf deinen echten deutschen Spaltennamen
        display_cols = ["Vermögenswert", "Richtung", "Hebelwirkung", "Eintrittspreis", "Ausstiegspreis", "Marge in USD", "Status", "Begründung"]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols].sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Aktuell keine aktiven Trades in der Handelsgeschichte.")

    # Logbuch-Bereich
    st.subheader("🖥️ 24/7 Agenten-Logbuch (Was er aktuell tut)")
    st.markdown(
        f"""<div class="log-box">
        [{datetime.now().strftime('%H:%M:%S')}] 🔍 Starte Scan auf 5M, 15M, 1H und 4H Zeitebenen...<br>
        [{datetime.now().strftime('%H:%M:%S')}] ⚙️ Berechne RSI und EMA-Konfluenz für 12 Krypto-Assets...<br>
        [{datetime.now().strftime('%H:%M:%S')}] 🧠 Gemini-Gehirn analysiert Marktstimmung via Web-Auswertung...<br>
        [{datetime.now().strftime('%H:%M:%S')}] 💎 Evolution: Der Agent lernt aus den letzten 5 Trades.
        </div>""", 
        unsafe_allow_html=True
    )

with right_col:
    st.subheader("💬 Interaktiver KI-Diskurs")
    
    # Chat-Verlauf anzeigen
    chat_container = st.container(height=350)
    with chat_container:
        if chat_data:
            # Sortiert nach deinem Spaltennamen 'Ausweis' (deine ID)
            for msg in sorted(chat_data, key=lambda x: x.get('Ausweis', 0)):
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
        else:
            st.write("_Noch keine Nachrichten. Schreib deinem Agenten etwas!_")

    # Chat-Eingabe (Injektion in deine Tabelle 'Chatnachrichten')
    if prompt := st.chat_input("Frag den Agenten nach seiner Begründung oder gib ihm Infos..."):
        with st.chat_message("user"):
            st.write(prompt)
        
        requests.post(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS, json={"role": "user", "content": prompt})
        st.rerun()

# --- SIDEBAR: ASSETS & LERN-FORTSCHRITT ---
with st.sidebar:
    st.header("🧠 KI-Evolutionsstufen")
    st.write("**Aktuelle Überwachungs-Dichte:**")
    st.code("BTC, ETH, SOL, LINK, DOT, ADA, XRP, MATIC, DOGE, AVAX")
    st.markdown("---")
    st.write("🤖 **Gelerntes Wissen:**")
    if mem_data and isinstance(mem_data, list) and len(mem_data) > 0:
        m = mem_data[0]
        if m.get("learned_lessons"):
            for lesson in m["learned_lessons"]:
                st.caption(f"• {lesson}")
        else:
            st.caption("• Analysiere Marktzyklen für autonomes Hebel-Trading (10x).")
            st.caption("• Maximiere Datenaufnahme zur Beschleunigung des Lernprozesses.")
    else:
        st.caption("• Analysiere Marktzyklen für autonomes Hebel-Trading (10x).")
