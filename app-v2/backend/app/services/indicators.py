"""Pure technical-indicator functions ported from modules/indicators.py.

All functions are stateless and operate on a pandas DataFrame with
columns: Open, High, Low, Close, Volume (capitalized).
"""
from __future__ import annotations

import pandas as pd


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period).mean()


def ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def bollinger(close: pd.Series, period: int = 20, mult: float = 2.0) -> pd.DataFrame:
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    return pd.DataFrame(
        {
            "upper": middle + mult * std,
            "middle": middle,
            "lower": middle - mult * std,
        }
    )


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    low_min = df["Low"].rolling(k_period).min()
    high_max = df["High"].rolling(k_period).max()
    denom = (high_max - low_min).replace(0, float("nan"))
    k = (df["Close"] - low_min) / denom * 100
    d = k.rolling(d_period).mean()
    return pd.DataFrame({"k": k, "d": d})


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()
