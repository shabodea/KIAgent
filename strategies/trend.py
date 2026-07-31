
"""
Regelbasiertes Konfluenz-Signal.
Ersetzt den Zustand, in dem der Bot beim Nicht-Antworten der KI
random.choice(['BUY','SELL']) gewuerfelt hat.
"""
from market_data.indicators import rsi_wilder, pattern_score


def confluence_signal(df_1h, df_15m):
    """
    Kombiniert RSI (1h + 15m) mit Kerzenmuster-Score der 15m-Kerze
    zu einer deterministischen Entscheidung + Konfidenz (0-1).
    """
    if len(df_1h) < 20 or len(df_15m) < 20:
        return {"direction": "HOLD", "confidence": 0.0, "reasons": ["zu wenig Daten"]}

    rsi_1h = rsi_wilder(df_1h["close"]).iloc[-1]
    rsi_15m = rsi_wilder(df_15m["close"]).iloc[-1]
    pscore = pattern_score(df_15m)

    score = 0.0
    reasons = []

    if rsi_1h < 40:
        score += 1; reasons.append(f"1h RSI ueberverkauft ({rsi_1h:.0f})")
    elif rsi_1h > 60:
        score -= 1; reasons.append(f"1h RSI ueberkauft ({rsi_1h:.0f})")

    if rsi_15m < 35:
        score += 1; reasons.append(f"15m RSI ueberverkauft ({rsi_15m:.0f})")
    elif rsi_15m > 65:
        score -= 1; reasons.append(f"15m RSI ueberkauft ({rsi_15m:.0f})")

    if pscore > 0:
        score += 2 * pscore; reasons.append("bullisches Kerzenmuster")
    elif pscore < 0:
        score += 2 * pscore; reasons.append("baerisches Kerzenmuster")

    if score >= 2:
        direction = "BUY"
    elif score <= -2:
        direction = "SELL"
    else:
        direction = "HOLD"

    confidence = min(abs(score) / 4.0, 1.0)
    if not reasons:
        reasons = ["keine klare Konfluenz"]

    return {"direction": direction, "confidence": round(confidence, 2), "reasons": reasons,
            "rsi_1h": round(float(rsi_1h), 2), "rsi_15m": round(float(rsi_15m), 2)}
