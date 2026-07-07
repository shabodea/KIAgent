
import sys
import os
import requests

# --- SYSTEM-WEGWEISER ---
ZENTRALER_PFAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ZENTRALER_PFAD not in sys.path:
    sys.path.insert(0, ZENTRALER_PFAD)

from config.settings import GEMINI_API_KEY
from database.supabase import get_all_data_live, send_chat_message

class GeminiCoreAgent:
    def __init__(self):
        self.model = "gemini-1.5-flash"
        self.api_key = GEMINI_API_KEY

    def execute_thought_cycle(self, user_prompt):
        """
        Der zentrale Denkzyklus. Gemini liest das gesamte System (Systemzustand, 
        Marktdaten, Trades) und entscheidet, was zu tun ist.
        """
        # 1. Werkzeug: Live-Systemzustand einsaugen
        trades, chat, risiko, knowledge = get_all_data_live()
        
        # 2. Kontext für das Gehirn aufbereiten
        system_kontext = f"""
        Du bist der autonome Chef-Analyst und System-Manager des KIAgent-Handelssystems.
        Du bewohnst das Dashboard und hast die volle Kontrolle über die Interpretation der Abläufe.
        
        AKTUELLES SYSTEM-GEDÄCHTNIS:
        - Risikostatus: {str(risiko[:1] if risiko else 'OPEN')}
        - Bekanntes Wissen/Regeln: {str(knowledge)}
        - Offene/Geschlossene Positionen: {str(trades[:5] if trades else 'Keine aktiven Trades')}
        """
        
        # 3. Anfrage an die Gemini API formulieren
        if not self.api_key:
            return "Fehler: Kein GEMINI_API_KEY in den Server-Umgebungsvariablen gefunden."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key.strip()}"
        
        prompt_komplett = f"{system_kontext}\n\nMaster-Anweisung auf dem Dashboard: {user_prompt}\n\nReagiere als hochentwickelte KI, liefere präzise Analysen oder steuere die nächsten Schritte:"
        
        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt_komplett}]}]}, timeout=15).json()
            antwort = res['candidates'][0]['content']['parts'][0]['text']
            return antwort
        except Exception as e:
            return f"Fehler im Denkprozess des Agenten: {str(e)}"

    def process_live_chat(self):
        """
        Überprüft die Chat-Pipeline und antwortet als intelligenter System-Manager.
        """
        try:
            _, chat, _, _ = get_all_data_live()
            if chat and len(chat) > 0:
                latest_msg = sorted(chat, key=lambda x: x.get('id', 0))[-1]
                
                if latest_msg["role"] == "user":
                    user_input = latest_msg["content"]
                    print(f"🧠 Gemini Agent denkt nach über: {user_input}")
                    
                    # Denkzyklus starten
                    ki_antwort = self.execute_thought_cycle(user_input)
                    
                    # Antwort ins Dashboard zurückschreiben
                    send_chat_message("assistant", ki_antwort)
                    print(f"🧠 Gemini Agent hat geantwortet.")
        except Exception as e:
            print(f"Fehler im Agenten-Chat-Loop: {e}")
