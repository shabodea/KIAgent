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
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "NIGHT-USD"  
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
    except:
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
    except:
        return None

def get_performance_summary(symbol):
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=net_pnl&Vermögenswert=eq.{symbol}&Status=eq.CLOSED&order=id.desc&limit=3",
            headers=HEADERS
        ).json()
        if not isinstance(resp, list) or len(resp) == 0: return "No history."
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
    
    # Wir fordern jetzt zusätzlich eine Prognose und Begründung an
    prompt = f"""
    {market_data['symbol']} {market_data['last']:.0f} | 5m RSI:{rsi_5m:.0f} 15m:{rsi_15m:.0f} 1h:{rsi_1h:.0f}
    Hist: {history}
    Entscheide BUY/SELL/HOLD. Wenn BUY oder SELL, gib auch einen erwarteten Kurs an (target price).
    JSON: {{"d":"BUY"/"SELL"/"HOLD","r":"Begründung","sl":0,"tp":0,"target":0}}
    """
    answer, _ = router.route(prompt, system_context="NUR JSON.", preferred_model="deepseek")
    match = re.search(r'\{.*\}', answer, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except: pass
    return {"d": "HOLD", "r": "Limit", "sl": 0.0, "tp": 0.0, "target": 0.0}

def analyze_learn(asset, entry_price, exit_price, pnl, margin, reasoning, target_price, hit):
    profit_text = "GEWINN" if pnl > 0 else "VERLUST"
    hit_text = "erreicht" if hit else "verfehlt"
    prompt = f"""
    Trade {asset} {profit_text} ${pnl:.2f}. 
    Prognose: Kurs sollte {target_price} erreichen. Ergebnis: {hit_text}.
    Gib mir eine kurze Lektion, warum ich falsch oder richtig lag, und was ich beim nächsten Mal besser machen kann.
    """
    router = ModelRouter()
    answer, _ = router.route(prompt, system_context="Du bist ein Coach.", preferred_model="deepseek")
    send_chat_message("system", f"📘 Lektion: {answer}")

def main_loop():
    print("⚡ DeepSeek-Only mit Prognose-Lernen (15s pro Asset).", flush=True)
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0
    last_api_call = {asset: 0 for asset in MONITORED_ASSETS}
    COOLDOWN_TRADING = 15

    while True:
        try:
            balance = get_current_balance()
            margin_per_trade = balance * 0.10

            for symbol in MONITORED_ASSETS:
                if time.time() - last_api_call.get(symbol, 0) < COOLDOWN_TRADING:
                    continue
                
                data = get_asset_data(symbol)
                if not data: continue
                
                active_trades = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,direction,Eintrittspreis,target_price&Vermögenswert=eq.{symbol}&Status=eq.ACTIVE",
                    headers=HEADERS
                ).json()
                
                has_position = False
                entry_price = 0.0
                direction = "HOLD"
                target_price = 0.0  # Erwarteter Kurs aus der Prognose
                if isinstance(active_trades, list) and len(active_trades) > 0:
                    first_trade = active_trades[0]
                    if isinstance(first_trade, dict) and 'Eintrittspreis' in first_trade:
                        has_position = True
                        entry_price = float(first_trade['Eintrittspreis'])
                        direction = first_trade.get('direction', 'HOLD')
                        target_price = float(first_trade.get('target_price', 0.0))
                
                rsi_5m = calculate_rsi(data['closes_5m'])
                rsi_15m = calculate_rsi(data['closes_15m'])
                
                if has_position and (rsi_5m > 70 or rsi_15m > 70):
                    exit_price = data['last']
                    pnl = (exit_price - entry_price) / entry_price * margin_per_trade * 10
                    if direction == 'SELL': pnl *= -1
                    # Prüfen, ob die Prognose eingetroffen ist
                    if direction == 'BUY':
                        hit = exit_price >= target_price
                    else:  # SELL
                        hit = exit_price <= target_price
                    close_trade(symbol, exit_price, pnl)
                    analyze_learn(symbol, entry_price, exit_price, pnl, margin_per_trade, "Exit", target_price, hit)
                    continue
                
                elif not has_position:
                    decision = get_entry_decision(data, balance)
                    last_api_call[symbol] = time.time()
                    
                    if decision['d'] in ['BUY', 'SELL']:
                        target = decision.get('target', 0.0)
                        save_trade(
                            asset=symbol, 
                            direction=decision['d'],
                            entry_price=data['last'],
                            stop_loss=decision.get('sl', 0.0),
                            take_profit=decision.get('tp', 0.0),
                            reasoning=decision.get('r', 'KI'),
                            indicators=f"5m RSI:{rsi_5m:.1f}",
                            expected_move='Scalp',
                            margin_usd=margin_per_trade,
                            leverage=10,
                            status='ACTIVE',
                            target_price=target  # NEU: Speichern der Prognose
                        )

            if int(time.time()) % 15 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None: last_chat_id = new_id

            time.sleep(2)
        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}", flush=True)
            time.sleep(30)

if __name__ == "__main__":
    main_loop()
