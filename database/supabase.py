import requests
from config.settings import SUPABASE_URL, HEADERS

def get_all_data_live(limit=50):
    try:
        t = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=*&order=id.desc&limit={limit}", headers=HEADERS).json()
        c = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages?select=*&order=id.desc&limit={limit}", headers=HEADERS).json()
        r = requests.get(f"{SUPABASE_URL}/rest/v1/Risiko_Log?select=*&order=id.desc&limit={limit}", headers=HEADERS).json()
        k = requests.get(f"{SUPABASE_URL}/rest/v1/system_knowledge?select=*&order=id.desc&limit={limit}", headers=HEADERS).json()
        trades = t if isinstance(t, list) else []
        chat = c if isinstance(c, list) else []
        risiko = r if isinstance(r, list) else []
        knowledge = k if isinstance(k, list) else []
        return trades, chat, risiko, knowledge
    except Exception as e:
        print(f"❌ Datenbank-Verbindungsfehler: {e}")
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

def save_trade(asset, direction, entry_price, stop_loss, take_profit, reasoning, indicators, expected_move, margin_usd, leverage=10, status='ACTIVE', target_price=0.0):
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
            "Marge in USD": margin_usd,
            "Hebelwirkung": leverage,
            "target_price": target_price
        }
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte",
            headers=HEADERS,
            json=data
        )
        if response.status_code in [200, 201]:
            print(f"✅ Scalp-Trade gespeichert: {direction} {asset} | Ziel: ${target_price:.2f}")
            return True
        else:
            print(f"❌ Fehler beim Speichern: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception beim Speichern: {e}")
        return False

def close_trade(asset, exit_price, pnl):
    try:
        trades = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id&Vermögenswert=eq.{asset}&Status=eq.ACTIVE",
            headers=HEADERS
        ).json()
        if not isinstance(trades, list) or len(trades) == 0:
            return False
        trade_id = trades[0]['id']
        data = {
            "Status": "CLOSED",
            "net_pnl": pnl
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
