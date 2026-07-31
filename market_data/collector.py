
"""
Zentrale Kraken/ccxt-Anbindung.
Ersetzt den bisherigen 1-Zeilen-Platzhalter UND die Praxis, in worker.py
bei jedem Aufruf eine neue ccxt.kraken()-Instanz zu erzeugen (das hat
vorher unnoetig oft gegen Krakens Rate-Limit gelaufen).
"""
import time
import ccxt
import pandas as pd

_exchange = None
_ohlcv_cache = {}
CACHE_TTL_SECONDS = 45  # verhindert, dass wir Kraken bei jedem Loop-Durchlauf neu anfragen


def get_exchange():
    """Eine einzige, wiederverwendete Exchange-Instanz mit aktivem Rate-Limiter."""
    global _exchange
    if _exchange is None:
        _exchange = ccxt.kraken({"enableRateLimit": True})
        _exchange.load_markets()
    return _exchange


def get_valid_assets(asset_list):
    """Filtert die konfigurierte Asset-Liste auf das, was Kraken tatsaechlich listet.
    Verhindert stille Dauerfehler fuer Symbole, die nicht (mehr) existieren."""
    exchange = get_exchange()
    valid = [a for a in asset_list if a.replace("-", "/") in exchange.markets]
    return valid


def fetch_ohlcv_df(symbol: str, timeframe: str = "15m", limit: int = 100) -> pd.DataFrame:
    """Holt OHLCV-Daten als DataFrame, mit kurzem Cache pro (Symbol, Timeframe)."""
    key = (symbol, timeframe)
    now = time.time()
    cached = _ohlcv_cache.get(key)
    if cached and (now - cached["ts"] < CACHE_TTL_SECONDS):
        return cached["df"]

    exchange = get_exchange()
    try:
        ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=timeframe, limit=limit)
    except Exception as e:
        print(f"⚠️ OHLCV-Fehler {symbol} {timeframe}: {e}")
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    _ohlcv_cache[key] = {"ts": now, "df": df}
    return df


def fetch_ticker_and_book(symbol: str):
    """Aktueller Preis + grobe Support/Resistance aus dem Orderbuch-Top."""
    exchange = get_exchange()
    ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
    book = exchange.fetch_order_book(symbol.replace("-", "/"), limit=5)
    support = book["bids"][0][0] if book["bids"] else ticker["last"] * 0.99
    resistance = book["asks"][0][0] if book["asks"] else ticker["last"] * 1.01
    return ticker, support, resistance
