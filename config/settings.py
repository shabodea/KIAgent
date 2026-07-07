
import os

# --- DATENBANK (SUPABASE) KONFIGURATION ---
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# --- KRYPTO-BÖRSE (KRAKEN) PARAMETER ---
MAX_TOTAL_BUDGET_USD = 200.0  # Maximales Gesamtkapital im Umlauf
FIXED_LEVERAGE = 10           # Institutioneller Hebelfaktor
BASE_TIMEFRAME = "15m"        # Analyse-Intervall für Indikatoren

# --- KI-Schnittstellen ---
# Der Gemini API Key wird aus Sicherheitsgründen als Umgebungsvariable vom Server geladen
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
