import time
import requests
from config.settings import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY

class RateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.tokens = max_requests
        self.last_refill = time.time()

    def allow(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens += elapsed * (self.max_requests / self.window_seconds)
        if self.tokens > self.max_requests:
            self.tokens = self.max_requests
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

class ModelRouter:
    def __init__(self):
        # WICHTIG: Diese Werte entsprechen jetzt den ECHTEN Gratis-Limits der Anbieter
        # (Stand 2026). Die alten Werte (55/45/100 pro Minute) lagen weit ueber den
        # tatsaechlichen kostenlosen Kontingenten und fuehrten dauerhaft zu 429-Fehlern,
        # die dann im Code als Muenzwurf-Fallback endeten.
        self.gemini_limiter = RateLimiter(10, 60)     # Gratis: ca. 10-15 Anfragen/Minute
        self.groq_limiter = RateLimiter(28, 60)        # Gratis: 30 Anfragen/Minute, 1000/Tag (hartes Limit!)
        self.deepseek_limiter = RateLimiter(15, 60)    # nur relevant, falls ein :free-Modell genutzt wird
        self.gemini_key = GEMINI_API_KEY
        self.groq_key = GROQ_API_KEY
        self.openrouter_key = OPENROUTER_API_KEY

    def call_gemini(self, prompt, system_context=""):
        # gemini-2.5-flash-lite hat aktuell das grosszuegigste Gratis-Kontingent.
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash-lite:generateContent?key={self.gemini_key.strip()}"
        full_prompt = f"{system_context}\n\n{prompt}" if system_context else prompt
        try:
            resp = requests.post(url, json={"contents": [{"parts": [{"text": full_prompt}]}]}, timeout=10).json()
            if "error" in resp:
                if "429" in str(resp) or "quota" in str(resp).lower():
                    return None, "RATE_LIMIT"
                return None, f"Gemini Fehler: {resp['error']['message']}"
            return resp['candidates'][0]['content']['parts'][0]['text'], None
        except Exception as e:
            return None, str(e)

    def call_groq(self, prompt, system_context=""):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
        messages = []
        if system_context: messages.append({"role": "system", "content": system_context})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = requests.post(url, headers=headers, json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.7}, timeout=10).json()
            if "error" in resp:
                return None, f"Groq Fehler: {resp['error']['message']}"
            return resp['choices'][0]['message']['content'], None
        except Exception as e:
            return None, str(e)

    def call_deepseek(self, prompt, system_context=""):
        # HINWEIS: DeepSeek-Modelle sind auf OpenRouter seit Mitte 2026 nicht mehr kostenlos.
        # Fuer eine wirklich kostenlose Variante hier ein aktuelles ":free"-Modell eintragen,
        # z.B. "deepseek/deepseek-r1-distill:free" (Verfuegbarkeit vorher auf
        # openrouter.ai/models pruefen - Gratis-Modelle rotieren ohne Vorankuendigung).
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openrouter_key}", "Content-Type": "application/json"}
        messages = []
        if system_context: messages.append({"role": "system", "content": system_context})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = requests.post(url, headers=headers, json={
                "model": "deepseek/deepseek-r1-distill:free",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500  # <-- Entscheidend fuer Kostenkontrolle
            }, timeout=10).json()
            if "error" in resp:
                return None, f"DeepSeek Fehler: {resp['error']['message']}"
            return resp['choices'][0]['message']['content'], None
        except Exception as e:
            return None, str(e)

    def route(self, prompt, system_context="", preferred_model="gemini"):
        kus_models = [
            ("gemini", self.gemini_limiter, self.gemini_key, self.call_gemini),
            ("groq", self.groq_limiter, self.groq_key, self.call_groq),
            ("deepseek", self.deepseek_limiter, self.openrouter_key, self.call_deepseek)
        ]
        
        # 1. Versuche das bevorzugte Modell
        for name, limiter, api_key, func in kus_models:
            if name == preferred_model and api_key:
                if limiter.allow():
                    answer, error = func(prompt, system_context)
                    if answer is not None:
                        return answer, name
                    elif error == "RATE_LIMIT":
                        limiter.tokens = 0  # Hard-Reset
        
        # 2. Fallback durch alle anderen
        for name, limiter, api_key, func in kus_models:
            if name != preferred_model and api_key:
                if limiter.allow():
                    answer, error = func(prompt, system_context)
                    if answer is not None:
                        return answer, name
        
        return "Alle 3 KIs sind voll ausgelastet. Warte auf neues Limit.", "none"
