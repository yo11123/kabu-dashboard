"""
改善版 全MLモデル一括学習（v2）

改善点:
  - 東証全銘柄（3800+）で学習（日経225 → 全銘柄）
  - マーケット全体指標を特徴量に追加（VIX, ドル円, 米10年債, 金, 原油）
  - セクター相対強度を追加
  - LightGBM + XGBoost のアンサンブル
  - LSTM のハイパーパラメータ改善
  - 学習データの不均衡対策強化

使い方:
    python train/train_all_v2.py
"""
import os
import sys
import warnings
import pickle
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from tqdm import tqdm

warnings.filterwarnings("ignore")

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"
MODELS_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# 銘柄リスト取得
# ═══════════════════════════════════════════════════════════════════


def load_all_tse_tickers() -> list[str]:
    """東証全銘柄のティッカーコードを取得する（アプリと同じJPXソース）。"""
    import io

    # JPX公式の上場銘柄一覧Excel
    urls = [
        "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls",
        "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html",
    ]

    for url in urls:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/vnd.ms-excel, */*",
            }
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()

            # xls/xlsx を読む
            try:
                df = pd.read_excel(io.BytesIO(resp.content), dtype=str)
            except Exception:
                df = pd.read_excel(io.BytesIO(resp.content), dtype=str, engine="xlrd")

            # コード列を探す
            code_col = None
            for col in df.columns:
                col_str = str(col).strip()
                if "コード" in col_str or "code" in col_str.lower():
                    code_col = col
                    break
            if code_col is None:
                code_col = df.columns[0]

            codes = df[code_col].dropna().astype(str).str.strip().str.replace(".0", "", regex=False)
            tickers = [f"{c}.T" for c in codes if c.isdigit() and len(c) == 4]

            if len(tickers) > 500:
                print(f"JPXから {len(tickers)} 銘柄を取得")
                return tickers
        except Exception as e:
            print(f"JPXリスト取得試行失敗 ({url[:50]}...): {e}")
            continue

    # フォールバック: ローカルのdata_loaderを使う
    try:
        sys.path.insert(0, str(ROOT))
        from modules.data_loader import _fetch_tse_raw
        stocks = _fetch_tse_raw()
        tickers = [s["code"] for s in stocks]
        print(f"data_loaderから {len(tickers)} 銘柄を取得")
        return tickers
    except Exception as e:
        print(f"data_loader フォールバック失敗: {e}")

    # 最終フォールバック: 日経225
    tickers_path = DATA_DIR / "nikkei225_tickers.txt"
    codes = []
    with open(tickers_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if parts:
                codes.append(parts[0].strip())
    print(f"最終フォールバック: 日経225 ({len(codes)} 銘柄)")
    return [c for c in codes if c.endswith(".T")]


# ═══════════════════════════════════════════════════════════════════
# マーケット全体指標の取得
# ═══════════════════════════════════════════════════════════════════


def fetch_market_data(period: str = "5y") -> pd.DataFrame:
    """VIX, ドル円, 米10年債, 金, 原油 の日次データを取得する。"""
    print("マーケット全体指標を取得中...")
    market_tickers = {
        "vix": "^VIX",
        "usdjpy": "JPY=X",
        "us10y": "^TNX",
        "gold": "GC=F",
        "oil": "CL=F",
        "sp500": "^GSPC",
        "nikkei": "^N225",
    }

    market = pd.DataFrame()
    for name, ticker in market_tickers.items():
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [str(c[0]).capitalize() for c in df.columns]
                else:
                    df.columns = [str(c).capitalize() for c in df.columns]
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                market[f"mkt_{name}"] = df["Close"]
                market[f"mkt_{name}_ret5d"] = df["Close"].pct_change(5) * 100
                market[f"mkt_{name}_ret20d"] = df["Close"].pct_change(20) * 100
        except Exception:
            continue

    # VIX の水準分類
    if "mkt_vix" in market.columns:
        market["mkt_vix_regime"] = pd.cut(
            market["mkt_vix"],
            bins=[0, 15, 20, 30, 100],
            labels=[0, 1, 2, 3],
        ).astype(float)

    market = market.ffill()
    print(f"  マーケット指標: {len(market.columns)} カラム, {len(market)} 日分")
    return market


# ═══════════════════════════════════════════════════════════════════
# 特徴量計算（改善版）
# ═══════════════════════════════════════════════════════════════════


def calc_features_v2(df: pd.DataFrame, market: pd.DataFrame | None = None) -> pd.DataFrame:
    """改善版: 個別銘柄特徴量 + マーケット全体指標。"""
    close = df["Close"].copy()
    high = df["High"].copy()
    low = df["Low"].copy()
    volume = df["Volume"].copy() if "Volume" in df.columns else pd.Series(0, index=df.index)
    opn = df["Open"].copy() if "Open" in df.columns else close.copy()

    feat = pd.DataFrame(index=df.index)

    # ── テクニカル指標（基本）─────────────────────────────────
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
    # MACDヒストグラムの変化（加速度）
    feat["macd_hist_diff"] = feat["macd_hist"].diff()

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    feat["bb_position"] = (close - bb_mid) / bb_std.replace(0, np.nan)
    feat["bb_width"] = (bb_std * 4) / bb_mid.replace(0, np.nan) * 100
    # バンド幅の変化（スクイーズ検出）
    feat["bb_width_change"] = feat["bb_width"].pct_change(5) * 100

    for period in [5, 25, 75, 200]:
        sma = close.rolling(period).mean()
        feat[f"sma{period}_dev"] = (close - sma) / sma * 100

    sma25 = close.rolling(25).mean()
    sma75 = close.rolling(75).mean()
    feat["sma25_slope"] = sma25.pct_change(5) * 100
    feat["sma75_slope"] = sma75.pct_change(10) * 100

    # ゴールデンクロス/デッドクロス接近度
    if len(close) >= 75:
        feat["sma_cross_gap"] = (sma25 - sma75) / sma75 * 100

    for days in [1, 2, 3, 5, 10, 20, 60]:
        feat[f"return_{days}d"] = close.pct_change(days) * 100

    feat["volatility_20d"] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    feat["volatility_5d"] = close.pct_change().rolling(5).std() * np.sqrt(252) * 100
    # ボラティリティの変化
    feat["vol_change"] = feat["volatility_5d"] - feat["volatility_20d"]

    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    feat["atr_14"] = tr.rolling(14).mean() / close * 100

    vol_ma20 = volume.rolling(20).mean()
    feat["volume_ratio"] = volume / vol_ma20.replace(0, np.nan)
    feat["volume_change_5d"] = volume.rolling(5).mean() / volume.rolling(20).mean()
    # 上昇日の出来高 vs 下落日の出来高
    up_mask = close > opn
    up_vol = (volume * up_mask.astype(float)).rolling(10).mean()
    dn_vol = (volume * (~up_mask).astype(float)).rolling(10).mean()
    feat["volume_up_dn_ratio"] = up_vol / dn_vol.replace(0, np.nan)

    low14 = low.rolling(14).min()
    high14 = high.rolling(14).max()
    feat["stoch_k"] = (close - low14) / (high14 - low14).replace(0, np.nan) * 100
    feat["stoch_d"] = feat["stoch_k"].rolling(3).mean()

    tp = (high + low + close) / 3
    feat["cci_20"] = (tp - tp.rolling(20).mean()) / (tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean()) * 0.015)

    feat["from_52w_high"] = (close / close.rolling(252).max() - 1) * 100
    feat["from_52w_low"] = (close / close.rolling(252).min() - 1) * 100

    feat["autocorr_5d"] = close.pct_change().rolling(20).apply(
        lambda x: x.autocorr(lag=1) if len(x.dropna()) > 5 else np.nan, raw=False
    )
    feat["up_day_ratio_10d"] = (close.diff() > 0).rolling(10).mean()
    feat["up_day_ratio_20d"] = (close.diff() > 0).rolling(20).mean()

    # ── 新規追加: 高度な特徴量 ────────────────────────────────
    # ローリングシャープレシオ
    ret20 = close.pct_change().rolling(20)
    feat["sharpe_20d"] = ret20.mean() / ret20.std().replace(0, np.nan) * np.sqrt(252)

    # 価格のフラクタル次元（近似）- ボラティリティの安定性
    feat["hurst_proxy"] = close.pct_change().rolling(60).apply(
        lambda x: np.log(x.std()) / np.log(len(x)) if x.std() > 0 else np.nan, raw=False
    )

    # 出来高加重平均価格(VWAP)乖離
    if volume.sum() > 0:
        vwap = (close * volume).rolling(20).sum() / volume.rolling(20).sum().replace(0, np.nan)
        feat["vwap_dev"] = (close - vwap) / vwap * 100

    # 陰線/陽線の大きさ
    feat["candle_body"] = (close - opn) / opn * 100
    feat["candle_body_avg5"] = feat["candle_body"].rolling(5).mean()

    # 上ヒゲ/下ヒゲ比率
    feat["upper_shadow"] = (high - pd.concat([close, opn], axis=1).max(axis=1)) / close * 100
    feat["lower_shadow"] = (pd.concat([close, opn], axis=1).min(axis=1) - low) / close * 100

    # ── 一目均衡表 ─────────────────────────────────────────
    if len(close) >= 52:
        h9, l9 = high.rolling(9).max(), low.rolling(9).min()
        h26, l26 = high.rolling(26).max(), low.rolling(26).min()
        h52, l52 = high.rolling(52).max(), low.rolling(52).min()
        tenkan = (h9 + l9) / 2
        kijun = (h26 + l26) / 2
        senkou_a = (tenkan + kijun) / 2
        senkou_b = (h52 + l52) / 2
        feat["ichimoku_tenkan_dev"] = (close - tenkan) / tenkan.replace(0, np.nan) * 100
        feat["ichimoku_kijun_dev"] = (close - kijun) / kijun.replace(0, np.nan) * 100
        feat["ichimoku_tk_cross"] = (tenkan - kijun) / kijun.replace(0, np.nan) * 100
        feat["ichimoku_cloud_top"] = (close - senkou_a.shift(26)) / close * 100
        feat["ichimoku_cloud_bottom"] = (close - senkou_b.shift(26)) / close * 100
        feat["ichimoku_cloud_thickness"] = (senkou_a - senkou_b) / close * 100
        feat["ichimoku_above_cloud"] = ((close > senkou_a.shift(26)) & (close > senkou_b.shift(26))).astype(int)
        feat["ichimoku_below_cloud"] = ((close < senkou_a.shift(26)) & (close < senkou_b.shift(26))).astype(int)

    # ── ADX / DMI ────────────────────────────────────────
    if len(close) >= 28:
        plus_dm = (high.diff()).clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        feat["adx_plus_di"] = 100 * plus_dm.rolling(14).mean() / tr.rolling(14).mean().replace(0, np.nan)
        feat["adx_minus_di"] = 100 * minus_dm.rolling(14).mean() / tr.rolling(14).mean().replace(0, np.nan)
        di_diff = (feat["adx_plus_di"] - feat["adx_minus_di"]).abs()
        di_sum = (feat["adx_plus_di"] + feat["adx_minus_di"]).replace(0, np.nan)
        feat["adx"] = (di_diff / di_sum * 100).rolling(14).mean()
        feat["di_diff"] = feat["adx_plus_di"] - feat["adx_minus_di"]

    # ── Williams %R ──────────────────────────────────────
    for period in [14, 28]:
        highest = high.rolling(period).max()
        lowest = low.rolling(period).min()
        feat[f"williams_r_{period}"] = (highest - close) / (highest - lowest).replace(0, np.nan) * -100

    # ── ドンチャンチャネル位置 ────────────────────────────
    for period in [20, 50]:
        dc_high = high.rolling(period).max()
        dc_low = low.rolling(period).min()
        feat[f"donchian_pos_{period}"] = (close - dc_low) / (dc_high - dc_low).replace(0, np.nan)

    # ── TRIX ─────────────────────────────────────────────
    e1 = close.ewm(span=15, adjust=False).mean()
    e2 = e1.ewm(span=15, adjust=False).mean()
    e3 = e2.ewm(span=15, adjust=False).mean()
    feat["trix"] = e3.pct_change() * 10000

    # ── MA クロスシグナル ─────────────────────────────────
    if len(close) >= 75:
        feat["golden_cross_5_25"] = ((sma25 > sma75) & (sma25.shift(1) <= sma75.shift(1))).astype(int)
        feat["dead_cross_5_25"] = ((sma25 < sma75) & (sma25.shift(1) >= sma75.shift(1))).astype(int)

    # ── OBV ──────────────────────────────────────────────
    if volume.sum() > 0:
        obv_sign = np.sign(close.diff()).fillna(0)
        obv = (obv_sign * volume).cumsum()
        obv_sma20 = obv.rolling(20).mean()
        feat["obv_dev"] = (obv - obv_sma20) / obv_sma20.abs().replace(0, np.nan) * 100
        feat["obv_slope"] = obv.pct_change(5) * 100

    feat["weekday"] = df.index.dayofweek
    feat["month"] = df.index.month

    # ── マーケット全体指標をマージ ────────────────────────────
    if market is not None:
        for col in market.columns:
            feat[col] = market[col].reindex(feat.index).ffill()

        # 個別銘柄 vs 市場の相対リターン（アルファ）
        if "mkt_nikkei_ret5d" in market.columns:
            feat["alpha_5d"] = feat.get("return_5d", 0) - market["mkt_nikkei_ret5d"].reindex(feat.index).ffill()
        if "mkt_nikkei_ret20d" in market.columns:
            feat["alpha_20d"] = feat.get("return_20d", 0) - market["mkt_nikkei_ret20d"].reindex(feat.index).ffill()

    return feat


# ═══════════════════════════════════════════════════════════════════
# モデル1: アンサンブル株価方向予測（XGBoost + LightGBM）
# ═══════════════════════════════════════════════════════════════════


def train_ensemble_direction(tickers: list[str], market: pd.DataFrame):
    """XGBoost + LightGBM のアンサンブルで方向予測。"""
    print("\n" + "=" * 60)
    print("モデル1: アンサンブル方向予測 (XGBoost + LightGBM)")
    print(f"対象: {len(tickers)} 銘柄")
    print("=" * 60)

    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    from sklearn.metrics import classification_report, roc_auc_score

    all_X, all_y = [], []
    processed = 0

    for ticker in tqdm(tickers, desc="データ取得"):
        try:
            df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < 300:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            feat = calc_features_v2(df, market)
            feat["target"] = (df["Close"].shift(-5) / df["Close"] - 1 > 0.02).astype(int)
            feat = feat.dropna(subset=["target"])
            feat = feat.dropna(thresh=int(len(feat.columns) * 0.7))
            if len(feat) < 100:
                continue

            all_X.append(feat.drop(columns=["target"]))
            all_y.append(feat["target"])
            processed += 1
        except Exception:
            continue

    X = pd.concat(all_X, ignore_index=True).fillna(0)
    y = pd.concat(all_y, ignore_index=True)
    # Inf除去
    X = X.replace([np.inf, -np.inf], 0)
    feature_names = list(X.columns)
    print(f"学習データ: {len(X):,} サンプル, {X.shape[1]} 特徴量, {processed} 銘柄")
    print(f"正例率: {y.mean():.1%}")

    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    pos_weight = len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1)

    # XGBoost
    print("\n--- XGBoost ---")
    xgb = XGBClassifier(
        n_estimators=800, max_depth=7, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        scale_pos_weight=pos_weight,
        tree_method="hist", device="cuda",
        eval_metric="auc", early_stopping_rounds=40, random_state=42,
    )
    xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=100)
    xgb_prob = xgb.predict_proba(X_test)[:, 1]
    print(f"XGBoost AUC: {roc_auc_score(y_test, xgb_prob):.4f}")

    # LightGBM
    print("\n--- LightGBM ---")
    lgbm = LGBMClassifier(
        n_estimators=800, max_depth=7, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        scale_pos_weight=pos_weight,
        device="gpu", verbose=-1, random_state=42,
    )
    try:
        lgbm.fit(X_train, y_train, eval_set=[(X_test, y_test)])
    except Exception:
        # GPU失敗時はCPUで
        lgbm.set_params(device="cpu")
        lgbm.fit(X_train, y_train, eval_set=[(X_test, y_test)])
    lgbm_prob = lgbm.predict_proba(X_test)[:, 1]
    print(f"LightGBM AUC: {roc_auc_score(y_test, lgbm_prob):.4f}")

    # アンサンブル
    ensemble_prob = (xgb_prob + lgbm_prob) / 2
    ensemble_auc = roc_auc_score(y_test, ensemble_prob)
    print(f"\nEnsemble AUC: {ensemble_auc:.4f}")

    ensemble_pred = (ensemble_prob > 0.5).astype(int)
    print(classification_report(y_test, ensemble_pred, target_names=["下落/横ばい", "上昇"]))

    # 特徴量重要度（XGBoost）
    importance = pd.Series(xgb.feature_importances_, index=feature_names).sort_values(ascending=False)
    print("特徴量重要度 TOP15:")
    print(importance.head(15))

    with open(MODELS_DIR / "xgboost_direction.pkl", "wb") as f:
        pickle.dump({"model": xgb, "features": feature_names}, f)
    with open(MODELS_DIR / "lgbm_direction.pkl", "wb") as f:
        pickle.dump({"model": lgbm, "features": feature_names}, f)
    print(f"\n保存完了")


# ═══════════════════════════════════════════════════════════════════
# モデル2: LSTM 方向予測（改善版）
# ═══════════════════════════════════════════════════════════════════


def train_lstm_direction_v2(tickers: list[str], market: pd.DataFrame):
    """改善版LSTM: Bidirectional + Attention。メモリ効率改善版。"""
    print("\n" + "=" * 60)
    print("モデル2: LSTM 方向予測（改善版・分割処理）")
    print("=" * 60)

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    from sklearn.preprocessing import RobustScaler
    from sklearn.metrics import roc_auc_score
    import tempfile, gc

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"デバイス: {device}")

    SEQ_LEN = 30

    # ── Pass 1: スケーラーを学習（サンプリングで軽量化）─────────
    print("Pass 1: スケーラー学習（サンプリング）...")
    sample_rows = []
    sample_tickers = tickers[::10]  # 10銘柄に1つでスケーラーを学習
    for ticker in tqdm(sample_tickers, desc="スケーラー学習"):
        try:
            df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < 300:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            feat = calc_features_v2(df, market).dropna()
            if len(feat) > 50:
                sample_rows.append(feat.iloc[::5].values)  # 5行に1つサンプリング
        except Exception:
            continue

    scaler = RobustScaler()
    sample_data = np.vstack(sample_rows)
    n_features = sample_data.shape[1]
    scaler.fit(np.nan_to_num(sample_data, nan=0, posinf=0, neginf=0))
    del sample_rows, sample_data
    gc.collect()
    print(f"  特徴量数: {n_features}")

    # ── Pass 2: 銘柄ごとにスケーリング+シーケンス化→ディスク保存 ──
    print("Pass 2: シーケンス構築（銘柄単位で直接保存）...")
    tmp_dir = Path(tempfile.mkdtemp())
    total_seqs = 0
    chunk_id = 0
    CHUNK_SIZE = 50_000  # 5万シーケンスごとに保存（メモリ節約）

    # 事前確保した固定サイズバッファ
    buf_X = np.zeros((CHUNK_SIZE, SEQ_LEN, n_features), dtype=np.float32)
    buf_y = np.zeros(CHUNK_SIZE, dtype=np.float32)
    buf_idx = 0

    def _flush_buffer():
        nonlocal buf_idx, chunk_id, total_seqs
        if buf_idx == 0:
            return
        np.save(tmp_dir / f"X_{chunk_id}.npy", buf_X[:buf_idx])
        np.save(tmp_dir / f"y_{chunk_id}.npy", buf_y[:buf_idx])
        total_seqs += buf_idx
        chunk_id += 1
        buf_idx = 0

    for ticker in tqdm(tickers, desc="シーケンス構築"):
        try:
            df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < 300:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            feat = calc_features_v2(df, market)
            target = (df["Close"].shift(-5) / df["Close"] - 1 > 0.02).astype(float)
            feat["target"] = target
            feat = feat.dropna()
            if len(feat) < SEQ_LEN + 10:
                continue

            values = feat.drop(columns=["target"]).values
            values = np.nan_to_num(scaler.transform(np.nan_to_num(values, nan=0, posinf=0, neginf=0)),
                                   nan=0, posinf=0, neginf=0).astype(np.float32)
            labels = feat["target"].values

            for i in range(SEQ_LEN, len(values) - 5):
                buf_X[buf_idx] = values[i - SEQ_LEN:i]
                buf_y[buf_idx] = labels[i]
                buf_idx += 1
                if buf_idx >= CHUNK_SIZE:
                    _flush_buffer()
        except Exception:
            continue

    _flush_buffer()
    del buf_X, buf_y
    gc.collect()

    print(f"データ: {total_seqs:,} シーケンス, {chunk_id} チャンク")

    # ── Pass 3: チャンクごとに学習（メモリに全データを載せない）──
    split_chunk = max(int(chunk_id * 0.8), 1)

    # テストデータだけ読み込む（最後のチャンクのみ、小さい）
    test_Xs, test_ys = [], []
    for i in range(split_chunk, chunk_id):
        test_Xs.append(np.load(tmp_dir / f"X_{i}.npy"))
        test_ys.append(np.load(tmp_dir / f"y_{i}.npy"))
    X_test_np = np.concatenate(test_Xs); del test_Xs
    y_test_np = np.concatenate(test_ys); del test_ys; gc.collect()
    test_ds = TensorDataset(torch.tensor(X_test_np), torch.tensor(y_test_np))
    test_dl = DataLoader(test_ds, batch_size=1024)
    print(f"テスト: {len(X_test_np):,}")
    del X_test_np; gc.collect()

    # 訓練はチャンクごとにDataLoaderを作り直す（エポックごとにチャンクを順に読む）
    train_chunk_ids = list(range(split_chunk))

    class BiLSTMAttention(nn.Module):
        def __init__(self, input_dim, hidden_dim=192, num_layers=2, dropout=0.3):
            super().__init__()
            self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers,
                                batch_first=True, dropout=dropout, bidirectional=True)
            self.attn = nn.Linear(hidden_dim * 2, 1)
            self.head = nn.Sequential(
                nn.Linear(hidden_dim * 2, 96),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(96, 1),
            )

        def forward(self, x):
            out, _ = self.lstm(x)
            # Attention
            weights = torch.softmax(self.attn(out), dim=1)
            context = (out * weights).sum(dim=1)
            return self.head(context).squeeze(-1)

    model = BiLSTMAttention(n_features).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)
    # pos_weight はテストデータから推定
    _test_y_np = np.concatenate([np.load(tmp_dir / f"y_{i}.npy") for i in range(split_chunk, chunk_id)])
    _pw = (_test_y_np == 0).sum() / max((_test_y_np == 1).sum(), 1)
    del _test_y_np
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([_pw]).to(device))

    best_auc = 0
    for epoch in range(40):
        model.train()
        losses = []
        # チャンクごとに読み込んで学習（メモリに全データを載せない）
        import random
        random.shuffle(train_chunk_ids)
        for cid in train_chunk_ids:
            _cx = torch.tensor(np.load(tmp_dir / f"X_{cid}.npy"))
            _cy = torch.tensor(np.load(tmp_dir / f"y_{cid}.npy"))
            _cdl = DataLoader(TensorDataset(_cx, _cy), batch_size=512, shuffle=True)
            for xb, yb in _cdl:
                xb, yb = xb.to(device), yb.to(device)
                pred = model(xb)
                loss = criterion(pred, yb)
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                losses.append(loss.item())
            del _cx, _cy, _cdl
        scheduler.step()

        model.eval()
        all_prob, all_true = [], []
        with torch.no_grad():
            for xb, yb in test_dl:
                prob = torch.sigmoid(model(xb.to(device))).cpu().numpy()
                all_prob.extend(prob)
                all_true.extend(yb.numpy())
        auc = roc_auc_score(all_true, all_prob)
        if auc > best_auc:
            best_auc = auc
            torch.save(model.state_dict(), MODELS_DIR / "lstm_direction.pt")
        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1:2d} | Loss: {np.mean(losses):.4f} | AUC: {auc:.4f} | Best: {best_auc:.4f}")

    print(f"\nBest AUC: {best_auc:.4f}")
    with open(MODELS_DIR / "lstm_config.pkl", "wb") as f:
        pickle.dump({"scaler": scaler, "n_features": n_features, "seq_len": SEQ_LEN}, f)


# ═══════════════════════════════════════════════════════════════════
# モデル3: 決算サプライズ予測（改善版）
# ═══════════════════════════════════════════════════════════════════


def train_earnings_surprise_v2(tickers: list[str], market: pd.DataFrame):
    """改善版: マーケット指標も特徴量に含める。"""
    print("\n" + "=" * 60)
    print("モデル3: 決算サプライズ予測（改善版）")
    print("=" * 60)

    from xgboost import XGBClassifier
    from sklearn.metrics import classification_report, roc_auc_score

    all_X, all_y = [], []
    feature_names = None

    for ticker in tqdm(tickers, desc="決算データ収集"):
        try:
            t = yf.Ticker(ticker)
            earn_df = t.get_earnings_dates(limit=20)
            if earn_df is None or earn_df.empty:
                continue
            if earn_df.index.tz is not None:
                earn_df.index = earn_df.index.tz_localize(None)

            df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < 100:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            feat = calc_features_v2(df, market)
            if feature_names is None:
                feature_names = list(feat.columns)

            for dt, row in earn_df.iterrows():
                eps_act = row.get("Reported EPS")
                eps_est = row.get("EPS Estimate")
                if pd.isna(eps_act) or pd.isna(eps_est) or eps_est == 0:
                    continue
                mask = feat.index <= dt - pd.Timedelta(days=1)
                if mask.sum() < 5:
                    continue
                pre_earn = feat.loc[mask].iloc[-1]
                if pre_earn.isna().sum() > len(pre_earn) * 0.3:
                    continue
                all_X.append(pre_earn.values)
                all_y.append(1 if float(eps_act) > float(eps_est) else 0)
        except Exception:
            continue

    if len(all_X) < 50:
        print("決算データ不足。スキップ。")
        return

    X = pd.DataFrame(all_X, columns=feature_names).fillna(0).replace([np.inf, -np.inf], 0)
    y = np.array(all_y)
    print(f"データ: {len(X):,} 件, 正例率: {y.mean():.1%}")

    split = int(len(X) * 0.8)
    model = XGBClassifier(
        n_estimators=500, max_depth=6, learning_rate=0.03,
        tree_method="hist", device="cuda",
        eval_metric="auc", early_stopping_rounds=30, random_state=42,
    )
    model.fit(X.iloc[:split], y[:split], eval_set=[(X.iloc[split:], y[split:])], verbose=50)
    y_prob = model.predict_proba(X.iloc[split:])[:, 1]
    print(f"AUC: {roc_auc_score(y[split:], y_prob):.4f}")

    with open(MODELS_DIR / "xgboost_earnings.pkl", "wb") as f:
        pickle.dump({"model": model, "features": feature_names}, f)


# ═══════════════════════════════════════════════════════════════════
# モデル4: 最適売買タイミング（テクニカル+ファンダ+ニュース）
# ═══════════════════════════════════════════════════════════════════


def _news_sentiment(text: str) -> float:
    pos = ["上昇", "高値", "好調", "増収", "増益", "上方修正", "反発", "回復", "成長",
           "好決算", "増配", "自社株買い", "最高益", "黒字", "拡大",
           "surge", "rally", "gain", "rise", "bull", "upgrade", "beat"]
    neg = ["下落", "安値", "低迷", "減収", "減益", "下方修正", "暴落", "悪化",
           "減配", "赤字", "縮小", "リスク", "懸念", "不安", "戦争", "制裁",
           "crash", "plunge", "loss", "fall", "bear", "downgrade", "miss"]
    t = text.lower()
    p = sum(1 for w in pos if w in t)
    n = sum(1 for w in neg if w in t)
    return (p - n) / max(p + n, 1)


def train_optimal_timing_v2(tickers: list[str], market: pd.DataFrame):
    """改善版: テクニカル+ファンダ+ニュース+マーケット全体指標。"""
    print("\n" + "=" * 60)
    print("モデル4: 最適売買タイミング（改善版）")
    print("=" * 60)

    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    from sklearn.metrics import classification_report, roc_auc_score

    all_X, all_y = [], []
    processed = 0

    for ticker in tqdm(tickers, desc="マルチソースデータ"):
        try:
            df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < 300:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            feat = calc_features_v2(df, market)

            # ファンダメンタル
            try:
                info = yf.Ticker(ticker).info or {}
                for k, v in [("per", "trailingPE"), ("pbr", "priceToBook"),
                             ("roe", "returnOnEquity"), ("div_yield", "dividendYield"),
                             ("rev_growth", "revenueGrowth"), ("op_margin", "operatingMargins"),
                             ("beta", "beta")]:
                    raw = info.get(v)
                    try:
                        feat[f"fund_{k}"] = float(raw) if raw is not None else np.nan
                    except (TypeError, ValueError):
                        feat[f"fund_{k}"] = np.nan
                mc = info.get("marketCap")
                try:
                    feat["fund_mktcap_log"] = np.log10(float(mc)) if mc else np.nan
                except (TypeError, ValueError):
                    feat["fund_mktcap_log"] = np.nan
            except Exception:
                pass

            # ニュースセンチメント
            try:
                news = yf.Ticker(ticker).news
                titles = [n.get("title", "") for n in (news if isinstance(news, list) else [])][:20]
                feat["news_sentiment"] = np.mean([_news_sentiment(t) for t in titles]) if titles else 0
            except Exception:
                feat["news_sentiment"] = 0

            future_ret = df["Close"].shift(-10) / df["Close"] - 1
            feat["target"] = (future_ret > 0.03).astype(int)
            feat = feat.dropna(subset=["target"])
            feat = feat.dropna(thresh=int(len(feat.columns) * 0.6))
            if len(feat) < 100:
                continue

            all_X.append(feat.drop(columns=["target"]))
            all_y.append(feat["target"])
            processed += 1
        except Exception:
            continue

    X = pd.concat(all_X, ignore_index=True).fillna(0).replace([np.inf, -np.inf], 0)
    # 全カラムをfloat型に強制変換（object型混入を防ぐ）
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)
    y = pd.concat(all_y, ignore_index=True)
    features = list(X.columns)
    print(f"データ: {len(X):,} サンプル, {X.shape[1]} 特徴量, {processed} 銘柄")

    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    pos_weight = len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1)

    xgb = XGBClassifier(
        n_estimators=800, max_depth=7, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7,
        scale_pos_weight=pos_weight,
        tree_method="hist", device="cuda",
        eval_metric="auc", early_stopping_rounds=40, random_state=42,
    )
    xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=100)
    xgb_prob = xgb.predict_proba(X_test)[:, 1]
    print(f"\nXGBoost AUC: {roc_auc_score(y_test, xgb_prob):.4f}")

    importance = pd.Series(xgb.feature_importances_, index=features).sort_values(ascending=False)
    print("\n特徴量重要度 TOP15:")
    print(importance.head(15))

    with open(MODELS_DIR / "xgboost_timing.pkl", "wb") as f:
        pickle.dump({"model": xgb, "features": features}, f)


# ═══════════════════════════════════════════════════════════════════
# メイン
# ═══════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    print("[START] 改善版MLモデル学習 v2")
    print(f"保存先: {MODELS_DIR}")

    try:
        import torch
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    except ImportError:
        print("[WARN] PyTorch未インストール")

    # 銘柄取得
    tickers = load_all_tse_tickers()
    print(f"対象銘柄: {len(tickers)}")

    # マーケット全体指標
    market = fetch_market_data("5y")

    # 全モデル強制再学習（特徴量を大幅強化したため）
    # 1. アンサンブル方向予測
    train_ensemble_direction(tickers, market)

    # 2. LSTM方向予測
    try:
        import torch
        train_lstm_direction_v2(tickers, market)
    except ImportError:
        print("[WARN] PyTorch未インストール。LSTMスキップ。")

    # 3. 決算サプライズ
    train_earnings_surprise_v2(tickers, market)

    # 4. 最適タイミング
    train_optimal_timing_v2(tickers, market)

    print("\n" + "=" * 60)
    print("[DONE] 全モデル学習完了! (v2)")
    for f in sorted(MODELS_DIR.glob("*")):
        if f.is_file() and not f.name.startswith("."):
            print(f"  {f.name} ({f.stat().st_size / 1e6:.1f} MB)")
