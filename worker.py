import os
import time
import requests
from datetime import datetime

# Schlüssel aus dem Render-Tresor laden
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def ask_gemini(prompt_text):
    """Verbindet den Server direkt mit dem echten Google-Gemini-Gehirn"""
    if not GEMINI_API_KEY:
        return "⚠️ Fehler: Kein GEMINI_API_KEY auf Render hinterlegt! Bitte trage ihn in den Umgebungsvariablen ein."
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        res_json = response.json()
        return res_json['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Ausfall im KI-Kortex: {str(e)}"

def process_chat_and_learning():
    """Liest deine Chat-Nachrichten, antwortet via Gemini und speichert gelerntes Wissen"""
    messages = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS).json()
    
    if messages:
        # Sortiert nach ID, um die allerneueste Nachricht zu finden
        latest_msg = sorted(messages, key=lambda x: x.get('id', 0))[-1]
        
        # Wenn die letzte Nachricht von DIR (User) kam, muss die KI antworten!
        if latest_msg["role"] == "user":
            user_input = latest_msg["content"]
            print(f"📥 Neuer Input von Mama empfangen: '{user_input}'")
            
            # Das Gehirn wird mit System-Anweisungen gefüttert, um als Trading-Genie zu agieren
            system_context = (
                "Du bist der autonome 10x Krypto-Trading-Agent. Du filterst das Wissen, das dir dein "
                "Master (User) gibt, ab, lernst daraus für deine künftigen Strategien und antwortest hochprofessionell, "
                "präzise und interaktiv. Formuliere am Ende deiner Antwort immer eine ultrakurze Kern-Lektion (max. 1 Satz), "
                "die mit 'LEKTION:' beginnt."
            )
            
            full_prompt = f"{system_context}\n\nMaster schreibt: {user_input}"
            
            # Gemini berechnet die Antwort
            bot_response = ask_gemini(full_prompt)
            
            # 1. Antwort in den Chat schreiben
            requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={
                "role": "assistant",
                "content": bot_response
            })
            print("📤 Antwort erfolgreich im Chat gesendet!")
            
            # 2. Evolution: Extrahiere die Lektion und brenne sie ins unendliche Gedächtnis
            if "LEKTION:" in bot_response:
                lesson = bot_response.split("LEKTION:")[-1].strip()
                
                # Holt das aktuelle Gedächtnis, um es zu erweitern
                mem = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()[0]
                current_lessons = mem.get("learned_lessons", [])
                
                # Füge die neue Lektion hinzu (limitiert auf die letzten 10, um die Sidebar sauber zu halten)
                if lesson not in current_lessons:
                    current_lessons.append(lesson)
                    requests.patch(f"{SUPABASE_URL}/rest/v1/bot_memory?id=eq.1", headers=HEADERS, json={
                        "learned_lessons": current_lessons[-10:]
                    })
                    print(f"💾 Evolution: Neue Lektion im Gedächtnis verankert: {lesson}")

def calculate_indicators_and_trade():
    """Dauerschleife für den Multi-Timeframe-Scan der Kraken-Derivate"""
    # Hier fügen wir später die echten mathematischen Formeln für RSI und EMA ein
    pass

# --- HAUPTPROGRAMM ---
print("🦅 Die voll funktionsfähige KI-Maschine läuft jetzt 24/7...")

while True:
    try:
        # Checke im Sekundentakt, ob du ihm im Chat geschrieben hast
        process_chat_and_learning()
        time.sleep(2)
    except Exception as e:
        print(f"Fehler im Hauptprozess: {e}")
        time.sleep(5)
