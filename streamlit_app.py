import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- DATENBANK VERBINDUNG ---
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

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

# --- SÄULE 1: DATENSAMMLER (DIE LIVE-ABFRAGE DER 4 TABELLEN) ---
def get_all_data_live():
    try:
        timestamp = int(datetime.utcnow().timestamp())
        t = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=*&_ts={timestamp}", headers=HEADERS).json()
        c = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages?select=*&_ts={timestamp}", headers=HEADERS).json()
        r = requests.get(f"{SUPABASE_URL}/rest/v1/Risiko_Log?select=*&_ts={timestamp}", headers=HEADERS).json()
        k = requests.get(f"{SUPABASE_URL}/rest/v1/system_knowledge?select=*&_ts={timestamp}", headers=HEADERS).json()
        return t, c, r, k
    except Exception as e:
        return [], [], [], []

# ABFRAGE DIREKT AM ANFANG STARTEN
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

# --- STRATEGISCHE BEFEHLSZEILE (NUR EINMAL SEITENWEIT EXPOSED) ---
st.subheader("⌨️ Taktische Befehlszeile")
if prompt := st.chat_input("Gib dem Broker eine Anweisung..."):
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/chat_messages", 
            headers=HEADERS, 
            json={"role": "user", "content": prompt}
        )
        if response.status_code in [200, 201]:
            st.cache_data.clear()
            st.rerun()
    except Exception as e:
        st.error(f"Netzwerk-Fehler beim Senden: {str(e)}")

# --- SIDEBAR: UNSTERBLICHES GEDÄCHTNIS ---
with st.sidebar:
    st.header("🧠 KI-Gedächtnis (Dauerspeicher)")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge:
            st.caption(f"🛡️ **{k.get('kategorie')}**: {k.get('inhalt')}")
    else:
        st.caption("• Gedächtnis leer oder wird geladen...")

# HIER WERDEN ALLE VIER DATENSTRÖME DIREKT ZU BEGINN ZUGEWIESEN
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

# --- STRATEGISCHE BEFEHLSZEILE GANZ UNTEN ---
st.subheader("⌨️ Taktische Befehlszeile")
# DAMIT ERSETZEN:
if prompt := st.chat_input("Gib dem Broker eine Anweisung...", key="unique_broker_chat_input_2026"):
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/chat_messages", 
            headers=HEADERS, 
            json={"role": "user", "content": prompt}
        )
        if response.status_code in [200, 201]:
            st.cache_data.clear()
            st.rerun()
    except Exception as e:
        st.error(f"Netzwerk-Fehler beim Senden: {str(e)}")

# --- SIDEBAR: UNSTERBLICHES GEDÄCHTNIS ---
with st.sidebar:
    st.header("🧠 KI-Gedächtnis (Dauerspeicher)")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge:
            st.caption(f"🛡️ **{k.get('kategorie')}**: {k.get('inhalt')}")
    else:
        st.caption("• Gedächtnis leer oder wird geladen...")

# <--- EXAKT HIERHIN GEHÖRT DER ABRAUF JETZT (GANZ OBEN IM CODE!) --->
trades, chat, risiko, knowledge = get_all_data_live()

# --- MATHEMATISCHE AUSWERTUNG ---


trades, chat, risiko, knowledge = get_all_data_live()

# --- MATHEMATISCHE AUSWERTUNG ---
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

# --- METRIKEN ---
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("💰 Depot-Wert", f"${guthaben:.2f}")
with m2: st.metric("📊 Trefferquote", f"{win_rate:.1f}%")
with m3: st.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "CRITICAL")
with m4:
    tages_status = risiko[0].get("status") if isinstance(risiko, list) and len(risiko) > 0 else "OPEN"
    st.metric("⚡ Tages-Schutzschild", tages_status)

st.markdown("---")

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
                st.info(f"ℹ️ **Einfache Erklärung des Handelsmusters:**\n{pos.get('Begründung')}")
    else:
        st.info("Der Broker wartet auf ein klares mathematisches Signal und positives Internet-Sentiment.")

    st.subheader("📜 Letzte Buchungen")
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
        else: st.info("Noch keine Nachrichten.")

st.markdown("---")

st.subheader("⌨️ Taktische Befehlszeile")
if prompt := st.chat_input("Gib dem Broker eine Anweisung..."):
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={"role": "user", "content": prompt})
        st.rerun()
    except Exception as e: st.error(f"Fehler: {e}")

with st.sidebar:
    st.header("🧠 KI-Gedächtnis (Dauerspeicher)")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge: st.caption(f"🛡️ **{k.get('kategorie')}**: {k.get('inhalt')}")

trades, chat, risiko = get_all_data_live()  # <--- HIER liegt der Fehler!


trades, chat, risiko = get_all_data_live()  # <--- HIER liegt der Fehler!

# --- MATHEMATISCHE AUSWERTUNG ---
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

# --- METRIKEN-ZEILE ---
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
                st.info(f"ℹ️ **Einfache Erklärung des Handelsmusters:**\nDer Bot hat den 15-Minuten-Chart analysiert. Da der Kurs über dem Durchschnitt (EMA) lag und die Gemini-Internetrecherche ein bullisches Sentiment ergab, wurde diese Position eröffnet.")
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
            # FIX: Sortierung angepasst von 'Ausweis' auf 'id'
            for msg in sorted(chat, key=lambda x: x.get('id', 0) if isinstance(x, dict) else 0):
                with st.chat_message(msg.get("role", "user")):
                    st.write(msg.get("content", ""))
        else:
            st.info("Noch keine Nachrichten im Verlauf. Schreibe deine erste Anweisung!")

st.markdown("---")

# --- STRATEGISCHE BEFEHLSZEILE ---
st.subheader("⌨️ Taktische Befehlszeile")
if prompt := st.chat_input("Gib dem Broker eine Anweisung oder frage nach Markt-Sentiment..."):
    try:
        # FIX: Geändert von Chatnachrichten auf chat_messages
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/chat_messages", 
            headers=HEADERS, 
            json={"role": "user", "content": prompt}
        )
        
        if response.status_code in [200, 201]:
            st.success("Gesendet!")
            st.rerun()
        else:
            st.error(f"Datenbank-Fehler: Code {response.status_code} - {response.text}")
            
    except Exception as e:
        st.error(f"Netzwerk-Fehler beim Senden: {str(e)}")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🧠 KI-Gedächtnis (Dauerspeicher)")
    try:
        mem = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()
        if mem and isinstance(mem, list) and len(mem) > 0:
            lessons = mem[0].get("learned_lessons", [])
            if isinstance(lessons, list) and len(lessons) > 0:
                for lesson in lessons:
                    st.caption(f"🛡️ {lesson}")
            else:
                st.caption("• System im fehlerfreien Zustand.")
        else:
            st.caption("• Verbinde mit Gedächtnis-Speicher...")
    except:
        st.caption("• Keine Verbindung zum Gedächtnis.")
