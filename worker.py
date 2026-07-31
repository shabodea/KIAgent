"""
KIAgent Worker - 24/7 Hintergrund-Triebwerk (laeuft auf Render).

Aenderungen gegenueber der alten Version:
- Kein random.choice(['BUY','SELL']) mehr als Fallback -> regelbasiertes
  Konfluenz-Signal (RSI + Kerzenmuster) ist jetzt die primaere Entscheidung.
- Das LLM wird nur noch zur Bestaetigung/Begruendung genutzt (kein
  Rate-Limit-Stress mehr, kein Zufall).
- Jede Analyse (auch HOLD) wird ins Denkprotokoll (bot_thoughts) geschrieben,
  damit das Dashboard zeigt, was der Bot gerade prueft.
- Der Live-Chat wird jetzt TATSAECHLICH verarbeitet (vorher toter Code:
  agent.process_live_chat() wurde nie aufgerufen).
- Alle 6h wird automatisch mit den bisherigen Trades nachtrainiert
  (kein zusaetzlicher, kostenpflichtiger Render-Cron-Job noetig).
- Meilenstein-Meldung, sobald >=200 Trades UND >=70% Trefferquote.
- Eine einzige, wiederverwendete Kraken-Verbindung statt einer neuen
  Instanz pro Symbol/Aufruf (vorher: Rate-Limit-Risiko bei Kraken).
"""
import time
import requests

from agents.model_router import ModelRouter
from agents.gemini_agent import GeminiCoreAgent
from database.supabase import (
    send_chat_message, save_trade, close_trade,
    get_current_balance_and_winrate, log_thought, check_and_notify_milestone,
)
from market_data.collector import get_valid_assets, fetch_ohlcv_df
from market_data.indicators import rsi_wilder
from strategies.trend import confluence_signal
from memory.experience_memory import log_trade_features
from training.trainer import retrain_model_from_history, load_model_coefficients, predict_win_probability
from config.settings import SUPABASE_URL, HEADERS, MAX_TOTAL_BUDGET_USD, FIXED_LEVERAGE

MONITORED_ASSETS_RAW = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRX-USD",
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD",
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "NIGHT-USD",
]

ENTRY_COOLDOWN_SECONDS = 20     # nicht bei jedem 1-Sekunden-Tick pro Symbol neu einsteigen
RETRAIN_INTERVAL_SECONDS = 6 * 3600
EXIT_RSI_LOW, EXIT_RSI_HIGH = 20, 80


def get_open_position(symbol):
    trades = requests.get(
        f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,Eintrittspreis,Richtung"
        f"&Vermögenswert=eq.{symbol}&Status=eq.ACTIVE",
        headers=HEADERS,
    ).json()
    if isinstance(trades, list) and trades:
        return trades[0]
    return None


def main_loop():
    print("🚀 KIAgent 24/7 - regelbasierte Analyse + Lernschleife gestartet.", flush=True)

    valid_assets = get_valid_assets(MONITORED_ASSETS_RAW)
    print(f"✅ {len(valid_assets)}/{len(MONITORED_ASSETS_RAW)} Assets bei Kraken bestaetigt: {valid_assets}", flush=True)

    agent = GeminiCoreAgent()
    router = ModelRouter()
    last_chat_id = 0
    last_retrain = 0.0
    last_entry_call = {a: 0.0 for a in valid_assets}
    model_coeffs = load_model_coefficients()

    while True:
        try:
            balance, winrate, total_closed = get_current_balance_and_winrate(base_balance=MAX_TOTAL_BUDGET_USD)
            check_and_notify_milestone(total_closed, winrate)

            kelly = max(0.0, (2 * winrate) - 1)
            risk_pct = max(0.005, min(0.03, kelly * 0.05))

            for symbol in valid_assets:
                df_15m = fetch_ohlcv_df(symbol, "15m", 100)
                df_1h = fetch_ohlcv_df(symbol, "1h", 100)
                if df_15m.empty or df_1h.empty:
                    continue

                last_price = float(df_15m["close"].iloc[-1])
                position = get_open_position(symbol)

                signal = confluence_signal(df_1h, df_15m)
                log_thought(symbol, signal["direction"], signal["confidence"], signal["reasons"])

                # --- Offene Position: nur pruefen, ob Exit-Bedingung erreicht ist ---
                if position:
                    entry = float(position["Eintrittspreis"])
                    direction = position.get("Richtung", "BUY")
                    rsi_15m = signal["rsi_15m"]

                    if rsi_15m > EXIT_RSI_HIGH or rsi_15m < EXIT_RSI_LOW:
                        pnl = (last_price - entry) / entry * balance * risk_pct * FIXED_LEVERAGE
                        if direction == "SELL":
                            pnl *= -1
                        close_trade(symbol, last_price, pnl)

                        lesson_prompt = (
                            f"Trade {symbol} {'GEWINN' if pnl > 0 else 'VERLUST'} ${pnl:.2f}. "
                            f"RSI15m:{rsi_15m:.1f}. Was lerne ich daraus? 1 Satz."
                        )
                        lesson, _ = router.route(lesson_prompt, system_context="Du bist ein Trading-Coach.", preferred_model="gemini")
                        send_chat_message("system", f"📘 ML-Lektion: {lesson}")
                    continue

                # --- Keine offene Position: pruefen, ob ein Einstieg sinnvoll ist ---
                if time.time() - last_entry_call.get(symbol, 0) < ENTRY_COOLDOWN_SECONDS:
                    continue

                if signal["direction"] not in ("BUY", "SELL") or signal["confidence"] < 0.5:
                    continue

                last_entry_call[symbol] = time.time()

                win_prob = predict_win_probability(model_coeffs, [
                    signal["rsi_1h"], signal["rsi_15m"], signal["confidence"], signal["confidence"],
                ])
                if model_coeffs and win_prob < 0.55:
                    log_thought(symbol, "HOLD", signal["confidence"],
                                signal["reasons"] + [f"vom Modell abgelehnt (P={win_prob:.2f})"])
                    continue

                comment, _ = router.route(
                    f"{symbol}: Regelbasiertes Signal {signal['direction']} "
                    f"(Gruende: {signal['reasons']}). Kurze Begruendung in 1 Satz.",
                    system_context="Du bist Chef-Analyst. Antworte in 1 kurzem Satz.",
                    preferred_model="gemini",
                )

                margin = balance * risk_pct
                save_trade(
                    symbol, signal["direction"], last_price, 0, 0, comment,
                    f"15m:{signal['rsi_15m']:.1f}, 1h:{signal['rsi_1h']:.1f}",
                    "Konfluenz", margin, FIXED_LEVERAGE, "ACTIVE", last_price * 1.005,
                )

                new_trade = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id&Vermögenswert=eq.{symbol}"
                    f"&Status=eq.ACTIVE&order=id.desc&limit=1",
                    headers=HEADERS,
                ).json()
                if isinstance(new_trade, list) and new_trade:
                    log_trade_features(
                        new_trade[0]["id"], signal["rsi_1h"], signal["rsi_15m"],
                        signal["confidence"], signal["confidence"],
                    )

            # --- Live-Chat verarbeiten (vorher nie aufgerufen!) ---
            new_id = agent.process_live_chat(last_chat_id)
            if new_id:
                last_chat_id = new_id

            # --- Periodisches Nachtraining, ohne zusaetzlichen Render-Cron-Job ---
            if time.time() - last_retrain > RETRAIN_INTERVAL_SECONDS:
                new_coeffs = retrain_model_from_history()
                if new_coeffs:
                    model_coeffs = new_coeffs
                last_retrain = time.time()

            time.sleep(20)

        except Exception as e:
            print(f"❌ Fehler in main_loop: {e}", flush=True)
            time.sleep(30)


if __name__ == "__main__":
    main_loop()
