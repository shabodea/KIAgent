import os
import time
import requests
from datetime import datetime

# Schlüssel und Cloud-Datenbank-Konfiguration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

KRAKEN_TAKER_FEE = 0.0026
MAX_TOTAL_BUDGET_USD = 200.0  
POSITION_SIZE_USD = 50.0      
FIXED_LEVERAGE = 10           

def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url, timeout=10).json()
        all_pairs = res.get("result", {})
        return [pair for pair in all_pairs.keys() if pair.endswith("USDT")]
    except:
        return ["XBTUSDT", "ETHUSDT", "SOLUSDT"]

def get_current_used_budget():
    try:
        url = f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?Status=eq.ACTIVE"
        res = requests.get(url, headers=HEADERS).json()
        if isinstance(res, list):
            return sum(float(trade.get("Marge in USD", 0)) for trade in res if "Hebelwirkung" in trade)
        return 0.0
    except:
        return 999.0

def is_bot_paused():
    try:
        url = f"{SUPABASE_URL}/rest/v1/bot_memory"
        res = requests.get(url, headers=HEADERS).json()
        if res and isinstance(res, list):
            memory = res[0]
            paused_until = memory.get("paused_until")
            if paused_until:
                until_time = datetime.fromisoformat(paused_until.replace("Z", "+00:00"))
                if datetime.utcnow().timestamp() < until_time.timestamp():
                    return True
        return False
    except:
        return False

def check_and_close_trades():
    """
    Überwachungs-Maschine angepasst an deine exakten Supabase-Spaltennamen.
    Berechnet PnL mit 10x Hebel und fordert im Chat Feedback, falls ein Fehler auftritt.
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?Status=eq.ACTIVE"
        active_trades = requests.get(url, headers=HEADERS).json()
        if not isinstance(active_trades, list) or len(active_trades) == 0: return

        for trade in active_trades:
            if "Vermögenswert" not in trade or not trade["Vermögenswert"]: continue
            pair = trade["Vermögenswert"]
            trade_id = trade.get("Ausweis")
            
            # Live-Kurs von Kraken holen
            url_ticker = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
            res = requests.get(url_ticker, timeout=10).json()
            if "result" not in res: continue
            ticker_data = list(res["result"].values())[0]
            current_price = (float(ticker_data["b"][0]) + float(ticker_data["a"][0])) / 2
            
            entry = float(trade.get("Eintrittspreis", current_price))
            sl = entry * 0.985  # 1.5% Stop-Loss
            tp = entry * 1.03   # 3.0% Take-Profit
            
            closed = False
            reason = ""
            
            if current_price <= sl:
                closed = True
                reason = "STOP-LOSS"
            elif current_price >= tp:
                closed = True
                reason = "TAKE-PROFIT"
                
            if closed:
                # Exakte Hebel-Gewinnberechnung (LONG)
                price_change_p = (current_price - entry) / entry
                realized_pnl = POSITION_SIZE_USD * price_change_p * FIXED_LEVERAGE
                fees = float(trade.get("Gebühren_USD", 0))
                final_pnl = round(realized_pnl - fees, 4)

                # Update exakt in deine deutschen Tabellenspalten schießen!
                requests.patch(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?Ausweis=eq.{trade_id}", headers=HEADERS, json={
                    "Status": "CLOSED",
                    "Ausstiegspreis": current_price,
                    "net_pnl": final_pnl,
                    "Begründung": f"🔴 Geschlossen bei {round(current_price, 4)} via {reason}. Netto: {final_pnl}$"
                })
                
                # Feedback-Schleife triggern bei Verlust
                if final_pnl < 0:
                    feedback_prompt = (
                        f"Ein Trade für {pair} wurde im Stop-Loss beendet (Verlust: {final_pnl}$).\n"
                        f"Einstieg: {entry} | Ausstieg: {current_price}.\n"
                        "Schreibe eine kurze, direkte Nachricht an den Master auf Deutsch. "
                        "Erkläre präzise, welche Marktdaten dir fehlen (z.B. RSI, MACD oder gleitende Durchschnitte) "
                        "oder welche strategische Code-Erweiterung du von ihm brauchst, um dich weiter zu verbessern."
                    )
                    assistant_demand = ask_gemini_expert(feedback_prompt)
                    
                    requests.post(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS, json={
                        "role": "assistant",
                        "content": f"⚠️ **BOT-REFLXION NACH VERLUST:**\n\n{assistant_demand}\n\n*LEKTION: Meister, wir müssen den Code erweitern, um diesen Fehler künftig zu vermeiden.*"
                    })

                print(f"🔴 Position geschlossen: {pair} | Net-PnL: {final_pnl}$")
    except Exception as e:
        print(f"Fehler bei Trade-Überwachung: {e}")

def get_orderbook_and_atr(pair):
    try:
        url_depth = f"https://api.kraken.com/0/public/Depth?pair={pair}&count=5"
        url_ticker = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
        res_depth = requests.get(url_depth, timeout=10).json()
        res_ticker = requests.get(url_ticker, timeout=10).json()
        pair_depth = list(res_depth.get("result", {}).values())[0]
        pair_ticker = list(res_ticker.get("result", {}).values())[0]
        
        best_bid = float(pair_depth.get("bids", [[0]])[0][0])
        best_ask = float(pair_depth.get("asks", [[0]])[0][0])
        live_price = (best_bid + best_ask) / 2
        
        total_bid_vol = sum(float(b[1]) for b in pair_depth.get("bids", []))
        total_ask_vol = sum(float(a[1]) for a in pair_depth.get("asks", []))
        ratio = total_bid_vol / total_ask_vol if total_ask_vol > 0 else 1
        
        high_24h = float(pair_ticker.get("h", [live_price])[0])
        low_24h = float(pair_ticker.get("l", [live_price])[0])
        
        return {"live_price": live_price, "orderbook_ratio": round(ratio, 2), "volatility": (high_24h - low_24h)}
    except:
        return None

def get_advanced_metrics(asset_ticker):
    try:
        ticker = asset_ticker.replace("USDT", "").lower()
        if ticker == "xbt": ticker = "btc"
        search_res = requests.get(f"https://api.coingecko.com/api/v3/search?query={ticker}", timeout=10).json()
        if not search_res.get("coins"): return {"inflation_risk": "Low", "released_p": 100}
        coin_id = search_res["coins"][0]["id"]
        coin_data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}", timeout=10).json()
        market_data = coin_data.get("market_data", {})
        circulating = market_data.get("circulating_supply", 0)
        total_max = market_data.get("max_supply") or market_data.get("total_supply") or circulating
        released_percentage = (circulating / total_max) * 100 if total_max > 0 else 100
        return {"released_p": round(released_percentage, 2), "inflation_risk": "LOW" if released_percentage > 50 else "HIGH"}
    except:
        return {"released_p": 100.0, "inflation_risk": "Low"}

def run_unlimited_expert_trading():
    try:
        if is_bot_paused(): return
        current_allocated = get_current_used_budget()
        if current_allocated >= MAX_TOTAL_BUDGET_USD: return

        all_pairs = get_live_kraken_markets()

        for pair in all_pairs[:15]:
            if is_bot_paused() or get_current_used_budget() >= MAX_TOTAL_BUDGET_USD: break
            market_stats = get_orderbook_and_atr(pair)
            if not market_stats: continue
                
            if market_stats["orderbook_ratio"] > 1.4:
                adv_metrics = get_advanced_metrics(pair)
                if "HIGH" in adv_metrics["inflation_risk"]: continue
                
                price = market_stats["live_price"]
                exact_fees = POSITION_SIZE_USD * KRAKEN_TAKER_FEE * 2
                
                expert_prompt = f"Du bist der {FIXED_LEVERAGE}x Krypto-Experte. Signal für {pair} bei {price}. Lohnt sich ein Long-Trade? Antworte mit 'GO: Begründung' oder 'HOLD'."
                decision = ask_gemini_expert(expert_prompt)
                
                if "GO:" in decision:
                    # Payload exakt auf deine deutschen Spalten ausgerichtet
                    trade_payload = {
                        "Vermögenswert": pair,
                        "Richtung": "LONG",
                        "Hebelwirkung": FIXED_LEVERAGE,
                        "Eintrittspreis": price,
                        "Marge in USD": POSITION_SIZE_USD,
                        "Gebühren_USD": exact_fees,
                        "Status": "ACTIVE",
                        "Begründung": f"[10x] {decision.split('GO:')[-1].strip()}"
                    }
                    requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json=trade_payload)
                    print(f"🟢 TRADE GEÖFFNET: {pair}")
                    break
            time.sleep(2)
    except Exception as e:
        print(f"Fehler im Trading-Loop: {e}")

def ask_gemini_expert(prompt_text):
    if not GEMINI_API_KEY: return "⚠️ Key fehlt"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt_text}]}]}, timeout=15)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return "HOLD"

def process_chat():
    try:
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS).json()
        if messages and len(messages) > 0:
            latest_msg = sorted(messages, key=lambda x: x.get('Ausweis', 0))[-1]
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                system_context = "Du bist der unfehlbare Krypto-Trading-Experte. Antworte kurz auf Deutsch. Beende mit LEKTION: ..."
                bot_response = ask_gemini_expert(f"{system_context}\n\nMaster schreibt: {user_input}")
                requests.post(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS, json={"role": "assistant", "content": bot_response})
    except Exception as e: print(f"Fehler im Chat: {e}")

# --- HAUPTLOOP ---
print("🦅 Das vollendete Experten-Triebwerk läuft...")
while True:
    process_chat()
    check_and_close_trades() 
    run_unlimited_expert_trading()
    time.sleep(15)
