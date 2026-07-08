import time
import requests
from config.settings import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY

class RateLimiter:
    """Token-Bucket für Ratenbegrenzung"""
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.tokens = max_requests
        self.last_refill = time.time()

    def allow(self):
        now = time.time()
        # Tokens auffüllen
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
    """
    Verteilt Anfragen auf verschiedene KI-Modelle mit Rate-Limiting.
    """
    def __init__(self):
        self.gemini_limiter = RateLimiter(max_requests=15, window_seconds=60)  # 15/60, sicherheitshalber unter 16
        self.groq_limiter = RateLimiter(max_requests=50, window_seconds=60)    # Groq-Limit meist 50/min
        self.deepseek_limiter = RateLimiter(max_requests=100, window_seconds=60) # OpenRouter meist generös

        # API-Keys
        self.gemini_key = GEMINI_API_KEY
        self.groq_key = GROQ_API_KEY
        self.openrouter_key = OPENROUTER_API_KEY

    def call_gemini(self, prompt, system_context=""):
      url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key.strip()}"
        full_prompt = f"{system_context}\n\n{prompt}" if system_context else prompt
        payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
        try:
            resp = requests.post(url, json=payload, timeout=15).json()
            if "error" in resp:
                return None, f"Gemini API Fehler: {resp['error']['message']}"
            return resp['candidates'][0]['content']['parts'][0]['text'], None
        except Exception as e:
            return None, str(e)

    def call_groq(self, prompt, system_context=""):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_context:
            messages.append({"role": "system", "content": system_context})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.7
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15).json()
            if "error" in resp:
                return None, f"Groq API Fehler: {resp['error']['message']}"
            return resp['choices'][0]['message']['content'], None
        except Exception as e:
            return None, str(e)

    def call_deepseek(self, prompt, system_context=""):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_context:
            messages.append({"role": "system", "content": system_context})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": "deepseek/deepseek-r1",
            "messages": messages,
            "temperature": 0.7
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15).json()
            if "error" in resp:
                return None, f"DeepSeek API Fehler: {resp['error']['message']}"
            return resp['choices'][0]['message']['content'], None
        except Exception as e:
            return None, str(e)

    def route(self, prompt, system_context="", preferred_model="gemini"):
        """
        Wählt das beste verfügbare Modell aus.
        Reihenfolge: Zuerst das bevorzugte Modell, dann Fallback.
        """
        # 1. Versuche das bevorzugte Modell
        if preferred_model == "gemini" and self.gemini_limiter.allow() and self.gemini_key:
            answer, error = self.call_gemini(prompt, system_context)
            if answer is not None:
                return answer, "gemini"
            print(f"⚠️ Gemini fehlgeschlagen: {error}")

        elif preferred_model == "groq" and self.groq_limiter.allow() and self.groq_key:
            answer, error = self.call_groq(prompt, system_context)
            if answer is not None:
                return answer, "groq"
            print(f"⚠️ Groq fehlgeschlagen: {error}")

        elif preferred_model == "deepseek" and self.deepseek_limiter.allow() and self.openrouter_key:
            answer, error = self.call_deepseek(prompt, system_context)
            if answer is not None:
                return answer, "deepseek"
            print(f"⚠️ DeepSeek fehlgeschlagen: {error}")

        # 2. Fallback: Versuche die anderen Modelle (in der Reihenfolge Gemini -> Groq -> DeepSeek)
        if self.gemini_limiter.allow() and self.gemini_key:
            answer, error = self.call_gemini(prompt, system_context)
            if answer is not None:
                return answer, "gemini"
            print(f"⚠️ Gemini (Fallback) fehlgeschlagen: {error}")

        if self.groq_limiter.allow() and self.groq_key:
            answer, error = self.call_groq(prompt, system_context)
            if answer is not None:
                return answer, "groq"
            print(f"⚠️ Groq (Fallback) fehlgeschlagen: {error}")

        if self.deepseek_limiter.allow() and self.openrouter_key:
            answer, error = self.call_deepseek(prompt, system_context)
            if answer is not None:
                return answer, "deepseek"
            print(f"⚠️ DeepSeek (Fallback) fehlgeschlagen: {error}")

        # 3. Notfall: Rückgabe einer Standardantwort
        return "Alle KI-Modelle sind derzeit nicht verfügbar. Bitte später erneut versuchen.", "none"
