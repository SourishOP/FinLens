"""Load HSBC share-price data via yfinance with a small on-disk cache.

The cache keeps the project usable offline once data has been fetched, and avoids
hammering Yahoo during repeated model runs. Ticker defaults to HSBA.L (London
listing) but is configurable via the HSBC_TICKER env var.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None

DEFAULT_TICKER = os.getenv("HSBC_TICKER", "HSBA.L")
_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"


def load_prices(
    ticker: str = DEFAULT_TICKER,
    period: str = "5y",
    interval: str = "1d",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Return a tidy DataFrame indexed by date with columns:
    Open, High, Low, Close, Volume.

    Falls back to the on-disk cache if the network call fails.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _CACHE_DIR / f"{ticker.replace('.', '_')}_{period}_{interval}.parquet"

    if yf is not None:
        try:
            raw = yf.download(
                ticker, period=period, interval=interval,
                progress=False, auto_adjust=True,
            )
            if raw is not None and len(raw) > 0:
                df = _flatten(raw, ticker)
                try:
                    df.to_parquet(cache_file)
                except Exception:
                    pass  # cache is best-effort
                return df
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"[market_data] live fetch failed ({exc}); trying cache")

    if use_cache and cache_file.exists():
        print(f"[market_data] loading cached {cache_file.name}")
        return pd.read_parquet(cache_file)

    raise RuntimeError(
        f"Could not fetch '{ticker}' and no cache available. "
        "Check your internet connection or run once while online."
    )


def _flatten(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """yfinance returns MultiIndex columns for a single ticker in newer versions;
    normalise to flat OHLCV columns."""
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        # columns like ('Close', 'HSBA.L') -> 'Close'
        df.columns = [c[0] for c in df.columns]
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].dropna(how="all")
    df.index.name = "Date"
    return df
