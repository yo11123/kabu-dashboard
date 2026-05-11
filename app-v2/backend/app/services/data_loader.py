"""yfinance loader with normalized output (no Streamlit dependency).

Adapted from modules/data_loader.py — caching is now the frontend's
responsibility via TanStack Query.
"""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Literal

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)

Period = Literal["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
Interval = Literal["1d", "1wk", "1mo"]


def normalize_symbol(symbol: str) -> str:
    """JP 4-digit codes → append .T; US tickers passthrough."""
    s = symbol.strip().upper()
    if s.isdigit() and len(s) == 4:
        return f"{s}.T"
    return s


def fetch_ohlcv(symbol: str, period: Period = "1y", interval: Interval = "1d") -> pd.DataFrame | None:
    ticker = normalize_symbol(symbol)
    for attempt in range(3):
        try:
            df = yf.Ticker(ticker).history(period=period, interval=interval)
            if df is None or df.empty:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
            if "Close" not in cols:
                continue
            df = df[cols].copy()
            if df["Close"].isna().sum() > len(df) * 0.3:
                return None
            return df
        except Exception as e:  # noqa: BLE001
            log.warning("yfinance fetch failed (%s, attempt %d): %s", ticker, attempt, e)
            if attempt < 2:
                time.sleep(2**attempt)
    return None


@lru_cache(maxsize=128)
def fetch_info(symbol: str) -> dict:
    """Fetch ticker.info — used for fundamentals."""
    ticker = normalize_symbol(symbol)
    try:
        info = yf.Ticker(ticker).info
        return info if isinstance(info, dict) else {}
    except Exception as e:  # noqa: BLE001
        log.warning("yfinance info failed (%s): %s", ticker, e)
        return {}
