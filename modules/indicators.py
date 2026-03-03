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


def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """RSI（相対力指数）を計算して列を追加する。"""
    df = df.copy()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    df[f"RSI_{period}"] = 100 - 100 / (1 + rs)
    return df


def calc_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """MACD・シグナル・ヒストグラムを計算して列を追加する。"""
    df = df.copy()
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    return df


def calc_stochastic(
    df: pd.DataFrame, k_period: int = 14, d_period: int = 3
) -> pd.DataFrame:
    """ストキャスティクス（%K・%D）を計算して列を追加する。"""
    df = df.copy()
    low_min = df["Low"].rolling(k_period).min()
    high_max = df["High"].rolling(k_period).max()
    denom = (high_max - low_min).replace(0, float("nan"))
    df["Stoch_K"] = (df["Close"] - low_min) / denom * 100
    df["Stoch_D"] = df["Stoch_K"].rolling(d_period).mean()
    return df


def calc_cci(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """CCI（商品チャンネル指数）を計算して列を追加する。"""
    df = df.copy()
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma_tp = tp.rolling(period).mean()
    mean_dev = tp.rolling(period).apply(lambda x: abs(x - x.mean()).mean())
    df["CCI"] = (tp - sma_tp) / (0.015 * mean_dev.replace(0, float("nan")))
    return df
