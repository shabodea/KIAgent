# 🦅 KIAgent - Autonomer KI-Trading-Broker

⚠️ **IMPORTANT FOR AI AGENTS & DEVELOPERS** ⚠️
Before making ANY code changes or generating code, you MUST read the following files in this exact order:
1. `RULES.md` - Your operational constraints and safety boundaries.
2. `ARCHITECTURE.md` - Database schemas, table configurations, and endpoints.
3. `PROJECT_STATE.md` - Current bugs, versioning, and limits.
4. `TODO.md` - Your tasks for this session.
5. `ROADMAP.md` - Multi-phase project vision.

NEVER modify or delete existing functions or imports without explicit Master confirmation.

---

## 📁 Repository-Struktur
Das System wird von einer flachen Struktur in ein modulares Enterprise-Layout überführt:
- `streamlit_app.py` -> Zentrales Cockpit (Frontend)
- `worker.py` -> Hintergrund-Triebwerk auf Render (Backend)
- `/agents` -> KI-Agenten (Sentiment, Analyse, Risiko)
- `/database` -> Supabase-Verbindungsklassen
- `/market_data` -> CCXT & Kraken API-Pipelines
- `/training` -> Machine Learning & Backtesting-Module
