"""
日経平均株価 翌日予測モデル

明日の日経平均が上がるか下がるか、どの程度動くかを予測する。
特徴量: テクニカル指標 + 米国市場 + 為替 + VIX + コモディティ

使い方:
    python train/train_nikkei_forecast.py
"""
import os
import sys
import warnings
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)


def fetch_data() -> pd.DataFrame:
    """日経平均と関連指標の日次データを取得する。"""
    print("データ取得中...")
    tickers = {
        "nikkei": "^N225",
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "dow": "^DJI",
        "vix": "^VIX",
        "usdjpy": "JPY=X",
        "us10y": "^TNX",
        "gold": "GC=F",
        "oil": "CL=F",
        "sox": "^SOX",
    }

    data = pd.DataFrame()
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="10y", interval="1d", progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [str(c[0]).capitalize() for c in df.columns]
                else:
                    df.columns = [str(c).capitalize() for c in df.columns]
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                data[f"{name}_close"] = df["Close"]
                data[f"{name}_volume"] = df.get("Volume", 0)
                print(f"  {name}: {len(df)} 日分")
        except Exception as e:
            print(f"  {name}: 取得失敗 ({e})")

    data = data.ffill().dropna()
    print(f"統合データ: {len(data)} 日分")
    return data


def calc_features(data: pd.DataFrame) -> pd.DataFrame:
    """予測用の特徴量を計算する。"""
    feat = pd.DataFrame(index=data.index)
    nk = data["nikkei_close"]

    # ── 日経平均のテクニカル指標 ────────────────────────────────
    # リターン
    for d in [1, 2, 3, 5, 10, 20]:
        feat[f"nk_ret_{d}d"] = nk.pct_change(d) * 100

    # 移動平均乖離率
    for p in [5, 25, 75, 200]:
        sma = nk.rolling(p).mean()
        feat[f"nk_sma{p}_dev"] = (nk - sma) / sma * 100

    # RSI(14)
    delta = nk.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    feat["nk_rsi"] = 100 - 100 / (1 + gain / loss)

    # MACD
    ema12 = nk.ewm(span=12, adjust=False).mean()
    ema26 = nk.ewm(span=26, adjust=False).mean()
    feat["nk_macd_hist"] = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()

    # ボリンジャーバンド位置
    bb_mid = nk.rolling(20).mean()
    bb_std = nk.rolling(20).std()
    feat["nk_bb_pos"] = (nk - bb_mid) / bb_std.replace(0, np.nan)

    # ボラティリティ
    feat["nk_vol_20d"] = nk.pct_change().rolling(20).std() * np.sqrt(252) * 100
    feat["nk_vol_5d"] = nk.pct_change().rolling(5).std() * np.sqrt(252) * 100

    # 上昇日比率
    feat["nk_up_ratio_10d"] = (nk.diff() > 0).rolling(10).mean()

    # 曜日
    feat["weekday"] = data.index.dayofweek

    # 月
    feat["month"] = data.index.month

    # ── 米国市場（前日の影響）────────────────────────────────
    for name in ["sp500", "nasdaq", "dow"]:
        col = f"{name}_close"
        if col in data.columns:
            feat[f"{name}_ret_1d"] = data[col].pct_change() * 100
            feat[f"{name}_ret_5d"] = data[col].pct_change(5) * 100

    # ── VIX ──────────────────────────────────────────────────
    if "vix_close" in data.columns:
        feat["vix"] = data["vix_close"]
        feat["vix_change"] = data["vix_close"].pct_change() * 100
        feat["vix_ma5_dev"] = (data["vix_close"] - data["vix_close"].rolling(5).mean()) / data["vix_close"].rolling(5).mean() * 100

    # ── 為替 ──────────────────────────────────────────────────
    if "usdjpy_close" in data.columns:
        feat["usdjpy"] = data["usdjpy_close"]
        feat["usdjpy_ret_1d"] = data["usdjpy_close"].pct_change() * 100
        feat["usdjpy_ret_5d"] = data["usdjpy_close"].pct_change(5) * 100

    # ── 金利 ──────────────────────────────────────────────────
    if "us10y_close" in data.columns:
        feat["us10y"] = data["us10y_close"]
        feat["us10y_change"] = data["us10y_close"].diff()

    # ── コモディティ ──────────────────────────────────────────
    for name in ["gold", "oil"]:
        col = f"{name}_close"
        if col in data.columns:
            feat[f"{name}_ret_1d"] = data[col].pct_change() * 100
            feat[f"{name}_ret_5d"] = data[col].pct_change(5) * 100

    # ── SOX ───────────────────────────────────────────────────
    if "sox_close" in data.columns:
        feat["sox_ret_1d"] = data["sox_close"].pct_change() * 100

    # ── 日経 vs S&P500 の相対リターン（アルファ）──────────────
    if "sp500_close" in data.columns:
        feat["nk_alpha_5d"] = feat.get("nk_ret_5d", 0) - feat.get("sp500_ret_5d", 0)

    return feat


def train():
    """日経平均翌日予測モデルを学習する。"""
    print("=" * 60)
    print("日経平均 翌日予測モデル")
    print("=" * 60)

    data = fetch_data()
    feat = calc_features(data)
    nk = data["nikkei_close"]

    # ── ターゲット ─────────────────────────────────────────
    # 1. 翌日の方向（上がるか下がるか）
    feat["target_direction"] = (nk.shift(-1) / nk - 1 > 0).astype(int)
    # 2. 翌日の変動率（回帰用）
    feat["target_return"] = (nk.shift(-1) / nk - 1) * 100

    feat = feat.dropna()
    feature_cols = [c for c in feat.columns if not c.startswith("target_")]
    print(f"特徴量: {len(feature_cols)} 個, データ: {len(feat)} 日分")

    X = feat[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    # 全カラムをfloat化
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)
    y_dir = feat["target_direction"]
    y_ret = feat["target_return"]

    # 時系列分割
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_dir_train, y_dir_test = y_dir.iloc[:split], y_dir.iloc[split:]
    y_ret_train, y_ret_test = y_ret.iloc[:split], y_ret.iloc[split:]

    # ── モデル1: 方向予測（分類）────────────────────────────
    print("\n--- 方向予測（XGBoost分類）---")
    from xgboost import XGBClassifier
    from sklearn.metrics import classification_report, roc_auc_score, accuracy_score

    clf = XGBClassifier(
        n_estimators=500, max_depth=6, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7,
        tree_method="hist", device="cuda",
        eval_metric="auc", early_stopping_rounds=30, random_state=42,
    )
    clf.fit(X_train, y_dir_train, eval_set=[(X_test, y_dir_test)], verbose=50)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_dir_test, y_pred)
    auc = roc_auc_score(y_dir_test, y_prob)
    print(f"\n正解率: {acc:.1%}")
    print(f"AUC: {auc:.4f}")
    print(classification_report(y_dir_test, y_pred, target_names=["下落", "上昇"]))

    # 特徴量重要度
    importance = pd.Series(clf.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("特徴量重要度 TOP10:")
    print(importance.head(10))

    # ── モデル2: 変動幅予測（回帰）────────────────────────────
    print("\n--- 変動幅予測（XGBoost回帰）---")
    from xgboost import XGBRegressor
    from sklearn.metrics import mean_absolute_error, r2_score

    reg = XGBRegressor(
        n_estimators=500, max_depth=6, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7,
        tree_method="hist", device="cuda",
        early_stopping_rounds=30, random_state=42,
    )
    reg.fit(X_train, y_ret_train, eval_set=[(X_test, y_ret_test)], verbose=50)

    y_ret_pred = reg.predict(X_test)
    mae = mean_absolute_error(y_ret_test, y_ret_pred)
    r2 = r2_score(y_ret_test, y_ret_pred)
    print(f"\n平均絶対誤差: {mae:.3f}%")
    print(f"R2スコア: {r2:.4f}")

    # 予測 vs 実際の方向一致率
    dir_match = ((y_ret_pred > 0) == (y_ret_test > 0)).mean()
    print(f"方向一致率（回帰モデル）: {dir_match:.1%}")

    # ── 保存 ──────────────────────────────────────────────
    with open(MODELS_DIR / "nikkei_forecast.pkl", "wb") as f:
        pickle.dump({
            "classifier": clf,
            "regressor": reg,
            "features": feature_cols,
            "metrics": {
                "accuracy": round(acc, 4),
                "auc": round(auc, 4),
                "mae": round(mae, 4),
                "r2": round(r2, 4),
                "direction_match": round(dir_match, 4),
            },
        }, f)
    print(f"\n保存: {MODELS_DIR / 'nikkei_forecast.pkl'}")
    print("完了!")


if __name__ == "__main__":
    train()
