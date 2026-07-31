# 📝 Aktuelle offene Aufgaben (TODO.md)

*Hinweis für die KI: Dieses Dokument muss nach jeder erfolgreichen Sitzung aktualisiert werden.*

## 🛑 Von dir manuell zu erledigen (kein Code-Fix moeglich, braucht deine Zugangsdaten)
- [ ] `supabase_setup_v2.sql` einmalig im Supabase SQL-Editor ausfuehren.
- [ ] `.env.example` als Vorlage nutzen: GEMINI_API_KEY, GROQ_API_KEY, SUPABASE_URL,
      SUPABASE_KEY in Render (Environment) UND Streamlit Cloud (Secrets) eintragen.
- [ ] Kostenlose API-Keys besorgen: aistudio.google.com (Gemini), console.groq.com (Groq).
- [ ] Nach dem Push: Render-Logs beobachten, ob der Worker fehlerfrei startet.

## ⚙️ Sinnvolle naechste Ausbaustufen
- [ ] Backtesting-Modul (`backtesting/backtester.py`) bauen, um die Konfluenz-Strategie
      auf historischen Daten zu pruefen, bevor man dem Paper-Trading-Ergebnis traut.
- [ ] `Risiko_Log`-Tabelle tatsaechlich befuellen (wird aktuell nur gelesen, nie beschrieben)
      + Tagesverlust-Notbremse einbauen.
- [ ] Mehr Timeframes/Indikatoren in `strategies/trend.py` einbeziehen (aktuell RSI 1h/15m
      + ein Kerzenmuster-Score), sobald genug Trainingsdaten vorhanden sind.
