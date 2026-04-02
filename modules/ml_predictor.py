"""
機械学習モデル推論モジュール

学習済みモデル（models/）を読み込み、リアルタイムで予測を行う。
モデルが存在しない場合は None を返す（エラーにはしない）。
"""
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

_MODELS_DIR = Path(os.path.dirname(os.path.dirname(__file__))) / "models"

# キャッシュ
_cache: dict = {}


def _load_pickle(name: str) -> dict | None:
    """Pickleモデルをキャッシュ付きで読み込む。"""
    if name in _cache:
        return _cache[name]
    path = _MODELS_DIR / name
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        _cache[name] = data
        return data
    except Exception:
        return None


def _calc_features(df: pd.DataFrame) -> pd.DataFrame:
    """推論用の特徴量を計算する（学習時と同じ計算）。"""
    close = df["Close"].copy()
    high = df["High"].copy()
    low = df["Low"].copy()
    volume = df["Volume"].copy() if "Volume" in df.columns else pd.Series(0, index=df.index)

    feat = pd.DataFrame(index=df.index)

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    feat["rsi_14"] = 100 - 100 / (1 + gain / loss)

    gain5 = delta.clip(lower=0).rolling(5).mean()
    loss5 = (-delta.clip(upper=0)).rolling(5).mean().replace(0, np.nan)
    feat["rsi_5"] = 100 - 100 / (1 + gain5 / loss5)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    feat["macd"] = ema12 - ema26
    feat["macd_signal"] = feat["macd"].ewm(span=9, adjust=False).mean()
    feat["macd_hist"] = feat["macd"] - feat["macd_signal"]

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    feat["bb_position"] = (close - bb_mid) / bb_std.replace(0, np.nan)
    feat["bb_width"] = (bb_std * 4) / bb_mid.replace(0, np.nan) * 100

    for period in [5, 25, 75]:
        sma = close.rolling(period).mean()
        feat[f"sma{period}_dev"] = (close - sma) / sma * 100

    sma25 = close.rolling(25).mean()
    feat["sma25_slope"] = sma25.pct_change(5) * 100

    for days in [1, 3, 5, 10, 20]:
        feat[f"return_{days}d"] = close.pct_change(days) * 100

    feat["volatility_20d"] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    feat["volatility_5d"] = close.pct_change().rolling(5).std() * np.sqrt(252) * 100

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    feat["atr_14"] = tr.rolling(14).mean() / close * 100

    vol_ma20 = volume.rolling(20).mean()
    feat["volume_ratio"] = volume / vol_ma20.replace(0, np.nan)
    feat["volume_change_5d"] = volume.rolling(5).mean() / volume.rolling(20).mean()

    low14 = low.rolling(14).min()
    high14 = high.rolling(14).max()
    feat["stoch_k"] = (close - low14) / (high14 - low14).replace(0, np.nan) * 100
    feat["stoch_d"] = feat["stoch_k"].rolling(3).mean()

    tp = (high + low + close) / 3
    feat["cci_20"] = (tp - tp.rolling(20).mean()) / (
        tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean()) * 0.015
    )

    feat["from_52w_high"] = (close / close.rolling(252).max() - 1) * 100
    feat["from_52w_low"] = (close / close.rolling(252).min() - 1) * 100

    feat["autocorr_5d"] = close.pct_change().rolling(20).apply(
        lambda x: x.autocorr(lag=1) if len(x.dropna()) > 5 else np.nan, raw=False
    )
    feat["up_day_ratio_10d"] = (close.diff() > 0).rolling(10).mean()
    feat["up_day_ratio_20d"] = (close.diff() > 0).rolling(20).mean()
    feat["weekday"] = df.index.dayofweek
    feat["month"] = df.index.month

    return feat


# ─── 公開API ────────────────────────────────────────────────────────────


def predict_direction_xgb(df: pd.DataFrame) -> float | None:
    """XGBoostで5日後に+2%上昇する確率を予測する。"""
    data = _load_pickle("xgboost_direction.pkl")
    if data is None:
        return None
    try:
        model = data["model"]
        features = data["features"]
        feat = _calc_features(df)
        if feat.empty:
            return None
        row = feat.iloc[-1:][features].fillna(0)
        prob = model.predict_proba(row)[0][1]
        return round(float(prob) * 100, 1)
    except Exception:
        return None


def predict_direction_lstm(df: pd.DataFrame) -> float | None:
    """LSTMで5日後に+2%上昇する確率を予測する。"""
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        return None

    config = _load_pickle("lstm_config.pkl")
    pt_path = _MODELS_DIR / "lstm_direction.pt"
    if config is None or not pt_path.exists():
        return None

    try:
        scaler = config["scaler"]
        n_features = config["n_features"]
        seq_len = config["seq_len"]

        feat = _calc_features(df)
        if len(feat) < seq_len:
            return None

        values = feat.iloc[-seq_len:].values
        if np.any(np.isnan(values)) or np.any(np.isinf(values)):
            values = np.nan_to_num(values, nan=0, posinf=0, neginf=0)

        scaled = scaler.transform(values.reshape(-1, n_features))
        x = torch.tensor(scaled.reshape(1, seq_len, n_features), dtype=torch.float32)

        class LSTMPredictor(nn.Module):
            def __init__(self, input_dim, hidden_dim=128, num_layers=2, dropout=0.3):
                super().__init__()
                self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers,
                                    batch_first=True, dropout=dropout)
                self.head = nn.Sequential(
                    nn.Linear(hidden_dim, 64),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(64, 1),
                )

            def forward(self, x):
                out, _ = self.lstm(x)
                return self.head(out[:, -1, :]).squeeze(-1)

        model = LSTMPredictor(n_features)
        model.load_state_dict(torch.load(pt_path, map_location="cpu", weights_only=True))
        model.eval()
        with torch.no_grad():
            prob = torch.sigmoid(model(x)).item()
        return round(prob * 100, 1)
    except Exception:
        return None


def predict_earnings_surprise(df: pd.DataFrame) -> float | None:
    """決算でEPS予想を超過する確率を予測する。"""
    data = _load_pickle("xgboost_earnings.pkl")
    if data is None:
        return None
    try:
        model = data["model"]
        features = data["features"]
        feat = _calc_features(df)
        if feat.empty:
            return None
        row = feat.iloc[-1:][features].fillna(0)
        prob = model.predict_proba(row)[0][1]
        return round(float(prob) * 100, 1)
    except Exception:
        return None


def predict_buy_timing(df: pd.DataFrame, fund: dict | None = None,
                       news_sentiment: float = 0) -> float | None:
    """最適買いタイミングの確率を予測する（テクニカル+ファンダ+ニュース）。"""
    data = _load_pickle("xgboost_timing.pkl")
    if data is None:
        return None
    try:
        model = data["model"]
        features = data["features"]
        feat = _calc_features(df)
        if feat.empty:
            return None

        row = feat.iloc[-1:].copy()

        # ファンダメンタル特徴量を追加
        if fund:
            for k, v in fund.items():
                col = f"fund_{k}"
                if col in features:
                    row[col] = v if v is not None else 0

        # ニュースセンチメント
        if "news_sentiment" in features:
            row["news_sentiment"] = news_sentiment

        # 不足カラムを0で埋める
        for f in features:
            if f not in row.columns:
                row[f] = 0

        row = row[features].fillna(0)
        prob = model.predict_proba(row)[0][1]
        return round(float(prob) * 100, 1)
    except Exception:
        return None


def get_available_models() -> dict[str, bool]:
    """利用可能なモデルの一覧を返す。"""
    return {
        "XGBoost方向予測": (_MODELS_DIR / "xgboost_direction.pkl").exists(),
        "LSTM方向予測": (_MODELS_DIR / "lstm_direction.pt").exists(),
        "決算サプライズ": (_MODELS_DIR / "xgboost_earnings.pkl").exists(),
        "最適売買タイミング": (_MODELS_DIR / "xgboost_timing.pkl").exists(),
    }
