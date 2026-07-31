"""
KIAgent Worker - 24/7 Hintergrund-Triebwerk (laeuft auf Render).

Neu in dieser Version:
- JEDE Netzwerk-Anfrage hat jetzt ein Zeitlimit (Timeout). Vorher konnte eine
  einzige haengende Verbindung (Kraken oder Supabase) den kompletten Worker
  fuer immer blockieren, komplett ohne Fehlermeldung - das sah im Render-Log
  wie ein "Stillstand ohne Grund" aus.
- Sichtbare Fortschritts-Ausgabe pro Analyse-Runde, damit im Log erkennbar
  ist, dass der Bot aktiv arbeitet (statt Stille = Unsicherheit, ob er haengt).
- 5 Zeitfenster (5m/15m/1h/4h/1d) pro Asset -> immer aktueller Snapshot
  (market_snapshot) fuer das Profi-Dashboard.
- Explorations-Modus: nimmt bewusst auch schwaechere Signale als kleinere
  Trades mit, um schneller Trainingsdaten zu sammeln (reines Paper-Trading).
"""
import time
import random
import requests

from agents.model_router import ModelRouter
from agents.gemini_agent import GeminiCoreAgent
from database.supabase import (
    send_chat_message, save_trade, close_trade,
    get_current_balance_and_winrate, log_thought, check_and_notify_milestone,
    upsert_market_snapshot,
)
from market_data.collector import get_valid_assets, fetch_ohlcv_df
from market_data.indicators import rsi_wilder
from strategies.trend import confluence_signal, DECISION_THRESHOLD
from memory.experience_memory import log_trade_features
from training.trainer import retrain_model_from_history, load_model_coefficients, predict_win_probability
from config.settings import SUPABASE_URL, HEADERS, MAX_TOTAL_BUDGET_USD, FIXED_LEVERAGE

REQUEST_TIMEOUT = 15

MONITORED_ASSETS_RAW = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRX-USD",
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD",
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "NIGHT-USD",
]

SNAPSHOT_TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]
ENTRY_COOLDOWN_SECONDS = 20
RETRAIN_INTERVAL_SECONDS = 6 * 3600
EXIT_RSI_LOW, EXIT_RSI_HIGH = 20, 80

# --- Explorations-Parameter (nur Paper-Trading, deshalb bewusst grosszuegig) ---
EXPLORATION_RATE = 0.25          # Chance, ein zu schwaches Signal trotzdem als Mini-Trade zu nehmen
EXPLORATION_MIN_SCORE = 1.0      # ab diesem rohen Score gilt ein HOLD als "leaning", nicht als neutral
EXPLORATION_MARGIN_FACTOR = 0.4  # Explorations-Trades bekommen weniger Kapital als volle Signale


def get_open_position(symbol):
    trades = requests.get(
        f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,Eintrittspreis,Richtung"
        f"&Vermögenswert=eq.{symbol}&Status=eq.ACTIVE",
        headers=HEADERS, timeout=REQUEST_TIMEOUT,
    ).json()
    if isinstance(trades, list) and trades:
        return trades[0]
    return None


def main_loop():
    print("🚀 KIAgent 24/7 - regelbasierte Analyse + Lernschleife + Explorations-Modus gestartet.", flush=True)

    valid_assets = get_valid_assets(MONITORED_ASSETS_RAW)
    print(f"✅ {len(valid_assets)}/{len(MONITORED_ASSETS_RAW)} Assets bei Kraken bestaetigt: {valid_assets}", flush=True)

    agent = GeminiCoreAgent()
    router = ModelRouter()
    last_chat_id = 0
    last_retrain = 0.0
    last_entry_call = {a: 0.0 for a in valid_assets}
    model_coeffs = load_model_coefficients()
    print(f"ℹ️ Gelerntes Modell beim Start: {'vorhanden' if model_coeffs else 'noch keins (folgt nach 30+ Trades)'}", flush=True)

    round_number = 0

    while True:
        round_number += 1
        round_start = time.time()
        trades_this_round = 0
        try:
            balance, winrate, total_closed = get_current_balance_and_winrate(base_balance=MAX_TOTAL_BUDGET_USD)
            check_and_notify_milestone(total_closed, winrate)

            kelly = max(0.0, (2 * winrate) - 1)
            risk_pct = max(0.005, min(0.03, kelly * 0.05))

            print(f"🔄 Runde {round_number} gestartet (Depot ${balance:.2f}, Trefferquote {winrate*100:.1f}%, {total_closed} Trades bisher)", flush=True)

            for i, symbol in enumerate(valid_assets, start=1):
                # --- Alle Zeitfenster holen (fuer das Profi-Dashboard, unabhaengig von der Entscheidung) ---
                dfs = {tf: fetch_ohlcv_df(symbol, tf, 100) for tf in SNAPSHOT_TIMEFRAMES}
                if dfs["15m"].empty or dfs["1h"].empty:
                    print(f"  [{i}/{len(valid_assets)}] {symbol}: keine Kursdaten erhalten, übersprungen", flush=True)
                    continue

                rsi_by_tf = {
                    tf: (round(float(rsi_wilder(dfs[tf]["close"]).iloc[-1]), 2) if not dfs[tf].empty and len(dfs[tf]) > 15 else None)
                    for tf in SNAPSHOT_TIMEFRAMES
                }
                last_price = float(dfs["15m"]["close"].iloc[-1])

                signal = confluence_signal(dfs["1h"], dfs["15m"])
                upsert_market_snapshot(symbol, last_price, signal["direction"], signal["confidence"],
                                        signal["reasons"], rsi_by_tf)
                log_thought(symbol, signal["direction"], signal["confidence"], signal["reasons"])

                position = get_open_position(symbol)

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
                        print(f"  [{i}/{len(valid_assets)}] {symbol}: Position geschlossen, PnL ${pnl:.2f}", flush=True)

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

                is_exploration = False
                trade_direction = signal["direction"]
                trade_confidence = signal["confidence"]

                if trade_direction == "HOLD":
                    score = signal["score"]
                    if abs(score) >= EXPLORATION_MIN_SCORE and random.random() < EXPLORATION_RATE:
                        trade_direction = "BUY" if score > 0 else "SELL"
                        trade_confidence = min(abs(score) / DECISION_THRESHOLD, 1.0) * 0.5
                        is_exploration = True

                if trade_direction not in ("BUY", "SELL"):
                    continue

                last_entry_call[symbol] = time.time()

                win_prob = predict_win_probability(model_coeffs, [
                    signal["rsi_1h"], signal["rsi_15m"], trade_confidence, trade_confidence,
                ])
                if model_coeffs and not is_exploration and win_prob < 0.55:
                    log_thought(symbol, "HOLD", trade_confidence,
                                signal["reasons"] + [f"vom Modell abgelehnt (P={win_prob:.2f})"])
                    continue

                reasons_for_trade = list(signal["reasons"])
                if is_exploration:
                    reasons_for_trade.append("Exploration: bewusst getradet, um Trainingsdaten zu sammeln")

                comment, _ = router.route(
                    f"{symbol}: Signal {trade_direction} (Gruende: {reasons_for_trade}). "
                    f"Kurze Begruendung in 1 Satz.",
                    system_context="Du bist Chef-Analyst. Antworte in 1 kurzem Satz.",
                    preferred_model="gemini",
                )

                margin = balance * risk_pct
                if is_exploration:
                    margin *= EXPLORATION_MARGIN_FACTOR

                save_trade(
                    symbol, trade_direction, last_price, 0, 0, comment,
                    f"15m:{signal['rsi_15m']:.1f}, 1h:{signal['rsi_1h']:.1f}",
                    "Exploration" if is_exploration else "Konfluenz",
                    margin, FIXED_LEVERAGE, "ACTIVE", last_price * 1.005,
                )
                trades_this_round += 1
                print(f"  [{i}/{len(valid_assets)}] {symbol}: NEUER TRADE {trade_direction}"
                      f"{' (Exploration)' if is_exploration else ''} @ ${last_price:.4f}", flush=True)

                new_trade = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id&Vermögenswert=eq.{symbol}"
                    f"&Status=eq.ACTIVE&order=id.desc&limit=1",
                    headers=HEADERS, timeout=REQUEST_TIMEOUT,
                ).json()
                if isinstance(new_trade, list) and new_trade:
                    log_trade_features(
                        new_trade[0]["id"], signal["rsi_1h"], signal["rsi_15m"],
                        trade_confidence, trade_confidence,
                    )

            # --- Live-Chat verarbeiten ---
            new_id = agent.process_live_chat(last_chat_id)
            if new_id:
                last_chat_id = new_id

            # --- Periodisches Nachtraining ---
            if time.time() - last_retrain > RETRAIN_INTERVAL_SECONDS:
                new_coeffs = retrain_model_from_history()
                if new_coeffs:
                    model_coeffs = new_coeffs
                last_retrain = time.time()

            elapsed = time.time() - round_start
            print(f"✅ Runde {round_number} fertig in {elapsed:.0f}s, {trades_this_round} neue Trades.", flush=True)

            time.sleep(20)

        except Exception as e:
            print(f"❌ Fehler in main_loop: {e}", flush=True)
            time.sleep(30)


if __name__ == "__main__":
    main_loop()
