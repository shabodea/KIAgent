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

# --- DATEN-REFRESH ---
@st.cache_data(ttl=2)
def load_data():
    try:
        mem = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()
        trades = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS).json()
        chat = requests.get(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS).json()
        return mem, trades, chat
    except:
        return [], [], []

mem_data, trades_data, chat_data = load_data()

# --- MATHEMATISCHE KOORDINATION DER STATISTIKEN ---
aktuelles_guthaben = 200.0  # Startkapital
all_time_gewinn = 0.0
all_time_verlust = 0.0
gesamtes_einsatz_volumen = 0.0

if isinstance(trades_data, list) and len(trades_data) > 0:
    for t in trades_data:
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
    # NEU: Die detaillierten Analyse-Fenster für JEDEN aktiven Trade (Zusätzlich hinzugefügt!)
    st.subheader("🔍 Analyse-Fenster der aktiven Handelspositionen")
    active_trades = [t for t in trades_data if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades_data, list) else []
    
    if len(active_trades) > 0:
        for trade in active_trades:
            with st.expander(f"📦 LIVE-ANALYSIS: {trade.get('Vermögenswert')} | Einstieg: {trade.get('Eintrittspreis')}$", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**📈 Richtung:** {trade.get('Richtung')} ({trade.get('Hebelwirkung')}x)")
                c1.markdown(f"**💵 Marge:** {trade.get('Marge in USD')}$")
                
                c2.markdown(f"**🎯 Target Take Profit:** {trade.get('Take_Profit_Preis')}$")
                c2.markdown(f"**🛡️ Sicherheits-Stop Loss:** {trade.get('Stop_Loss_Preis')}$")
                
                c3.markdown(f"**📊 Erwartete Bewegung:** `{trade.get('Erwartete_Bewegung', 'Berechne...')}`")
                c3.markdown(f"**⚙️ Indikatoren-Setup:** `{trade.get('Indikatoren_Setup', 'Aktiv')}`")
                
                st.info(f"🌐 **Internet-Recherche & Broker-Musterbegründung:**\n{trade.get('Begründung')}")
    else:
        st.info("Aktuell keine laufenden Positionen im Risiko. Triebwerk scannt...")

    # Deine gewohnte Live-Tabelle (Erhalten!)
    st.subheader("📜 Live-Positionen & Strategie-Ziele")
    if isinstance(trades_data, list) and len(trades_data) > 0 and isinstance(trades_data[0], dict):
        df = pd.DataFrame(trades_data)
        display_cols = ["Vermögenswert", "Richtung", "Hebelwirkung", "Eintrittspreis", "Ausstiegspreis", "Marge in USD", "Status", "Begründung"]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols].sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Aktuell keine aktiven Trades in der Handelsgeschichte.")

    # Dein 24/7 Agenten-Logbuch (Wieder vollständig da!)
    st.subheader("🖥️ 24/7 Agenten-Logbuch (Was er aktuell tut)")
    st.markdown(
        f"""<div class="log-box">
        [{datetime.now().strftime('%H:%M:%S')}] 🔍 Starte Echtzeit-Scan auf 5M, 15M, 1H und 4H Zeitebenen...<br>
        [{datetime.now().strftime('%H:%M:%S')}] ⚙️ Berechne RSI- und EMA-Konfluenz für 50 Krypto-Assets via Kraken...<br>
        [{datetime.now().strftime('%H:%M:%S')}] 🌐 Gemini-Gehirn durchsucht das Internet nach Open Interest, Liquidationen und News...<br>
        [{datetime.now().strftime('%H:%M:%S')}] 💎 Evolution: Das System optimiert seine Filtermuster autonom nach jedem Trade.
        </div>""", 
        unsafe_allow_html=True
    )

with right_col:
    # Dein interaktiver KI-Diskurs (Wieder vollständig da!)
    st.subheader("💬 Interaktiver KI-Diskurs")
    
    chat_container = st.container(height=350)
    with chat_container:
        if isinstance(chat_data, list) and len(chat_data) > 0 and isinstance(chat_data[0], dict):
            for msg in sorted(chat_data, key=lambda x: x.get('Ausweis', 0) if isinstance(x, dict) else 0):
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
        else:
            st.write("_Noch keine Nachrichten. Schreib deinem Agenten etwas!_")

    if prompt := st.chat_input("Frag den Agenten nach seiner Begründung oder gib ihm Infos..."):
        with st.chat_message("user"):
            st.write(prompt)
        
        requests.post(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS, json={"role": "user", "content": prompt})
        st.rerun()

# --- SIDEBAR: ASSETS & LERN-FORTSCHRITT (Wieder vollständig da!) ---
with st.sidebar:
    st.header("🧠 KI-Evolutionsstufen")
    st.write("**Aktuelle Überwachungs-Dichte:**")
    st.code("BTC, ETH, SOL, LINK, DOT, ADA, XRP, MATIC, DOGE, AVAX")
    st.markdown("---")
    st.write("🤖 **Gelerntes Wissen (Dauerspeicher):**")
    if mem_data and isinstance(mem_data, list) and len(mem_data) > 0:
        m = mem_data[0]
        if isinstance(m, dict) and m.get("learned_lessons"):
            for lesson in m["learned_lessons"]:
                st.caption(f"🛡️ {lesson}")
        else:
            st.caption("• Analysiere Marktzyklen für autonomes Hebel-Trading (10x).")
            st.caption("• Maximiere Datenaufnahme zur Beschleunigung des Lernprozesses.")
    else:
        st.caption("• Analysiere Marktzyklen für autonomes Hebel-Trading (10x).")
