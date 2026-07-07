# 🏛️ Architektur-Entscheidungen (Architecture Decision Records)

## ADR 1: Chat-Tabelle Name und Struktur
- **Datum:** 2026-07-07
- **Kontext:** Die deutsche Tabelle `Chatnachrichten` führte zu 404-Fehlern im Supabase-Schema-Cache.
- **Entscheidung:** Tabellenname wird permanent auf das englische Äquivalent `chat_messages` fixiert. Die Sortierspalte wird von `Ausweis` auf die Standard-ID `id` umgestellt.
- **Status:** Akzeptiert und im Code implementiert.

## ADR 2: Chat-Input-Feld Entkopplung
- **Datum:** 2026-07-07
- **Kontext:** Platzierung des Chat-Inputs innerhalb von Spalten führte zu Streamlit-Fokusverlusten und Einfrieren.
- **Entscheidung:** Das Eingabefeld wird als seitenweites Element ganz unten platziert und mit einem statischen `key` versehen.
- **Status:** Akzeptiert und implementiert.
