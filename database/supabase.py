import requests
from config.settings import SUPABASE_URL, HEADERS

# Zeitlimit fuer JEDE Netzwerk-Anfrage. Ohne das kann eine einzelne haengende
# Verbindung den kompletten Worker fuer immer blockieren, ohne jede Fehlermeldung.
TIMEOUT = 15

def get_all_data_live(limit=50):
    try:
        t = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=*&order=id.desc&limit={limit}", headers=HEADERS, timeout=TIMEOUT).json()
        c = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages?select=*&order=id.desc&limit={limit}", headers=HEADERS, timeout=TIMEOUT).json()
        r = requests.get(f"{SUPABASE_URL}/rest/v1/Risiko_Log?select=*&order=id.desc&limit={limit}", headers=HEADERS, timeout=TIMEOUT).json()
        k = requests.get(f"{SUPABASE_URL}/rest/v1/system_knowledge?select=*&order=id.desc&limit={limit}", headers=HEADERS, timeout=TIMEOUT).json()
        trades = t if isinstance(t, list) else []
        chat = c if isinstance(c, list) else []
        risiko = r if isinstance(r, list) else []
        knowledge = k if isinstance(k, list) else []
        return trades, chat, risiko, knowledge
    except Exception as e:
        print(f"❌ Verbindungsfehler: {e}")
        return [], [], [], []

def send_chat_message(role, content):
    try:
        response = requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={"role": role, "content": content}, timeout=TIMEOUT)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Chat-Fehler: {e}"); return False

def save_trade(asset, direction, entry_price, stop_loss, take_profit, reasoning, indicators, expected_move, margin_usd, leverage=10, status='ACTIVE', target_price=0.0):
    try:
        data = {
            "Vermögenswert": asset, "Richtung": direction, "Eintrittspreis": entry_price,
            "Stop_Loss_Preis": stop_loss, "Take_Profit_Preis": take_profit,
            "Begründung": reasoning, "Indikatoren_Setup": indicators, "Erwartete_Bewegung": expected_move,
            "Status": status, "net_pnl": 0.0, "Marge in USD": margin_usd, "Hebelwirkung": leverage, "target_price": target_price
        }
        response = requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json=data, timeout=TIMEOUT)
        if response.status_code not in (200, 201):
            print(f"⚠️ Trade speichern ({asset}) HTTP {response.status_code}: {response.text[:200]}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Fehler beim Speichern: {e}"); return False

def close_trade(asset, exit_price, pnl):
    try:
        trades = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id&Vermögenswert=eq.{asset}&Status=eq.ACTIVE", headers=HEADERS, timeout=TIMEOUT).json()
        if not isinstance(trades, list) or len(trades) == 0: return False
        trade_id = trades[0]['id']
        data = {"Status": "CLOSED", "net_pnl": pnl, "Austrittspreis": exit_price}
        response = requests.patch(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?id=eq.{trade_id}", headers=HEADERS, json=data, timeout=TIMEOUT)
        if response.status_code not in (200, 201, 204):
            print(f"⚠️ Trade schließen ({asset}) HTTP {response.status_code}: {response.text[:200]}")
        return response.status_code in [200, 201, 204]
    except Exception as e:
        print(f"❌ Fehler beim Schließen: {e}"); return False


def get_current_balance_and_winrate(base_balance=100.0, lookback=200):
    """Gibt (virtuelle Balance, Trefferquote, Anzahl geschlossener Trades) zurueck."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=net_pnl&Status=eq.CLOSED&order=id.desc&limit={lookback}",
            headers=HEADERS, timeout=TIMEOUT
        ).json()
        if not isinstance(resp, list):
            return base_balance, 0.5, 0
        wins = sum(1 for t in resp if t.get('net_pnl', 0.0) > 0)
        total = len(resp)
        winrate = wins / total if total > 0 else 0.5
        total_pnl = sum(float(t.get('net_pnl', 0.0)) for t in resp)
        return max(base_balance + total_pnl, 10.0), winrate, total
    except Exception as e:
        print(f"❌ Balance/Winrate-Fehler: {e}"); return base_balance, 0.5, 0


def upsert_market_snapshot(symbol, last_price, direction, confidence, reasons, rsi_by_tf):
    """Schreibt/ueberschreibt die aktuelle Einschaetzung fuer EIN Asset (eine Zeile pro Symbol,
    kein wachsendes Log). Das ist die schnelle Datenquelle fuer die Live-Tabelle im Dashboard,
    damit das Dashboard selbst keine eigenen Kraken-Anfragen mehr braucht."""
    try:
        reasons_text = ", ".join(reasons) if isinstance(reasons, list) else str(reasons)
        payload = {
            "symbol": symbol, "last_price": last_price, "direction": direction,
            "confidence": confidence, "reasons": reasons_text,
            "rsi_5m": rsi_by_tf.get("5m"), "rsi_15m": rsi_by_tf.get("15m"),
            "rsi_1h": rsi_by_tf.get("1h"), "rsi_4h": rsi_by_tf.get("4h"), "rsi_1d": rsi_by_tf.get("1d"),
            "updated_at": "now()",
        }
        headers_upsert = dict(HEADERS)
        headers_upsert["Prefer"] = "resolution=merge-duplicates"
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/market_snapshot?on_conflict=symbol", headers=headers_upsert, json=payload, timeout=TIMEOUT)
        if resp.status_code not in (200, 201, 204):
            print(f"⚠️ Snapshot-Update ({symbol}) HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"⚠️ Snapshot-Update fehlgeschlagen ({symbol}): {e}")


def get_market_snapshot():
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/market_snapshot?select=*&order=symbol.asc", headers=HEADERS, timeout=TIMEOUT).json()
        return resp if isinstance(resp, list) else []
    except Exception as e:
        print(f"❌ Snapshot laden fehlgeschlagen: {e}"); return []


def get_bot_thoughts(limit=25):
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/bot_thoughts?select=*&order=id.desc&limit={limit}", headers=HEADERS, timeout=TIMEOUT
        ).json()
        return resp if isinstance(resp, list) else []
    except Exception as e:
        print(f"❌ Denkprotokoll laden fehlgeschlagen: {e}"); return []


def log_thought(symbol, direction, confidence, reasons, ai_comment=""):
    """Schreibt JEDE Analyse (auch HOLD) ins Denkprotokoll, damit das Dashboard zeigt,
    was der Bot gerade prueft - nicht nur was er tatsaechlich tradet."""
    try:
        reasons_text = ", ".join(reasons) if isinstance(reasons, list) else str(reasons)
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/bot_thoughts", headers=HEADERS, json={
            "symbol": symbol, "direction": direction, "confidence": confidence,
            "reasons": reasons_text, "ai_comment": ai_comment
        }, timeout=TIMEOUT)
        if resp.status_code not in (200, 201, 204):
            print(f"⚠️ Denkprotokoll-Log ({symbol}) HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"⚠️ Denkprotokoll-Log fehlgeschlagen: {e}")


def check_and_notify_milestone(total_closed, winrate, threshold=0.70, min_trades=200):
    """Meldet sich einmalig im Chat, sobald >= min_trades Trades UND Trefferquote >= threshold."""
    if total_closed < min_trades or winrate < threshold:
        return
    try:
        flag = requests.get(
            f"{SUPABASE_URL}/rest/v1/system_knowledge?kategorie=eq.milestone_70", headers=HEADERS, timeout=TIMEOUT
        ).json()
        if isinstance(flag, list) and len(flag) == 0:
            send_chat_message("system", f"🏆 Meilenstein erreicht: {winrate*100:.1f}% Trefferquote über {total_closed} Trades!")
            requests.post(f"{SUPABASE_URL}/rest/v1/system_knowledge", headers=HEADERS,
                          json={"kategorie": "milestone_70", "inhalt": str(winrate)}, timeout=TIMEOUT)
    except Exception as e:
        print(f"⚠️ Meilenstein-Check fehlgeschlagen: {e}")
