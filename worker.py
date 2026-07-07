import os
import json
import re
from openai import OpenAI

# 1. API-Key Konfiguration
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "")

# 2. Client Initialisierung (OHNE die Klammer, die den Fehler verursacht)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1"
)

# 3. Funktion
def get_trading_decision(market_data):
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1",
            messages=[
                {"role": "system", "content": "Antworte NUR mit JSON: {'decision': 'BUY/SELL/HOLD', 'reasoning': '...'}"},
                {"role": "user", "content": f"Marktdaten: {market_data}"}
            ]
        )
        content = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"decision": "HOLD", "reasoning": "Kein JSON gefunden"}
    except Exception as e:
        print(f"Fehler: {e}")
        return {"decision": "HOLD", "reasoning": "Fehler"}
import time

# ... (dein restlicher Code mit der get_trading_decision Funktion) ...

if __name__ == "__main__":
    print("🚀 Genie-Modus aktiviert. Warte auf Marktdaten...")
    while True:
        try:
            # Hier holst du deine Daten
            # market_data = get_live_data() 
            
            # Hier triffst du die Entscheidung
            # decision = get_trading_decision(market_data)
            
            # Hier schreibst du in Supabase
            # ...
            
            print("Zyklus abgeschlossen. Warte 60 Sekunden...")
            time.sleep(60) # Der Bot macht eine Minute Pause, damit er nicht rattert
            
        except Exception as e:
            print(f"Fehler im Loop: {e}")
            time.sleep(10) # Bei Fehler kurz warten und neu versuchen
