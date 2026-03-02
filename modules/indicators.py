import pandas as pd


def calc_sma(df: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
    """単純移動平均線（SMA）を計算して列を追加する。"""
    df = df.copy()
    for p in periods:
        df[f"SMA_{p}"] = df["Close"].rolling(window=p).mean()
    return df


def calc_ema(df: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
    """指数移動平均線（EMA）を計算して列を追加する。"""
    df = df.copy()
    for p in periods:
        df[f"EMA_{p}"] = df["Close"].ewm(span=p, adjust=False).mean()
    return df


def calc_bollinger_bands(df: pd.DataFrame, period: int = 20, std_multiplier: float = 2.0) -> pd.DataFrame:
    """ボリンジャーバンドを計算して列を追加する。"""
    df = df.copy()
    middle = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    df["BB_upper"] = middle + std_multiplier * std
    df["BB_middle"] = middle
    df["BB_lower"] = middle - std_multiplier * std
    return df


def calc_volume_ma(df: pd.DataFrame, period: int = 25) -> pd.DataFrame:
    """出来高移動平均を計算して列を追加する。"""
    df = df.copy()
    if "Volume" in df.columns:
        df[f"Vol_MA_{period}"] = df["Volume"].rolling(window=period).mean()
    return df
