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

# KI Trading Agent - Software Architektur & Master-Gedächtnis

## 1. Projektziel
Ein absolut autonomes KI-System zur Krypto-Marktanalyse, algorithmischen Strategieentwicklung und Simulation von Trading-Entscheidungen (24/7-Überwachung, Backtesting, Paper-Trading).
*Wichtig:* Striktes Risiko-Management. Kein unkontrollierter Einsatz von Kapital.

## 2. Server- & Host-Infrastruktur
- **Frontend (Das Cockpit):** Läuft auf Streamlit Cloud über die Datei `streamlit_app.py`.
- **Backend (Das Triebwerk):** Läuft als autonomer Dauerprozess auf Render über die Datei `worker.py`.
- **Datenbank:** Supabase PostgreSQL. Beide Systeme (Render & Streamlit) kommunizieren in Echtzeit über die Supabase REST-API.
- **Daten-Pipeline:** CCXT-Anbindung an die Krypto-Börse **Kraken**.

## 3. Technische API-Verbindungsdaten
WICHTIG: Supabase-URL und -Key stehen ab sofort NICHT MEHR im Klartext in diesem
Repository. Sie werden ausschließlich als Umgebungsvariablen gesetzt:
- In Render: Dashboard -> Environment -> `SUPABASE_URL`, `SUPABASE_KEY`
- In Streamlit Cloud: App Settings -> Secrets -> `SUPABASE_URL`, `SUPABASE_KEY`
Siehe `.env.example` im Projekt-Root für die exakten Variablennamen.
Grund: Ein zuvor hier hinterlegter Klartext-Key wäre für jeden lesbar gewesen,
der dieses (ggf. öffentliche) Repository einsieht.
  ```json
  {
    "apikey": "<aus Umgebungsvariable SUPABASE_KEY>",
    "Authorization": "Bearer <aus Umgebungsvariable SUPABASE_KEY>",
    "Content-Type": "application/json"
  }
# 📐 KI Trading Agent – Architektur & Systemdokumentation

## 1. Projektübersicht
Autonomer KI-Trading-Agent für **24/7 Paper-Trading** auf Kraken (Krypto-Assets). 
Das System verfolgt eine **Machine-Learning-Explorationsstrategie**, bei der der Bot ohne starre RSI-Grenzen handelt, um massiv Daten zu sammeln. Ziel: Eine Trefferquote von >75% durch selbstständiges Erlernen optimaler Ein- und Ausstiegspunkte.

---

## 2. Technologie-Stack & Hosting
- **Frontend (Dashboard):** Streamlit (Cloud, 0.5 CPU / 512 MB RAM)
- **Backend (Worker):** Python (Render, 0.5 CPU / 512 MB RAM)
- **Datenbank:** Supabase PostgreSQL 
- **Marktdaten:** CCXT (Kraken API) – Live-Kurse & Orderbücher (keine Aktien mehr, nur 19 Krypto-Assets)
- **KI-Modelle:** OpenRouter (DeepSeek-R1 als Hauptmodell), Gemini (als Chat-Fallback) und Groq (als Trading-Fallback)

---

## 3. KI-Router & Modell-Nutzung (`agents/model_router.py`)
Das System nutzt eine `ModelRouter`-Klasse mit intelligentem Rate-Limiting, um die 3 KI-Modelle effizient zu verteilen:

| KI-Modell | Primärer Zweck | Rate-Limit | Kosten |
|-----------|----------------|------------|--------|
| **DeepSeek (OpenRouter)** | Trading-Entscheidungen, Begründungen, Post-Trade-Lektionen & Chat | ~100 Anfragen/min | 8 $ Guthaben (Reicht für > 300.000 Trades) |
| **Gemini (Google)** | Chat-Fallback (schnelle Antworten) | 60 Anfragen/min | Kostenlos |
| **Groq** | Trading-Fallback (wenn DeepSeek ausfällt) | 50 Anfragen/min | Kostenlos (Token-Tageslimit) |

---

## 4. Kernlogik: Machine-Learning-Exploration (`worker.py`)
Der Bot handelt nach einer **"Pure ML Exploration"**-Logik:

1. **Keine festen RSI-Regeln:** Der Bot handelt nicht nach starren Schwellenwerten.
2. **Zufällige & KI-gestützte Einstiege:** Er fragt DeepSeek nach einer Entscheidung. Falls DeepSeek zögert oder keine Richtung angibt, **würfelt der Bot** (`random.choice(['BUY', 'SELL'])`), um Daten für das Training zu generieren.
3. **Risikomanagement (fest):** 
   - **Hebel:** 10x (fest)
   - **Risiko pro Trade:** 2 % des aktuellen Guthabens (bei 10x Hebel = max. 20 % Verlust pro Trade).
4. **Ausstieg (Exit):** Der Bot steigt aus, wenn der 5-Minuten-RSI extreme Werte erreicht (> 80 oder < 20), oder wenn das von DeepSeek berechnete Kursziel (`target_price`) erreicht wurde.
5. **Selbstreflexion (Lernen):** Nach jedem geschlossenen Trade schickt DeepSeek eine 1-Satz-Lektion in den Chat, die genau analysiert, *welcher RSI-Bereich zu einem Gewinn oder Verlust geführt hat*.

---

## 5. Datenbank-Schema (Supabase)

### Tabelle: `public.Handelsgeschichte`
*Optimiert für das ML-Dashboard mit Prognose-Tracking:*

| Spaltenname | Typ | Beschreibung |
|-------------|-----|--------------|
| `id` | Integer | Primärschlüssel (Auto-Increment) |
| `Vermögenswert` | Text | Asset-Ticker (z.B. BTC-USD) |
| `Richtung` | Text | BUY / SELL |
| `Eintrittspreis` | Numeric | Preis beim Einstieg |
| `Stop_Loss_Preis` | Numeric | SL-Preis |
| `Take_Profit_Preis` | Numeric | TP-Preis |
| `target_price` | Numeric | **Neu:** Erwarteter Kurs (Prognose) |
| `Austrittspreis` | Numeric | **Neu:** Tatsächlicher Preis beim Schließen |
| `net_pnl` | Numeric | Gewinn/Verlust in USD |
| `Begründung` | Text | Begründung des Trades |
| `Indikatoren_Setup` | Text | RSI-Werte beim Einstieg (Format: `5m:45.1, 15m:...`) |
| `Erwartete_Bewegung` | Text | Scalping / Exploration |
| `Marge in USD` | Numeric | Investierte Marge |
| `Hebelwirkung` | Integer | Fester Hebel (10) |
| `Status` | Text | ACTIVE / CLOSED / PAPER |

### Tabelle: `public.chat_messages`
Speichert Chatverläufe und die ML-Lektionen des Bots:
- `id` (Integer), `role` (Text: user/system/assistant), `content` (Text)

### Tabelle: `public.system_knowledge`
- `id` (Integer), `kategorie` (Text), `inhalt` (Text) – für das Langzeitgedächtnis des Bots.

---

## 6. Dashboard: `streamlit_app.py` (Maximale Übersicht)
Das Cockpit ist so gestaltet, dass du sofort erkennst, ob das System lernt:

- **Live-Übersicht (5 Zeitfenster):** Zeigt 5m, 15m, 1h, 4h, 1d mit RSI-Werten und Signalen (`LONG` = 🟢 Grün, `SELL` = 🔴 Rot, `HOLD` = 🟠 Orange). Die RSI-Trendpfeile (⬆️⬇️) zeigen die Richtung des RSIs an.
- **ML-Einblicke (MVP):** Unten im Dashboard berechnet der Bot live den **durchschnittlichen RSI-Wert bei Gewinnen** und den **durchschnittlichen RSI-Wert bei Verlusten**. So siehst du genau, welche RSI-Zone er für die einzelnen Assets langsam als „optimal“ erkennt.
- **Prognose-Check:** Bei geschlossenen Trades wird der `Eintrittspreis`, der `target_price`, der `Austrittspreis` und das Ergebnis der Prognose (✅ JA / ❌ NEIN) angezeigt.
- **Live-Reflexion:** Zeigt die letzten „Selbstreflexionen“ des Bots, die er nach dem Schließen eines Trades generiert hat.

---

## 7. Aktuelle Asset-Liste (Nur Kraken)
Der Bot überwacht folgende 19 Krypto-Assets 24/7:
BTC-USD, XRP-USD, SOL-USD, ETH-USD, DOGE-USD, ZEC-USD, TRX-USD,
PAXG-USD, RENDER-USD, FET-USD, PEPE-USD, QNT-USD, WLD-USD,
LINK-USD, SUI-USD, NIL-USD, TAO-USD, NIGHT-USD


---

## 8. Entwicklungsablauf & Wartungsregeln (Für die KI)
- **Speicher und Kontext:** Der Bot vergisst nichts. Alle Trades, Fehler und Erfolge bleiben in der Supabase-Datenbank gespeichert und werden für die ML-Analyse genutzt.
- **Kostenmanagement:** 
  - Render: 7 $/Monat.
  - OpenRouter (DeepSeek): 8 $ aufgeladen. Durch die Beschränkung auf `max_tokens=500` pro Anfrage reicht das Guthaben für über 300.000 Trades.
- **Upgrade-Pfad:** Sobald der Bot im Paper-Trading eine Trefferquote von 75 % über mindestens 200 Trades erreicht, wird die Logik um einen echten `create_market_order()`-Befehl an die Kraken-API erweitert (Echtgeld-Modus).

---

## 9. Dateistruktur (Stand: Finaler ML-Build)
```text
/root
├── worker.py                 # Hauptschleife (ML-Exploration, DeepSeek-Logik)
├── streamlit_app.py           # Dashboard (Farbcodiert, ML-Analysen)
├── agents/
│   ├── model_router.py        # 3-KI-Wrapper & Rate-Limiter
│   └── gemini_agent.py        # Chat-Logik
├── database/
│   └── supabase.py            # Verbindung, save_trade, close_trade (mit target/Austrittspreis)
├── config/
│   └── settings.py            # API-Keys, Supabase-URLs
├── requirements.txt           # streamlit, pandas, ccxt, numpy, requests, openai, yfinance
└── ARCHITECTURE.md            # Diese Dokumentation

