import requests
from config.settings import SUPABASE_URL, HEADERS

def get_all_data_live():
    """
    Fragt alle 4 Haupttabellen synchron aus Supabase ab.
    FEHLERBEHEBUNG: Cache-Buster (_ts) entfernt, da PostgREST ihn als Spalten-Filter interpretiert!
    """
    try:
        t = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=*", headers=HEADERS).json()
        c = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages?select=*", headers=HEADERS).json()
        r = requests.get(f"{SUPABASE_URL}/rest/v1/Risiko_Log?select=*", headers=HEADERS).json()
        k = requests.get(f"{SUPABASE_URL}/rest/v1/system_knowledge?select=*", headers=HEADERS).json()
        
        # Falls Supabase Fehler-Dictionaries statt Listen zurückgibt, Fallback aktivieren
        trades = t if isinstance(t, list) else []
        chat = c if isinstance(c, list) else []
        risiko = r if isinstance(r, list) else []
        knowledge = k if isinstance(k, list) else []
        
        return trades, chat, risiko, knowledge
    except Exception as e:
        print(f" Kritischer Datenbank-Verbindungsfehler: {e}")
        return [], [], [], []

def send_chat_message(role, content):
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/chat_messages", 
            headers=HEADERS, 
            json={"role": role, "content": content}
        )
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Fehler beim Senden der Chat-Nachricht: {e}")
        return False

def save_trade(asset, direction, entry_price, reasoning, status='PAPER'):
    """
    Speichert eine Trading-Entscheidung in der Handelsgeschichte-Tabelle.
    """
    try:
        data = {
            "Vermögenswert": asset,
            "Richtung": direction,
            "Eintrittspreis": entry_price,
            "Begründung": reasoning,
            "Status": status,
            "net_pnl": 0.0,  # bei Paper-Trading erstmal 0
            "Marge in USD": 0.0,
            "Hebelwirkung": 1
        }
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte",
            headers=HEADERS,
            json=data
        )
        if response.status_code in [200, 201]:
            print(f"✅ Trade gespeichert: {direction} {asset} zu {entry_price}")
            return True
        else:
            print(f"❌ Fehler beim Speichern des Trades: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception beim Speichern: {e}")
        return False
