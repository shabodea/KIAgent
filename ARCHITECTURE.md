# KI Trading Agent - Software Architektur

## 1. Projektziel
Autonomes KI-System zur Marktanalyse, Strategieentwicklung und Simulation von Trading-Entscheidungen (24/7-Überwachung, Backtesting, Paper-Trading). 
*Wichtig:* Kein unkontrollierter Einsatz von Echtgeld. Maximales Risiko-Management.

## 2. Technologie-Stack
- Frontend: Streamlit Dashboard (`streamlit_app.py`)
- Backend: Python Core (`worker.py`)
- Hosting: Render (Backend), Streamlit Cloud (Frontend)
- Datenbank: Supabase PostgreSQL
- Daten-Pipeline: REST/CCXT (Kraken)
- KI: Gemini API (Modell: gemini-1.5-flash für Chat & Sentiment)

## 3. Projektregeln für die KI (PROMPT-RESTRIKTIONEN)
- **Niemals** bestehenden funktionierenden Code oder imports löschen.
- Keine Funktionen entfernen ohne ausdrückliche Zustimmung.
- Änderungen immer **abwärtskompatibel** und modular durchführen.
- Vor jeder Änderung den vorhandenen Code analysieren.
- Tabellennamen im Schema strikt einhalten: `public.Handelsgeschichte` (Trades), `public.chat_messages` (Chat-Protokoll, Spalten: id, role, content), `public.Risiko_Log` (Tageslimits), `public.system_knowledge` (Master-Gedächtnis).

## 4. Aktuelle Modulstruktur (Version 0.1)
- `streamlit_app.py`: Zentrales Cockpit, Risikomanagement-Anzeige, unblockierte Befehlszeile, Telemetrie-Logbuch.
- `worker.py`: Autonomes Hintergrund-Triebwerk auf Render (Datenbeschaffung, ATR-Positionsberechnung, Chat-Verarbeitung).

## 5. Entwicklungsablauf
1. Architektur prüfen -> 2. Betroffene Module nennen -> 3. Änderung planen -> 4. Modular erweitern -> 5. CHANGELOG.md aktualisieren.
