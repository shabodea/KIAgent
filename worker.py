import os
import time
import requests

# Schlüssel und Datenbank-Konfiguration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Exakte Kraken Gebührenstruktur (Standard Taker-Gebühr für Spot/Futures)
KRAKEN_TAKER_FEE = 0.0026  # 0.26%

def get_live_kraken_markets():
    """Holt alle aktiven USDT-Handelspaare live von Kraken"""
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url, timeout=10).json()
        all_pairs = res.get("result", {})
        # Wir filtern alle echten USDT-Märkte für den globalen Scan heraus
        return [pair for pair in all_pairs.keys() if pair.endswith("USDT")]
    except Exception as e:
        print(f"❌ Fehler beim Abruf der Marktliste: {e}")
        return ["XBTUSDT", "ETHUSDT", "SOLUSDT"]

def get_orderbook_metrics(pair):
    """
    Fragt das echte Live-Orderbuch von Kraken ab und analysiert die Liquidität.
    Berechnet das Ask/Bid-Verhältnis (Verkaufsdruck vs. Kaufdruck).
    """
    try:
        url = f"https://api.kraken.com/0/public/Depth?pair={pair}&count=20"
        res = requests.get(url, timeout=10).json()
        
        # Kraken gibt das Ergebnis oft mit dem internen Alternativnamen zurück
        pair_data = list(res.get("result", {}).values())[0]
        
        bids = pair_data.get("bids", [])  # Kaufaufträge [[Preis, Volumen, Zeit], ...]
        asks = pair_data.get("asks", [])  # Verkaufsaufträge
        
        if not bids or not asks:
            return None
            
        # Live-Preis (Mittelwert aus bestem Gebot und bestem Angebot)
        best_bid = float(bids[0][0])
        best_ask = asks[0][0] # Manchmal String, wir wandeln es sicher um
        live_price = (best_bid + float(best_ask)) / 2
        
        # Mathematische Orderbuchtiefe berechnen (kumuliertes Volumen der Top 20 Orders)
        total_bid_volume = sum(float(bid[1]) for bid in bids)
        total_ask_volume = sum(float(ask[1]) for ask in asks)
        
        # Orderbuch-Verhältnis (Werte > 1 bedeuten mehr Kaufdruck als Verkaufsdruck)
        orderbook_ratio = total_bid_volume / total_ask_volume if total_ask_volume > 0 else 1
        
        return {
            "live_price": live_price,
            "bid_depth": total_bid_volume,
            "ask_depth": total_ask_volume,
            "ratio": round(orderbook_ratio, 2)
        }
    except Exception as e:
        print(f"⚠️ Konnte Orderbuch für {pair} nicht lesen: {e}")
        return None

def ask_gemini_expert(prompt_text):
    """Verbindung zum aktuellen Gemini-Gehirn für die finale Filterung"""
    if not GEMINI_API_KEY:
        return "⚠️ Key fehlt"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY.strip()}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "HOLD"

def execute_live_market_analysis():
    """Der Kernprozess: Scannt den echten Markt, filtert mathematisch und entscheidet"""
    try:
        # Gelerntes Wissen laden
        mem_res = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()
        learned_context = ", ".join(mem_res[0].get("learned_lessons", [])) if mem_res else ""

        # Echten Markt holen
        all_pairs = get_live_kraken_markets()
        print(f"🧠 Experten-Scan: Analysiere den gesamten Kraken-Markt ({len(all_pairs)} Paare)...")

        # Wir prüfen die Märkte nacheinander auf echte Orderbuch-Ineffizienzen
        for pair in all_pairs[:30]:  # Wir scannen die ersten 30 liquiden Paare tiefgehend
            metrics = get_orderbook_metrics(pair)
            if not metrics:
                continue
                
            # Erster mathematischer Filter vor dem KI-Einsatz: 
            # Wir triggern ein Signal nur, wenn das Orderbuch ein klares Ungleichgewicht (Kaufdruck) zeigt
            if metrics["ratio"] > 1.5: 
                print(f"🎯 Auffälliges Orderbuch-Ungleichgewicht bei {pair}! Ratio: {metrics['ratio']}")
                
                # Exakte Gebührenberechnung für einen Test-Einsatz von z.B. 100 USD Margin
                test_margin = 100.0
                estimated_fees = test_margin * KRAKEN_TAKER_FEE * 2 # Einstieg + Ausstieg
                
                expert_prompt = (
                    f"Du bist der unfehlbare Krypto-Trading-Experte. Dein Gedächtnis: {learned_context}.\n"
                    f"Asset: {pair} | Aktueller Live-Preis: {metrics['live_price']}\n"
                    f"Echtes Orderbuch-Verhältnis (Kauf-/Verkaufsdruck): {metrics['ratio']} (Werte > 1.5 sind stark bullisch).\n"
                    f"Berechnete Kraken-Gebühren für diesen Trade: {estimated_fees} USD.\n"
                    f"Aufgabe: Lohnt sich hier ein schneller, profitabler Long-Trade, um die Gebühren weit zu übertreffen?\n"
                    "Antworte strikt mit 'GO: [Deine Begründung]' oder 'HOLD'."
                )
                
                decision = ask_gemini_expert(expert_prompt)
                
                if "GO:" in decision:
                    rationale_text = decision.split("GO:")[-1].strip()
                    
                    trade_payload = {
                        "asset": pair,
                        "direction": "LONG",
                        "leverage": 5, # Moderater Hebel für den Anfang
                        "entry_price": metrics["live_price"],
                        "margin_usd": test_margin,
                        "fees_usd": estimated_fees,
                        "status": "ACTIVE",
                        "rationale": f"[Live-Orderbuch Analyse] {rationale_text}"
                    }
                    
                    # In Supabase loggen und Trade abspeichern
                    requests.post(f"{SUPABASE_URL}/rest/v1/trade_history", headers=HEADERS, json={
                        "role": "assistant",
                        "content": f"🔥 Live-Orderbuch-Ausbruch erkannt bei {pair}! Ratio: {metrics['ratio']}. Trade gestartet."
                    })
                    requests.post(f"{SUPABASE_URL}/rest/v1/trade_history", headers=HEADERS, json=trade_payload)
                    print(f"🟢 EXPERTEN-TRADE ERÖFFNET: {pair} zu {metrics['live_price']}")
                    break # Einen Trade nach dem anderen abwickeln
                    
            time.sleep(1) # Schonung der API-Rate-Limits
            
    except Exception as e:
        print(f"Fehler im Analyse-Loop: {e}")

def process_chat():
    try:
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS).json()
        if messages and len(messages) > 0:
            latest_msg = sorted(messages, key=lambda x: x.get('id', 0))[-1]
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                system_context = "Du bist der unfehlbare Krypto-Trading-Experte. Antworte kurz, präzise und professionell auf Deutsch. Beende mit LEKTION: ..."
                bot_response = ask_gemini_expert(f"{system_context}\n\nMaster schreibt: {user_input}")
                requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={"role": "assistant", "content": bot_response})
    except Exception as e:
        print(f"Fehler im Chat-Check: {e}")

# --- HAUPTPROGRAMM ---
print("🦅 Experten-Triebwerk Stufe 1 läuft live und ununterbrochen...")
while True:
    process_chat()
    execute_live_market_analysis()
    time.sleep(15)
