import os
import json
import re
import time
import ccxt
import numpy as np
import requests
from agents.model_router import ModelRouter
from database.supabase import send_chat_message, save_trade, close_trade
from config.settings import SUPABASE_URL, HEADERS

MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRX-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "MIDNIGHT-USD"
]

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

def get_current_balance():
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=net_pnl&Status=eq.CLOSED",
            headers=HEADERS
        ).json()
        if isinstance(resp, list):
            total_pnl = sum(float(t.get('net_pnl', 0.0)) for t in resp)
            return 200.0 + total_pnl
        return 200.0
    except Exception as e:
        print(f"⚠️ Fehler beim Guthaben: {e}")
        return 200.0

def get_asset_data(symbol):
    try:
        exchange = ccxt.kraken()
        ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
        data = {}
        for tf in ['5m', '15m', '1h', '4h', '1d']:
            ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=tf, limit=50)
            data[tf] = [c[4] for c in ohlcv] if ohlcv else []
        return {
            "symbol": symbol,
            "last": ticker['last'],
            "closes_5m": data['5m'],
            "closes_15m": data['15m'],
            "closes_1h": data['1h'],
            "closes_4h": data['4h'],
            "closes_1d": data['1d']
        }
    except Exception as e:
        print(f"⚠️ Fehler bei {symbol}: {e}")
        return None

def get_performance_summary(symbol):
    # EXTREM GEKÜRZT, um Token zu sparen!
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=net_pnl&Vermögenswert=eq.{symbol}&Status=eq.CLOSED&order=id.desc&limit=3",
            headers=HEADERS
        ).json()
        if not isinstance(resp, list) or len(resp) == 0: 
            return "No history."
        wins = sum(1 for t in resp if t.get('net_pnl', 0.0) > 0)
        return f"Win {wins}/{len(resp)} trades."
    except:
        return "History error."

def get_entry_decision(market_data, balance):
    router = ModelRouter()
    rsi_5m = calculate_rsi(market_data['closes_5m'])
    rsi_15m = calculate_rsi(market_data['closes_15m'])
    rsi_1h = calculate_rsi(market_data['closes_1h'])
    history = get_performance_summary(market_data['symbol'])
    
    # KÜRZERER PROMPT, um das Token-Limit von Groq zu entlasten
    prompt = f"""
    {balance:.0f}€, 10x Hebel. 
    {market_data['symbol']} at {market_data['last']}. 5m RSI:{rsi_5m:.1f}, 15m:{rsi_15m:.1f}, 1h:{rsi_1h:.1f}.
    History: {history}. 
    BUY if 5m/15m oversold & 1h neutral. SELL if overbought. Else HOLD.
    JSON: {{"decision":"BUY"/"SELL"/"HOLD", "reasoning":"...", "sl":0.0, "tp":0.0}}
    """
    answer, _ = router.route(prompt, system_context="NUR JSON.", preferred_model="groq")
    match = re.search(r'\{.*\}', answer, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except: pass
    return {"decision": "HOLD", "reasoning": "API Limit", "sl": 0.0, "tp": 0.0}

def analyze_learn(asset, entry_price, exit_price, pnl, margin, reasoning):
    profit_text = "GEWINN" if pnl > 0 else "VERLUST"
    prompt = f"Trade {asset} {profit_text} ${pnl:.2f}. Lehre mich eine 1-Satz-Lektion."
    router = ModelRouter()
    answer, _ = router.route(prompt, system_context="Du bist ein Coach.", preferred_model="gemini") # Chat & Lernen über Gemini
    send_chat_message("system", f"📘 Lektion: {answer}")

def main_loop():
    print("🧠 Langsam-Modus gestartet (10-Minuten-Takt). API-Limits werden geschont.", flush=True)
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0
    last_api_call = {asset: 0 for asset in MONITORED_ASSETS}
    COOLDOWN_TRADING = 600  # 10 Minuten (statt 60 Sekunden)!

    while True:
        try:
            balance = get_current_balance()
            margin_per_trade = balance * 0.10

            for symbol in MONITORED_ASSETS:
                # Wartezeit von 10 Minuten abwarten
                if time.time() - last_api_call.get(symbol, 0) < COOLDOWN_TRADING:
                    continue
                
                data = get_asset_data(symbol)
                if not data: continue
                
                active_trades = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,direction,Eintrittspreis&Vermögenswert=eq.{symbol}&Status=eq.ACTIVE",
                    headers=HEADERS
                ).json()
                
                has_position = False
                entry_price = 0.0
                direction = "HOLD"
                if isinstance(active_trades, list) and len(active_trades) > 0:
                    first_trade = active_trades[0]
                    if isinstance(first_trade, dict) and 'Eintrittspreis' in first_trade:
                        has_position = True
                        entry_price = float(first_trade['Eintrittspreis'])
                        direction = first_trade.get('direction', 'HOLD')
                
                rsi_5m = calculate_rsi(data['closes_5m'])
                rsi_15m = calculate_rsi(data['closes_15m'])
                
                if has_position and (rsi_5m > 70 or rsi_15m > 70):
                    pnl = (data['last'] - entry_price) / entry_price * margin_per_trade * 10
                    if direction == 'SELL': pnl *= -1
                    close_trade(symbol, data['last'], pnl)
                    analyze_learn(symbol, entry_price, data['last'], pnl, margin_per_trade, "Exit")
                    continue
                
                elif not has_position:
                    decision = get_entry_decision(data, balance)
                    last_api_call[symbol] = time.time()
                    
                    if decision['decision'] in ['BUY', 'SELL']:
                        save_trade(
                            asset=symbol, direction=decision['decision'],
                            entry_price=data['last'], sl=decision.get('sl', 0.0),
                            tp=decision.get('tp', 0.0), reasoning=decision.get('reasoning', 'KI'),
                            indicators=f"5m RSI:{rsi_5m:.1f}",
                            expected_move='Scalp', margin_usd=margin_per_trade, leverage=10, status='ACTIVE'
                        )

            # Chat nur alle 30 Sekunden abfragen (Gemini 20/min Limit geschützt!)
            if int(time.time()) % 30 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None: last_chat_id = new_id

            time.sleep(5)  # Hauptschleife entschleunigen
        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}", flush=True)
            time.sleep(30)

if __name__ == "__main__":
    main_loop()
