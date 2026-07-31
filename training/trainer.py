"""
Trainiert ein einfaches Modell (Logistische Regression) aus der bisherigen
Trade-Historie: Welche RSI/Muster/Konfidenz-Konstellationen fuehrten zu
Gewinn vs. Verlust?

WICHTIG: Render loescht das lokale Dateisystem bei jedem Neustart/Deploy.
Deshalb werden die Modell-Koeffizienten NICHT als Datei, sondern als JSON
in der Supabase-Tabelle system_knowledge gespeichert und beim Start neu geladen.
"""
import json
import numpy as np
import requests
from config.settings import SUPABASE_URL, HEADERS
from memory.experience_memory import load_training_set

FEATURE_KEYS = ["rsi_1h", "rsi_15m", "pattern_score", "confidence"]
MIN_TRADES_TO_TRAIN = 30
TIMEOUT = 15


def retrain_model_from_history():
    rows = load_training_set()
    if len(rows) < MIN_TRADES_TO_TRAIN:
        print(f"ℹ️ Erst {len(rows)} abgeschlossene Trades mit Features. Brauche >= {MIN_TRADES_TO_TRAIN} zum Trainieren.")
        return None

    try:
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        print("⚠️ scikit-learn fehlt (siehe requirements.txt).")
        return None

    X = np.array([[float(r.get(k) or 0.0) for k in FEATURE_KEYS] for r in rows])
    y = np.array([1 if r.get("net_pnl", 0.0) > 0 else 0 for r in rows])

    if len(set(y.tolist())) < 2:
        print("ℹ️ Bisher nur Gewinne ODER nur Verluste -> Modell noch nicht sinnvoll trainierbar.")
        return None

    model = LogisticRegression(max_iter=500)
    model.fit(X, y)

    coeffs = {
        "weights": model.coef_[0].tolist(),
        "bias": float(model.intercept_[0]),
        "keys": FEATURE_KEYS,
        "trained_on": len(rows),
    }
    save_model_coefficients(coeffs)
    print(f"✅ Modell auf {len(rows)} abgeschlossenen Trades nachtrainiert.")
    return coeffs


def save_model_coefficients(coeffs: dict):
    try:
        existing = requests.get(
            f"{SUPABASE_URL}/rest/v1/system_knowledge?kategorie=eq.ml_model", headers=HEADERS, timeout=TIMEOUT
        ).json()
        payload = {"kategorie": "ml_model", "inhalt": json.dumps(coeffs)}
        if isinstance(existing, list) and existing:
            row_id = existing[0]["id"]
            requests.patch(f"{SUPABASE_URL}/rest/v1/system_knowledge?id=eq.{row_id}", headers=HEADERS, json=payload, timeout=TIMEOUT)
        else:
            requests.post(f"{SUPABASE_URL}/rest/v1/system_knowledge", headers=HEADERS, json=payload, timeout=TIMEOUT)
    except Exception as e:
        print(f"⚠️ Modell speichern fehlgeschlagen: {e}")


def load_model_coefficients():
    try:
        rows = requests.get(
            f"{SUPABASE_URL}/rest/v1/system_knowledge?kategorie=eq.ml_model", headers=HEADERS, timeout=TIMEOUT
        ).json()
        if isinstance(rows, list) and rows:
            return json.loads(rows[0]["inhalt"])
    except Exception as e:
        print(f"⚠️ Modell laden fehlgeschlagen: {e}")
    return None


def predict_win_probability(coeffs, feature_values):
    """Gibt 0.5 (neutral) zurueck, solange noch kein Modell trainiert wurde."""
    if not coeffs:
        return 0.5
    z = coeffs["bias"] + sum(w * v for w, v in zip(coeffs["weights"], feature_values))
    return 1.0 / (1.0 + np.exp(-z))
