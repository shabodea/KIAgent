# Projekt-Changelog

## Version 0.3 (Regelbasierte Analyse + Lernschleife)
- **Datum:** 2026-07-31
- **Sicherheit:** Supabase-Key aus ARCHITECTURE.md entfernt, SUPABASE_URL/SUPABASE_KEY
  in config/settings.py auf Umgebungsvariablen umgestellt (.env.example ergaenzt).
- **Kritischer Bugfix:** `call_groq` und `call_deepseek` in `agents/model_router.py`
  haben den Auth-Header gebaut, aber nie an `requests.post` uebergeben -> beide
  Modelle liefen bisher immer auf 401/Fehler und fielen sofort auf den naechsten
  Fallback zurueck.
- **Kritischer Bugfix:** `agent.process_live_chat()` wurde in `worker.py` nie
  aufgerufen -> der Dashboard-Chat konnte technisch nicht funktionieren.
- **Kern-Umbau:** `random.choice(['BUY','SELL'])`-Fallback entfernt. Neue Module
  `market_data/indicators.py` (RSI/EMA/MACD/Bollinger/ATR + Kerzenmuster),
  `market_data/collector.py` (eine wiederverwendete ccxt-Verbindung mit
  Rate-Limit statt neuer Instanz pro Aufruf) und `strategies/trend.py`
  (regelbasiertes Konfluenz-Signal) ersetzen die vorherigen Leerdateien.
- **Lernschleife:** `memory/experience_memory.py` + `training/trainer.py`
  implementiert (Feature-Logging pro Trade, Logistische Regression,
  Nachtraining alle 6h direkt im Worker, Koeffizienten in `system_knowledge`
  statt auf dem fluechtigen Render-Dateisystem gespeichert).
- **Neue Supabase-Tabellen:** `bot_thoughts` (Denkprotokoll), `trade_features`
  (Grundlage fuer das Training) - siehe `supabase_setup_v2.sql`.
- **Dashboard:** Live-Denkprotokoll und Trefferquote-Verlauf ergaenzt.
- **Modelle:** Gemini auf `gemini-2.5-flash-lite` umgestellt, Rate-Limiter auf
  reale Gratis-Kontingente korrigiert, DeepSeek-Modell auf ein `:free`-Modell
  umgestellt (OpenRouter fuehrt DeepSeek seit Mitte 2026 nur noch kostenpflichtig).
- **Aufgeraeumt:** `agents/__init__py` -> `agents/__init__.py`, `requirements.txt`
  bereinigt (yfinance/doppeltes requests/openai entfernt, scikit-learn ergaenzt).
- **Geänderte/neue Dateien:** `worker.py`, `streamlit_app.py`, `config/settings.py`,
  `agents/model_router.py`, `database/supabase.py`, `market_data/indicators.py`,
  `market_data/collector.py`, `strategies/trend.py`, `memory/experience_memory.py`,
  `training/trainer.py`, `ARCHITECTURE.md`, `requirements.txt`, `.env.example`,
  `supabase_setup_v2.sql`.

## Version 0.1 (Aktueller Stand)
- **Datum:** 2026-07-07
- **Änderungen:** - Daten-Abrufe am Anfang der `streamlit_app.py` zentralisiert (`trades, chat, risiko, knowledge = get_all_data_live()`).
  - Chat-Eingabe auf englische Tabelle `chat_messages` und Sortierung auf Spalte `id` korrigiert.
  - Fehler `StreamlitDuplicateElementId` durch Bereinigung doppelter Code-Reste isoliert.
  - Tabelle `system_knowledge` in Supabase erfolgreich als Dauerspeicher für zukünftige Sitzungen initialisiert.
- **Geänderte Dateien:**
  - `streamlit_app.py`
  - `worker.py`
