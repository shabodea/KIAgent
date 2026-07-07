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
        trades, chat, risiko, knowledge = get_all_data_live()
        
        system_kontext = f"""
        Du bist der autonome Chef-Analyst des KIAgent-Handelssystems.
        Du bewohnst das Dashboard und interagierst live mit dem Master.
        
        AKTUELLES SYSTEM-GEDÄCHTNIS:
        - Risikostatus: {str(risiko[:1] if risiko else 'OPEN')}
        - Bekanntes Wissen/Regeln: {str(knowledge)}
        - Offene Positionen: {str(trades[:5] if trades else 'Keine aktiven Trades')}
        """
        
        if not self.api_key:
            print("❌ FEHLER: Kein GEMINI_API_KEY gefunden! Prüfe die Render Environment Variables.", flush=True)
            return "System-Fehler: Mein API-Schlüssel fehlt. Ich bin offline."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key.strip()}"
        prompt_komplett = f"{system_kontext}\n\nMaster-Anweisung: {user_prompt}\n\nAntworte kurz und präzise auf Deutsch als Broker:"
        
        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt_komplett}]}]}, timeout=15).json()
            
            # Falls Google einen Fehler zurückgibt (z.B. falscher Key)
            if "error" in res:
                print(f"❌ Google API Fehler: {res['error']['message']}", flush=True)
                return f"Google API Fehler: {res['error']['message']}"
                
            return res['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"❌ Fehler im Denkprozess (API Error): {str(e)}", flush=True)
            return f"Fehler im Denkprozess: {str(e)}"

    def process_live_chat(self):
        try:
            _, chat, _, _ = get_all_data_live()
            if not chat or len(chat) == 0:
                return

            # SICHERHEITS-FIX: Wir sortieren nach der 'created_at' Zeit! 
            # Das verhindert den tödlichen UUID-Crash.
            sortierter_chat = sorted(chat, key=lambda x: x.get('created_at', ''))
            
            letzte_gesamt_nachricht = sortierter_chat[-1]
            user_nachrichten = [m for m in sortierter_chat if m.get("role") == "user"]
            
            if user_nachrichten:
                letzte_user_nachricht = user_nachrichten[-1]
                
                if letzte_gesamt_nachricht["role"] == "user":
                    user_input = letzte_user_nachricht["content"]
                    
                    print(f"🧠 Agent erkennt neue Nachricht vom Master. Denke nach...", flush=True)
                    
                    ki_antwort = self.execute_thought_cycle(user_input)
                    
                    erfolg = send_chat_message("assistant", ki_antwort)
                    if erfolg:
                        print("✅ KI-Antwort erfolgreich in Supabase gespeichert!", flush=True)
                    else:
                        print("❌ Fehler beim Speichern der KI-Antwort in Supabase!", flush=True)
        except Exception as e:
            # CRITICAL: flush=True hinzugefügt, damit Render den Fehler anzeigt!
            print(f"❌ Kritischer Absturz im Agenten-Chat-Loop: {e}", flush=True)
