"""
Speichert bei jedem Trade die Feature-Werte (RSI/Muster/Konfidenz),
damit training/trainer.py daraus spaeter lernen kann, welche
Konstellationen tatsaechlich zu Gewinnen fuehren.
"""
import requests
from config.settings import SUPABASE_URL, HEADERS

TIMEOUT = 15  # verhindert, dass eine haengende Verbindung den Worker fuer immer blockiert


def log_trade_features(trade_id, rsi_1h, rsi_15m, pattern_score, confidence):
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/trade_features", headers=HEADERS, json={
            "trade_id": trade_id,
            "rsi_1h": float(rsi_1h),
            "rsi_15m": float(rsi_15m),
            "pattern_score": float(pattern_score),
            "confidence": float(confidence),
        }, timeout=TIMEOUT)
    except Exception as e:
        print(f"⚠️ Feature-Log fehlgeschlagen: {e}")


def load_training_set(limit=500):
    """Verknuepft geschlossene Trades (Erfolg/Misserfolg) mit ihren gespeicherten Features."""
    try:
        trades = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,net_pnl&Status=eq.CLOSED&order=id.desc&limit={limit}",
            headers=HEADERS, timeout=TIMEOUT,
        ).json()
        features = requests.get(
            f"{SUPABASE_URL}/rest/v1/trade_features?select=*&order=id.desc&limit={limit}",
            headers=HEADERS, timeout=TIMEOUT,
        ).json()
        if not isinstance(trades, list) or not isinstance(features, list):
            return []

        feat_by_trade = {f["trade_id"]: f for f in features if f.get("trade_id") is not None}
        rows = []
        for t in trades:
            f = feat_by_trade.get(t["id"])
            if f:
                rows.append({**f, "net_pnl": t.get("net_pnl", 0.0)})
        return rows
    except Exception as e:
        print(f"⚠️ Trainingsdaten laden fehlgeschlagen: {e}")
        return []
