"""
BB ブレイクアウト成功確率の推論モジュール。

models/lstm_bb.pt と models/scaler_bb.pkl が存在する場合のみ動作する。
どちらかが欠けていたりエラーが起きた場合は None を返す（グレースフルデグラデーション）。
"""
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

_MODELS_DIR = Path(__file__).parent.parent / "models"
_MODEL_PATH  = _MODELS_DIR / "lstm_bb.pt"
_SCALER_PATH = _MODELS_DIR / "scaler_bb.pkl"

SEQ_LEN    = 20   # lstm_model.py と同じ値
N_FEATURES = 5

# モジュールレベルのキャッシュ（起動後の再ロードを防ぐ）
_model  = None
_scaler = None


def is_model_available() -> bool:
    """学習済みモデルとスケーラーが両方存在するかを確認する。"""
    return _MODEL_PATH.exists() and _SCALER_PATH.exists()


def _load_artifacts() -> bool:
    """モデルとスケーラーをメモリにロードする。失敗時は False を返す。"""
    global _model, _scaler
    if _model is not None:
        return True
    if not is_model_available():
        return False

    try:
        import torch
        # lstm_model.py が modules/ にあるためパスを解決
        import sys
        _modules_dir = str(Path(__file__).parent)
        if _modules_dir not in sys.path:
            sys.path.insert(0, str(Path(__file__).parent.parent))

        from modules.lstm_model import LSTMClassifier

        with open(_SCALER_PATH, "rb") as f:
            _scaler = pickle.load(f)

        m = LSTMClassifier()
        m.load_state_dict(
            torch.load(_MODEL_PATH, map_location="cpu", weights_only=True)
        )
        m.eval()
        _model = m
        return True
    except Exception:
        return False


def build_feature_sequence(df: pd.DataFrame) -> "np.ndarray | None":
    """
    現在日を末尾とする SEQ_LEN 日分の特徴量配列を返す。
    形状: (SEQ_LEN, N_FEATURES) float32

    df は BB_upper / BB_lower / BB_middle / Volume / Vol_MA_* 列を含む前提。
    """
    need = SEQ_LEN + 1  # pct_change のため +1 日余分に必要
    if len(df) < need:
        return None

    seg = df.iloc[-need:].copy()

    # Feature 1: 日次リターン（%変化）
    f1 = seg["Close"].pct_change().values[1:]

    # Feature 2: 出来高比（当日出来高 / 25日MA）
    vol_ma_col = next((c for c in df.columns if c.startswith("Vol_M")), None)
    if vol_ma_col:
        vma = seg[vol_ma_col].values[1:]
        with np.errstate(divide="ignore", invalid="ignore"):
            f2 = np.where(vma > 0, seg["Volume"].values[1:] / vma, 1.0)
    else:
        f2 = np.ones(SEQ_LEN)

    # Feature 3: BBポジション（0=下限〜1=上限）
    bw = (seg["BB_upper"] - seg["BB_lower"]).values[1:]
    with np.errstate(divide="ignore", invalid="ignore"):
        f3 = np.where(
            bw > 0,
            (seg["Close"].values[1:] - seg["BB_lower"].values[1:]) / bw,
            0.5,
        )

    # Feature 4: バンド幅 / 中心（%BB幅）
    mid = seg["BB_middle"].values[1:]
    with np.errstate(divide="ignore", invalid="ignore"):
        f4 = np.where(mid > 0, bw / mid, 0.0)

    # Feature 5: BB上限の日次上昇率
    f5 = np.diff(seg["BB_upper"].values) / seg["BB_upper"].values[:-1]

    feats = np.stack([f1, f2, f3, f4, f5], axis=1).astype(np.float32)
    # NaN/Inf をクリップ
    feats = np.nan_to_num(feats, nan=0.0, posinf=3.0, neginf=-3.0)
    feats = np.clip(feats, -5.0, 5.0)
    return feats


def predict_proba(df: pd.DataFrame) -> "float | None":
    """
    BB ブレイクアウト後の成功確率を 0〜100 の float で返す。
    モデル未存在やエラーの場合は None を返す。
    """
    if not _load_artifacts():
        return None

    feats = build_feature_sequence(df)
    if feats is None:
        return None

    try:
        import torch

        flat   = feats.reshape(-1, N_FEATURES)
        scaled = _scaler.transform(flat).reshape(1, SEQ_LEN, N_FEATURES).astype(np.float32)

        with torch.no_grad():
            x    = torch.from_numpy(scaled)
            prob = _model(x).item()

        return round(prob * 100, 1)
    except Exception:
        return None
