"""
Zentrale Kraken/ccxt-Anbindung.
Eine wiederverwendete Exchange-Instanz mit Rate-Limit statt einer neuen
Instanz pro Aufruf. Cache-Dauer ist jetzt pro Zeitfenster unterschiedlich:
schnelle Zeitfenster (5m) werden oefter neu geholt als langsame (1d), das
spart unnoetige Kraken-Anfragen.
"""
import time
import ccxt
import pandas as pd

_exchange = None
_ohlcv_cache = {}

# Cache-Dauer je Zeitfenster in Sekunden - laengere Zeitfenster aendern sich
# langsamer, muessen also seltener neu geladen werden.
CACHE_TTL_BY_TIMEFRAME = {
    "5m": 30,
    "15m": 45,
    "1h": 300,
    "4h": 1800,
    "1d": 3600,
}
DEFAULT_CACHE_TTL = 60


def get_exchange():
    """Eine einzige, wiederverwendete Exchange-Instanz mit aktivem Rate-Limiter."""
    global _exchange
    if _exchange is None:
        _exchange = ccxt.kraken({"enableRateLimit": True})
        _exchange.load_markets()
    return _exchange


def get_valid_assets(asset_list):
    """Filtert die konfigurierte Asset-Liste auf das, was Kraken tatsaechlich listet."""
    exchange = get_exchange()
    valid = [a for a in asset_list if a.replace("-", "/") in exchange.markets]
    return valid


def fetch_ohlcv_df(symbol: str, timeframe: str = "15m", limit: int = 100) -> pd.DataFrame:
    """Holt OHLCV-Daten als DataFrame, mit timeframe-abhaengigem Cache."""
    key = (symbol, timeframe)
    now = time.time()
    ttl = CACHE_TTL_BY_TIMEFRAME.get(timeframe, DEFAULT_CACHE_TTL)
    cached = _ohlcv_cache.get(key)
    if cached and (now - cached["ts"] < ttl):
        return cached["df"]

    exchange = get_exchange()
    try:
        ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=timeframe, limit=limit)
    except Exception as e:
        print(f"⚠️ OHLCV-Fehler {symbol} {timeframe}: {e}")
        if cached:
            return cached["df"]  # lieber alte Daten als gar keine
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
