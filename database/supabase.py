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

def save_trade(asset, direction, entry_price, stop_loss=0.0, take_profit=0.0, reasoning="", indicators="", expected_move="", status='PAPER'):
    try:
        data = {
            "Vermögenswert": asset,
            "Richtung": direction,
            "Eintrittspreis": entry_price,
            "Stop_Loss_Preis": stop_loss,
            "Take_Profit_Preis": take_profit,
            "Begründung": reasoning,
            "Indikatoren_Setup": indicators,
            "Erwartete_Bewegung": expected_move,
            "Status": status,
            "net_pnl": 0.0,
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
            print(f"❌ Fehler beim Speichern: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception beim Speichern: {e}")
        return False

def close_trade(asset, exit_price, pnl):
    """Findet den aktiven Trade für das Asset und schließt ihn."""
    try:
        # 1. Aktiven Trade finden
        trades = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id&Vermögenswert=eq.{asset}&Status=eq.ACTIVE",
            headers=HEADERS
        ).json()
        
        if not trades or len(trades) == 0:
            return False
            
        trade_id = trades[0]['id']
        
        # 2. Update auf CLOSED setzen
        data = {
            "Status": "CLOSED",
            "net_pnl": pnl
            # Optional: "Austrittspreis" Spalte, falls du eine hast
        }
        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?id=eq.{trade_id}",
            headers=HEADERS,
            json=data
        )
        return response.status_code in [200, 201, 204]
    except Exception as e:
        print(f"❌ Fehler beim Schließen des Trades: {e}")
        return False
