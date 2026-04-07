"""
日経平均 翌日予測 最大精度版 v2

改善点:
  1. Triple Barrier Method でラベル再定義
  2. クロスアセット特徴量（アジア市場、日米金利差、日経先物）
  3. カレンダーアノマリー（でかんしょ節効果、祝前日効果）
  4. HMM レジーム検出
  5. 指数減衰サンプルウェイティング
  6. XGBoost + LightGBM + CatBoost スタッキング
  7. Meta-Labeling（信頼度フィルタリング）
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


# ═══════════════════════════════════════════════════════════════════
# データ取得
# ═══════════════════════════════════════════════════════════════════


def fetch_data() -> pd.DataFrame:
    """日経平均と関連市場の日次データを取得する。"""
    print("データ取得中...")
    tickers = {
        "nikkei": "^N225",
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "dow": "^DJI",
        "vix": "^VIX",
        "usdjpy": "JPY=X",
        "us10y": "^TNX",
        "us2y": "^IRX",
        "gold": "GC=F",
        "oil": "CL=F",
        "sox": "^SOX",
        "russell": "^RUT",
        "topix": "1306.T",
        # アジア市場
        "shanghai": "000001.SS",
        "hangseng": "^HSI",
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
                if "Volume" in df.columns:
                    data[f"{name}_volume"] = df["Volume"]
                print(f"  {name}: OK ({len(df)} days)")
        except Exception as e:
            print(f"  {name}: FAILED ({e})")

    data = data.ffill().dropna(subset=["nikkei_close"])
    data = data.fillna(method="ffill").fillna(0)
    print(f"統合データ: {len(data)} 日分, {len(data.columns)} カラム")
    return data


# ═══════════════════════════════════════════════════════════════════
# 特徴量計算（改善版）
# ═══════════════════════════════════════════════════════════════════


def calc_features_v2(data: pd.DataFrame) -> pd.DataFrame:
    """最大精度版の特徴量を計算する。"""
    feat = pd.DataFrame(index=data.index)
    nk = data["nikkei_close"]

    # ── 日経平均テクニカル ─────────────────────────────────────
    for d in [1, 2, 3, 5, 10, 20, 60]:
        feat[f"nk_ret_{d}d"] = nk.pct_change(d) * 100

    for p in [5, 10, 25, 50, 75, 200]:
        sma = nk.rolling(p).mean()
        feat[f"nk_sma{p}_dev"] = (nk - sma) / sma * 100

    # SMA の傾き
    feat["nk_sma25_slope"] = nk.rolling(25).mean().pct_change(5) * 100
    feat["nk_sma75_slope"] = nk.rolling(75).mean().pct_change(10) * 100

    # RSI
    delta = nk.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    feat["nk_rsi"] = 100 - 100 / (1 + gain / loss)
    feat["nk_rsi_5"] = 100 - 100 / (1 + delta.clip(lower=0).rolling(5).mean() / (-delta.clip(upper=0)).rolling(5).mean().replace(0, np.nan))

    # MACD
    ema12 = nk.ewm(span=12, adjust=False).mean()
    ema26 = nk.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    feat["nk_macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    feat["nk_macd_hist_diff"] = feat["nk_macd_hist"].diff()

    # ボリンジャーバンド
    bb_mid = nk.rolling(20).mean()
    bb_std = nk.rolling(20).std()
    feat["nk_bb_pos"] = (nk - bb_mid) / bb_std.replace(0, np.nan)
    feat["nk_bb_width"] = (bb_std * 4) / bb_mid.replace(0, np.nan) * 100
    feat["nk_bb_width_change"] = feat["nk_bb_width"].pct_change(5)

    # ボラティリティ
    feat["nk_vol_20d"] = nk.pct_change().rolling(20).std() * np.sqrt(252) * 100
    feat["nk_vol_5d"] = nk.pct_change().rolling(5).std() * np.sqrt(252) * 100
    feat["nk_vol_ratio"] = feat["nk_vol_5d"] / feat["nk_vol_20d"].replace(0, np.nan)

    # 上昇日比率
    feat["nk_up_ratio_5d"] = (nk.diff() > 0).rolling(5).mean()
    feat["nk_up_ratio_10d"] = (nk.diff() > 0).rolling(10).mean()
    feat["nk_up_ratio_20d"] = (nk.diff() > 0).rolling(20).mean()

    # ローリングシャープレシオ
    ret = nk.pct_change()
    feat["nk_sharpe_20d"] = ret.rolling(20).mean() / ret.rolling(20).std().replace(0, np.nan) * np.sqrt(252)

    # 52週高値/安値比
    feat["nk_from_52w_high"] = (nk / nk.rolling(252).max() - 1) * 100
    feat["nk_from_52w_low"] = (nk / nk.rolling(252).min() - 1) * 100

    # ── ストキャスティクス (%K, %D) ──────────────────────────
    for period in [14, 9]:
        low_min = nk.rolling(period).min()
        high_max = data.get("nikkei_close", nk).rolling(period).max()  # 本来はHigh
        k = (nk - low_min) / (high_max - low_min).replace(0, np.nan) * 100
        d = k.rolling(3).mean()
        feat[f"nk_stoch_k_{period}"] = k
        feat[f"nk_stoch_d_{period}"] = d

    # ── CCI (Commodity Channel Index) ────────────────────────
    tp = nk  # 本来は (H+L+C)/3 だが Close のみ使用
    for period in [20, 14]:
        tp_sma = tp.rolling(period).mean()
        tp_mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        feat[f"nk_cci_{period}"] = (tp - tp_sma) / (0.015 * tp_mad).replace(0, np.nan)

    # ── ADX (Average Directional Index) ──────────────────────
    # Close のみなので、近似的に計算
    nk_diff = nk.diff()
    plus_dm = nk_diff.clip(lower=0)
    minus_dm = (-nk_diff).clip(lower=0)
    atr_14 = nk_diff.abs().rolling(14).mean().replace(0, np.nan)
    plus_di = 100 * plus_dm.rolling(14).mean() / atr_14
    minus_di = 100 * minus_dm.rolling(14).mean() / atr_14
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    feat["nk_adx"] = dx.rolling(14).mean()
    feat["nk_plus_di"] = plus_di
    feat["nk_minus_di"] = minus_di
    feat["nk_di_diff"] = plus_di - minus_di

    # ── ATR (Average True Range) ─────────────────────────────
    feat["nk_atr_14"] = nk_diff.abs().rolling(14).mean()
    feat["nk_atr_pct"] = feat["nk_atr_14"] / nk * 100  # 価格比率

    # ── 一目均衡表 (Ichimoku Cloud) ──────────────────────────
    high_9 = nk.rolling(9).max()
    low_9 = nk.rolling(9).min()
    high_26 = nk.rolling(26).max()
    low_26 = nk.rolling(26).min()
    high_52 = nk.rolling(52).max()
    low_52 = nk.rolling(52).min()

    tenkan = (high_9 + low_9) / 2       # 転換線
    kijun = (high_26 + low_26) / 2      # 基準線
    senkou_a = (tenkan + kijun) / 2     # 先行スパンA
    senkou_b = (high_52 + low_52) / 2   # 先行スパンB

    feat["nk_ichimoku_tenkan_dev"] = (nk - tenkan) / tenkan.replace(0, np.nan) * 100
    feat["nk_ichimoku_kijun_dev"] = (nk - kijun) / kijun.replace(0, np.nan) * 100
    feat["nk_ichimoku_tk_cross"] = (tenkan - kijun) / kijun.replace(0, np.nan) * 100  # TK差
    feat["nk_ichimoku_cloud_top"] = (nk - senkou_a.shift(26)) / nk * 100  # 雲上限との乖離
    feat["nk_ichimoku_cloud_bottom"] = (nk - senkou_b.shift(26)) / nk * 100  # 雲下限との乖離
    feat["nk_ichimoku_cloud_thickness"] = (senkou_a - senkou_b) / nk * 100  # 雲の厚さ
    # 三役好転/三役逆転のシグナル
    above_cloud = ((nk > senkou_a.shift(26)) & (nk > senkou_b.shift(26))).astype(int)
    below_cloud = ((nk < senkou_a.shift(26)) & (nk < senkou_b.shift(26))).astype(int)
    feat["nk_ichimoku_above_cloud"] = above_cloud
    feat["nk_ichimoku_below_cloud"] = below_cloud

    # ── Williams %R ──────────────────────────────────────────
    for period in [14, 28]:
        highest = nk.rolling(period).max()
        lowest = nk.rolling(period).min()
        feat[f"nk_williams_r_{period}"] = (highest - nk) / (highest - lowest).replace(0, np.nan) * -100

    # ── OBV (On-Balance Volume) トレンド ─────────────────────
    if "nikkei_volume" in data.columns:
        vol = data["nikkei_volume"]
        obv_sign = np.sign(nk.diff()).fillna(0)
        obv = (obv_sign * vol).cumsum()
        obv_sma20 = obv.rolling(20).mean()
        feat["nk_obv_dev"] = (obv - obv_sma20) / obv_sma20.abs().replace(0, np.nan) * 100
        feat["nk_obv_slope"] = obv.pct_change(5) * 100

    # ── MA クロスオーバーシグナル ─────────────────────────────
    sma5 = nk.rolling(5).mean()
    sma25 = nk.rolling(25).mean()
    sma75 = nk.rolling(75).mean()
    feat["nk_golden_cross_5_25"] = ((sma5 > sma25) & (sma5.shift(1) <= sma25.shift(1))).astype(int)
    feat["nk_dead_cross_5_25"] = ((sma5 < sma25) & (sma5.shift(1) >= sma25.shift(1))).astype(int)
    feat["nk_golden_cross_25_75"] = ((sma25 > sma75) & (sma25.shift(1) <= sma75.shift(1))).astype(int)
    feat["nk_dead_cross_25_75"] = ((sma25 < sma75) & (sma25.shift(1) >= sma75.shift(1))).astype(int)
    # クロスからの経過日数
    gc_5_25 = feat["nk_golden_cross_5_25"].replace(0, np.nan)
    dc_5_25 = feat["nk_dead_cross_5_25"].replace(0, np.nan)
    feat["nk_days_since_gc_5_25"] = gc_5_25.groupby(gc_5_25.cumsum()).cumcount()
    feat["nk_days_since_dc_5_25"] = dc_5_25.groupby(dc_5_25.cumsum()).cumcount()

    # ── ドンチャンチャネル ────────────────────────────────────
    for period in [20, 50]:
        dc_high = nk.rolling(period).max()
        dc_low = nk.rolling(period).min()
        feat[f"nk_donchian_pos_{period}"] = (nk - dc_low) / (dc_high - dc_low).replace(0, np.nan)

    # ── TRIX (Triple EMA) ────────────────────────────────────
    ema1 = nk.ewm(span=15, adjust=False).mean()
    ema2 = ema1.ewm(span=15, adjust=False).mean()
    ema3 = ema2.ewm(span=15, adjust=False).mean()
    feat["nk_trix"] = ema3.pct_change() * 10000

    # ── 出来高比率の変化 ──────────────────────────────────────
    if "nikkei_volume" in data.columns:
        vol = data["nikkei_volume"]
        feat["nk_vol_ratio_5_20"] = vol.rolling(5).mean() / vol.rolling(20).mean().replace(0, np.nan)
        feat["nk_vol_spike"] = vol / vol.rolling(20).mean().replace(0, np.nan)

    # ── カレンダーアノマリー（日本市場特有）────────────────────
    feat["weekday"] = data.index.dayofweek
    feat["month"] = data.index.month
    feat["is_first_half"] = (data.index.month <= 6).astype(int)  # でかんしょ節効果
    feat["is_month_end"] = (data.index.day >= 25).astype(int)
    feat["is_month_start"] = (data.index.day <= 5).astype(int)

    # 祝前日効果（jpholiday使用）
    try:
        import jpholiday
        feat["is_pre_holiday"] = 0
        for i, dt in enumerate(data.index):
            next_day = dt + pd.Timedelta(days=1)
            if jpholiday.is_holiday(next_day.date()):
                feat.iloc[i, feat.columns.get_loc("is_pre_holiday")] = 1
    except ImportError:
        feat["is_pre_holiday"] = 0

    # ── 米国市場 ──────────────────────────────────────────────
    for name in ["sp500", "nasdaq", "dow", "russell"]:
        col = f"{name}_close"
        if col in data.columns:
            feat[f"{name}_ret_1d"] = data[col].pct_change() * 100
            feat[f"{name}_ret_5d"] = data[col].pct_change(5) * 100

    # SOX
    if "sox_close" in data.columns:
        feat["sox_ret_1d"] = data["sox_close"].pct_change() * 100
        feat["sox_ret_5d"] = data["sox_close"].pct_change(5) * 100

    # ── VIX ──────────────────────────────────────────────────
    if "vix_close" in data.columns:
        feat["vix"] = data["vix_close"]
        feat["vix_change"] = data["vix_close"].pct_change() * 100
        feat["vix_ma5_dev"] = (data["vix_close"] - data["vix_close"].rolling(5).mean()) / data["vix_close"].rolling(5).mean() * 100
        feat["vix_ma20_dev"] = (data["vix_close"] - data["vix_close"].rolling(20).mean()) / data["vix_close"].rolling(20).mean() * 100
        # VIXレジーム
        feat["vix_regime"] = pd.cut(data["vix_close"], bins=[0, 15, 20, 30, 100], labels=[0, 1, 2, 3]).astype(float)

    # ── 為替 ──────────────────────────────────────────────────
    if "usdjpy_close" in data.columns:
        feat["usdjpy"] = data["usdjpy_close"]
        feat["usdjpy_ret_1d"] = data["usdjpy_close"].pct_change() * 100
        feat["usdjpy_ret_5d"] = data["usdjpy_close"].pct_change(5) * 100
        feat["usdjpy_ret_20d"] = data["usdjpy_close"].pct_change(20) * 100

    # ── 金利 ──────────────────────────────────────────────────
    if "us10y_close" in data.columns:
        feat["us10y"] = data["us10y_close"]
        feat["us10y_change"] = data["us10y_close"].diff()
    if "us2y_close" in data.columns:
        feat["us2y"] = data["us2y_close"]
    # 日米金利差（米10年-米2年 イールドカーブ）
    if "us10y_close" in data.columns and "us2y_close" in data.columns:
        feat["yield_curve"] = data["us10y_close"] - data["us2y_close"]

    # ── コモディティ ──────────────────────────────────────────
    for name in ["gold", "oil"]:
        col = f"{name}_close"
        if col in data.columns:
            feat[f"{name}_ret_1d"] = data[col].pct_change() * 100
            feat[f"{name}_ret_5d"] = data[col].pct_change(5) * 100

    # ── アジア市場 ────────────────────────────────────────────
    for name in ["shanghai", "hangseng"]:
        col = f"{name}_close"
        if col in data.columns:
            feat[f"{name}_ret_1d"] = data[col].pct_change() * 100
            feat[f"{name}_ret_5d"] = data[col].pct_change(5) * 100

    # ── 日経 vs S&P500 アルファ ───────────────────────────────
    if "sp500_close" in data.columns:
        feat["nk_alpha_5d"] = feat.get("nk_ret_5d", 0) - feat.get("sp500_ret_5d", 0)
        feat["nk_alpha_20d"] = feat.get("nk_ret_20d", pd.Series(0, index=data.index)) - data["sp500_close"].pct_change(20) * 100

    # ── TOPIX vs 日経（NT倍率変化）────────────────────────────
    if "topix_close" in data.columns:
        feat["nt_ratio"] = nk / data["topix_close"].replace(0, np.nan)
        feat["nt_ratio_change"] = feat["nt_ratio"].pct_change(5) * 100

    return feat


# ═══════════════════════════════════════════════════════════════════
# HMM レジーム検出
# ═══════════════════════════════════════════════════════════════════


def add_regime_features(feat: pd.DataFrame, nk_returns: pd.Series) -> pd.DataFrame:
    """HMMでマーケットレジーム（強気/中立/弱気）を検出し特徴量に追加する。"""
    try:
        from hmmlearn.hmm import GaussianHMM

        vol = nk_returns.rolling(20).std() * np.sqrt(252)
        X = np.column_stack([
            nk_returns.fillna(0).values,
            vol.fillna(0).values,
        ])

        # 有効な行のみ
        valid = ~np.isnan(X).any(axis=1) & ~np.isinf(X).any(axis=1)
        X_valid = X[valid]

        if len(X_valid) < 100:
            return feat

        hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=200, random_state=42)
        hmm.fit(X_valid)

        # 全データに対して予測
        regimes = np.full(len(X), np.nan)
        probs = np.full((len(X), 3), np.nan)
        regimes[valid] = hmm.predict(X_valid)
        probs[valid] = hmm.predict_proba(X_valid)

        feat["regime"] = regimes
        feat["regime_prob_0"] = probs[:, 0]
        feat["regime_prob_1"] = probs[:, 1]
        feat["regime_prob_2"] = probs[:, 2]
        print(f"  HMMレジーム検出: 3状態")
    except ImportError:
        print("  [WARN] hmmlearn未インストール。レジーム検出をスキップ")
    except Exception as e:
        print(f"  [WARN] レジーム検出失敗: {e}")

    return feat


# ═══════════════════════════════════════════════════════════════════
# Triple Barrier Labeling
# ═══════════════════════════════════════════════════════════════════


def triple_barrier_labels(close: pd.Series, vol: pd.Series,
                          upper_mult: float = 1.0, lower_mult: float = 1.0,
                          max_days: int = 5) -> pd.Series:
    """Triple Barrier Method でラベルを生成する。

    - 上限到達（+σ×upper_mult）→ 1（上昇）
    - 下限到達（-σ×lower_mult）→ 0（下落）
    - 期限（max_days日）→ リターンの符号
    """
    labels = pd.Series(np.nan, index=close.index)

    for i in range(len(close) - max_days):
        entry_price = close.iloc[i]
        threshold = vol.iloc[i] if not np.isnan(vol.iloc[i]) else 0.01
        upper = entry_price * (1 + threshold * upper_mult)
        lower = entry_price * (1 - threshold * lower_mult)

        hit = False
        for j in range(1, max_days + 1):
            if i + j >= len(close):
                break
            price = close.iloc[i + j]
            if price >= upper:
                labels.iloc[i] = 1
                hit = True
                break
            elif price <= lower:
                labels.iloc[i] = 0
                hit = True
                break

        if not hit and i + max_days < len(close):
            final_ret = close.iloc[i + max_days] / entry_price - 1
            labels.iloc[i] = 1 if final_ret > 0 else 0

    return labels


# ═══════════════════════════════════════════════════════════════════
# 学習
# ═══════════════════════════════════════════════════════════════════


def train():
    print("=" * 60)
    print("日経平均 翌日予測 最大精度版 v2")
    print("=" * 60)

    # GPU確認
    try:
        import torch
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
    except Exception:
        pass

    data = fetch_data()
    nk = data["nikkei_close"]
    nk_returns = nk.pct_change()

    # 特徴量計算
    print("\n特徴量計算中...")
    feat = calc_features_v2(data)
    feat = add_regime_features(feat, nk_returns)

    # Triple Barrier ラベル
    print("Triple Barrier ラベリング中...")
    vol_20d = nk_returns.rolling(20).std()
    feat["target"] = triple_barrier_labels(nk, vol_20d, upper_mult=1.0, lower_mult=1.0, max_days=5)

    # 翌日リターン（回帰用）
    feat["target_return"] = (nk.shift(-1) / nk - 1) * 100

    feat = feat.dropna(subset=["target"])
    feature_cols = [c for c in feat.columns if not c.startswith("target")]

    X = feat[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)
    y = feat["target"].astype(int)
    y_ret = feat["target_return"]

    print(f"特徴量: {len(feature_cols)} 個, データ: {len(X)} 日分")
    print(f"正例率: {y.mean():.1%}")

    # ── サンプルウェイティング（指数減衰）──────────────────────
    half_life = 504  # 約2年
    decay = np.log(2) / half_life
    weights = np.exp(-decay * np.arange(len(X))[::-1])
    weights = weights / weights.mean()

    # ── 時系列分割 ────────────────────────────────────────────
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    w_train = weights[:split]

    # ════════════════════════════════════════════════════════════
    # Level 0: ベースモデル
    # ════════════════════════════════════════════════════════════
    from xgboost import XGBClassifier, XGBRegressor
    from lightgbm import LGBMClassifier
    from sklearn.metrics import classification_report, roc_auc_score, accuracy_score

    print("\n--- Level 0: XGBoost ---")
    xgb = XGBClassifier(
        n_estimators=800, max_depth=6, learning_rate=0.02,
        subsample=0.8, colsample_bytree=0.6, reg_alpha=0.1, reg_lambda=1.5,
        tree_method="hist", device="cuda",
        eval_metric="auc", early_stopping_rounds=40, random_state=42,
    )
    xgb.fit(X_train, y_train, sample_weight=w_train,
            eval_set=[(X_test, y_test)], verbose=100)
    xgb_prob = xgb.predict_proba(X_test)[:, 1]
    print(f"XGBoost AUC: {roc_auc_score(y_test, xgb_prob):.4f}")

    print("\n--- Level 0: LightGBM ---")
    lgbm = LGBMClassifier(
        n_estimators=800, max_depth=6, learning_rate=0.02,
        subsample=0.8, colsample_bytree=0.6, reg_alpha=0.1, reg_lambda=1.5,
        verbose=-1, random_state=42,
    )
    try:
        lgbm.set_params(device="gpu")
        lgbm.fit(X_train, y_train, sample_weight=w_train,
                 eval_set=[(X_test, y_test)])
    except Exception:
        lgbm.set_params(device="cpu")
        lgbm.fit(X_train, y_train, sample_weight=w_train,
                 eval_set=[(X_test, y_test)])
    lgbm_prob = lgbm.predict_proba(X_test)[:, 1]
    print(f"LightGBM AUC: {roc_auc_score(y_test, lgbm_prob):.4f}")

    print("\n--- Level 0: CatBoost ---")
    try:
        from catboost import CatBoostClassifier
        cat = CatBoostClassifier(
            iterations=800, depth=6, learning_rate=0.02,
            task_type="GPU", verbose=100, random_seed=42,
        )
        cat.fit(X_train, y_train, sample_weight=w_train,
                eval_set=(X_test, y_test))
        cat_prob = cat.predict_proba(X_test)[:, 1]
        print(f"CatBoost AUC: {roc_auc_score(y_test, cat_prob):.4f}")
        has_catboost = True
    except Exception as e:
        print(f"CatBoost スキップ: {e}")
        cat_prob = xgb_prob  # フォールバック
        has_catboost = False

    # ════════════════════════════════════════════════════════════
    # Level 1: スタッキング（メタラーナー）
    # ════════════════════════════════════════════════════════════
    print("\n--- Level 1: スタッキング ---")
    meta_X_test = np.column_stack([xgb_prob, lgbm_prob, cat_prob])

    # 訓練データのOut-of-Fold予測を生成
    from sklearn.model_selection import TimeSeriesSplit
    n_folds = 5
    tscv = TimeSeriesSplit(n_splits=n_folds)
    meta_X_train = np.zeros((len(X_train), 3))

    for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_train)):
        _xtr, _xval = X_train.iloc[tr_idx], X_train.iloc[val_idx]
        _ytr, _yval = y_train.iloc[tr_idx], y_train.iloc[val_idx]
        _wtr = w_train[tr_idx]

        _xgb = XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.03,
                              tree_method="hist", device="cuda", eval_metric="auc",
                              early_stopping_rounds=20, random_state=42)
        _xgb.fit(_xtr, _ytr, sample_weight=_wtr, eval_set=[(_xval, _yval)], verbose=0)
        meta_X_train[val_idx, 0] = _xgb.predict_proba(_xval)[:, 1]

        _lgbm = LGBMClassifier(n_estimators=300, max_depth=5, learning_rate=0.03, verbose=-1, random_state=42)
        _lgbm.fit(_xtr, _ytr, sample_weight=_wtr, eval_set=[(_xval, _yval)])
        meta_X_train[val_idx, 1] = _lgbm.predict_proba(_xval)[:, 1]

        if has_catboost:
            _cat = CatBoostClassifier(iterations=300, depth=5, learning_rate=0.03,
                                       task_type="GPU", verbose=0, random_seed=42)
            _cat.fit(_xtr, _ytr, sample_weight=_wtr, eval_set=(_xval, _yval))
            meta_X_train[val_idx, 2] = _cat.predict_proba(_xval)[:, 1]
        else:
            meta_X_train[val_idx, 2] = meta_X_train[val_idx, 0]

    # メタラーナー（Logistic Regression — 過学習しにくい）
    from sklearn.linear_model import LogisticRegression
    # 最初のfoldは0のまま → 除外
    valid_meta = meta_X_train.sum(axis=1) > 0
    meta_lr = LogisticRegression(C=1.0, random_state=42)
    meta_lr.fit(meta_X_train[valid_meta], y_train[valid_meta])

    stacked_prob = meta_lr.predict_proba(meta_X_test)[:, 1]
    stacked_auc = roc_auc_score(y_test, stacked_prob)
    stacked_acc = accuracy_score(y_test, (stacked_prob > 0.5).astype(int))
    print(f"Stacked AUC: {stacked_auc:.4f}")
    print(f"Stacked Accuracy: {stacked_acc:.1%}")

    # ════════════════════════════════════════════════════════════
    # Meta-Labeling（信頼度モデル）
    # ════════════════════════════════════════════════════════════
    print("\n--- Meta-Labeling ---")
    # Primary予測が正しかったかどうかを学習
    primary_pred = (stacked_prob > 0.5).astype(int)
    meta_target = (primary_pred == y_test.values).astype(int)

    # メタ特徴量 = ベースモデルの確率 + 元の特徴量
    meta_features = np.column_stack([
        meta_X_test,
        np.abs(stacked_prob - 0.5),  # 予測の確信度
        X_test.values,
    ])

    # 分割
    meta_split = int(len(meta_features) * 0.5)
    meta_model = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        tree_method="hist", device="cuda", eval_metric="auc",
        early_stopping_rounds=20, random_state=42,
    )
    meta_model.fit(
        meta_features[:meta_split], meta_target[:meta_split],
        eval_set=[(meta_features[meta_split:], meta_target[meta_split:])],
        verbose=0,
    )
    confidence = meta_model.predict_proba(meta_features)[:, 1]

    # 高信頼度のみでの精度
    high_conf_mask = confidence > 0.6
    if high_conf_mask.sum() > 10:
        filtered_acc = accuracy_score(y_test[high_conf_mask], primary_pred[high_conf_mask])
        print(f"Meta-Labeling 高信頼度精度: {filtered_acc:.1%} ({high_conf_mask.sum()}/{len(high_conf_mask)} 取引)")
    else:
        filtered_acc = stacked_acc

    # ── 回帰モデル ────────────────────────────────────────────
    print("\n--- 変動幅予測（回帰）---")
    reg = XGBRegressor(
        n_estimators=500, max_depth=5, learning_rate=0.02,
        tree_method="hist", device="cuda", early_stopping_rounds=30, random_state=42,
    )
    y_ret_train = y_ret.iloc[:split]
    y_ret_test = y_ret.iloc[split:]
    reg.fit(X_train, y_ret_train, sample_weight=w_train,
            eval_set=[(X_test, y_ret_test)], verbose=100)

    from sklearn.metrics import mean_absolute_error
    y_ret_pred = reg.predict(X_test)
    mae = mean_absolute_error(y_ret_test, y_ret_pred)
    print(f"MAE: {mae:.3f}%")

    # ── 結果サマリー ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("最終結果サマリー")
    print("=" * 60)
    print(f"XGBoost AUC:     {roc_auc_score(y_test, xgb_prob):.4f}")
    print(f"LightGBM AUC:    {roc_auc_score(y_test, lgbm_prob):.4f}")
    if has_catboost:
        print(f"CatBoost AUC:    {roc_auc_score(y_test, cat_prob):.4f}")
    print(f"Stacked AUC:     {stacked_auc:.4f}")
    print(f"Stacked Accuracy: {stacked_acc:.1%}")
    if high_conf_mask.sum() > 10:
        print(f"Meta-Label精度:  {filtered_acc:.1%} ({high_conf_mask.sum()} trades)")
    print(f"変動幅MAE:       {mae:.3f}%")

    # 特徴量重要度
    importance = pd.Series(xgb.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("\n特徴量重要度 TOP15:")
    print(importance.head(15))

    # ── 保存 ──────────────────────────────────────────────────
    with open(MODELS_DIR / "nikkei_forecast.pkl", "wb") as f:
        pickle.dump({
            "classifier": xgb,
            "classifier_lgbm": lgbm,
            "meta_learner": meta_lr,
            "meta_model": meta_model,
            "regressor": reg,
            "features": feature_cols,
            "metrics": {
                "accuracy": round(stacked_acc, 4),
                "auc": round(stacked_auc, 4),
                "mae": round(mae, 4),
                "meta_accuracy": round(filtered_acc, 4),
            },
        }, f)
    print(f"\n保存: {MODELS_DIR / 'nikkei_forecast.pkl'}")


if __name__ == "__main__":
    train()
