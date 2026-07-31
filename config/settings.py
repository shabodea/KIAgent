import os

# --- DATENBANK (SUPABASE) KONFIGURATION ---
# WICHTIG: Diese Werte kommen jetzt AUSSCHLIESSLICH aus Umgebungsvariablen.
# Trage sie in Render (Environment) und in Streamlit Cloud (Secrets) ein.
# Siehe .env.example fuer die genauen Variablennamen.
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# --- KRYPTO-BÖRSE (KRAKEN) PARAMETER ---
MAX_TOTAL_BUDGET_USD = 100.0   # Virtuelles Paper-Trading-Kapital
FIXED_LEVERAGE = 10            # Institutioneller Hebelfaktor (nur Paper-Trading!)
BASE_TIMEFRAME = "15m"         # Analyse-Intervall fuer Indikatoren

# --- KI-Schnittstellen (alle als Umgebungsvariable, nie im Code) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def _preview(value):
    """Zeigt Laenge + Anfang/Ende eines Werts, OHNE ihn komplett preiszugeben.
    Damit sieht man sofort Tippfehler, Anfuehrungszeichen oder Leerzeichen,
    die beim Kopieren nach Render/Streamlit reingerutscht sind."""
    if not value:
        return "LEER / NICHT GESETZT"
    v = str(value)
    return f"Länge={len(v)}, Start='{v[:12]}...', Ende='...{v[-6:]}', erstes/letztes Zeichen={v[0]!r}/{v[-1]!r}"


print("🔎 Zugangsdaten-Check beim Start (zur Fehlersuche, keine Geheimnisse werden komplett angezeigt):", flush=True)
print(f"   SUPABASE_URL: {_preview(SUPABASE_URL)}", flush=True)
print(f"   SUPABASE_KEY: {_preview(SUPABASE_KEY)}", flush=True)
