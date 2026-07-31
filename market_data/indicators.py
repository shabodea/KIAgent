
"""
Echte technische Indikatoren + Kerzenmuster-Erkennung.
Ersetzt den bisherigen 1-Zeilen-Platzhalter.
Erwartet ueberall ein DataFrame mit Spalten: open, high, low, close, volume.
"""
import pandas as pd
import numpy as np


def rsi_wilder(closes: pd.Series, period: int = 14) -> pd.Series:
    """Wilder-geglaetteter RSI (Standard, den auch TradingView/Kraken-Charts nutzen)."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def ema(closes: pd.Series, period: int) -> pd.Series:
    return closes.ewm(span=period, adjust=False).mean()


def macd(closes: pd.Series, fast=12, slow=26, signal=9):
    macd_line = ema(closes, fast) - ema(closes, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def bollinger(closes: pd.Series, period=20, num_std=2):
    mid = closes.rolling(period).mean()
    band = closes.rolling(period).std()
    return mid - num_std * band, mid, mid + num_std * band


def atr(df: pd.DataFrame, period=14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period).mean()


def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Erkennt einfache, gut belegte Kerzenmuster auf Basis von open/high/low/close.
    Gibt pro Zeile True/False je Muster zurueck. Wichtig sind i.d.R. nur die
    letzten 1-2 Zeilen (aktuelle/vorletzte Kerze).
    """
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    rng = (h - l).replace(0, np.nan)
    upper_wick = h - c.where(c > o, o)
    lower_wick = c.where(c < o, o) - l

    patterns = pd.DataFrame(index=df.index)
    patterns["doji"] = (body / rng) < 0.1
    patterns["hammer"] = (lower_wick > 2 * body) & (upper_wick < body)
    patterns["shooting_star"] = (upper_wick > 2 * body) & (lower_wick < body)
    patterns["bull_engulf"] = (
        (c > o) & (c.shift(1) < o.shift(1)) & (c >= o.shift(1)) & (o <= c.shift(1))
    )
    patterns["bear_engulf"] = (
        (c < o) & (c.shift(1) > o.shift(1)) & (o >= c.shift(1)) & (c <= o.shift(1))
    )
    return patterns.fillna(False)


def pattern_score(df: pd.DataFrame) -> float:
    """Fasst die letzte Kerze zu einem einzigen Score zusammen: positiv = bullisch."""
    if len(df) < 3:
        return 0.0
    p = detect_candlestick_patterns(df).iloc[-1]
    score = 0.0
    if p["hammer"] or p["bull_engulf"]:
        score += 1.0
    if p["shooting_star"] or p["bear_engulf"]:
        score -= 1.0
    if p["doji"]:
        score *= 0.5  # Unentschlossenheit daempft das Signal
    return score
