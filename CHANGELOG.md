# Projekt-Changelog

## Version 0.1 (Aktueller Stand)
- **Datum:** 2026-07-07
- **Änderungen:** - Daten-Abrufe am Anfang der `streamlit_app.py` zentralisiert (`trades, chat, risiko, knowledge = get_all_data_live()`).
  - Chat-Eingabe auf englische Tabelle `chat_messages` und Sortierung auf Spalte `id` korrigiert.
  - Fehler `StreamlitDuplicateElementId` durch Bereinigung doppelter Code-Reste isoliert.
  - Tabelle `system_knowledge` in Supabase erfolgreich als Dauerspeicher für zukünftige Sitzungen initialisiert.
- **Geänderte Dateien:**
  - `streamlit_app.py`
  - `worker.py`
