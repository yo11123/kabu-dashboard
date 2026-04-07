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


def predict_nikkei_tomorrow(df: pd.DataFrame | None = None) -> dict | None:
    """日経平均の翌日予測を行う。

    Returns:
        {"direction": "上昇"|"下落", "probability": float, "expected_return": float,
         "expected_price": float, "confidence": str}
        or None if model unavailable
    """
    data = _load_pickle("nikkei_forecast.pkl")
    if data is None:
        return None

    try:
        clf = data["classifier"]
        reg = data["regressor"]
        features = data["features"]

        # データ取得（一括ダウンロードで高速化）
        import yfinance as yf
        tickers_map = {
            "nikkei": "^N225", "sp500": "^GSPC", "nasdaq": "^IXIC", "dow": "^DJI",
            "vix": "^VIX", "usdjpy": "JPY=X", "us10y": "^TNX",
            "gold": "GC=F", "oil": "CL=F", "sox": "^SOX",
        }
        ticker_list = list(tickers_map.values())
        name_list = list(tickers_map.keys())

        batch = yf.download(ticker_list, period="1y", interval="1d",
                            group_by="ticker", auto_adjust=True, progress=False, threads=True)

        raw = pd.DataFrame()
        for name, ticker in zip(name_list, ticker_list):
            try:
                if len(ticker_list) == 1:
                    _df = batch.copy()
                else:
                    _df = batch[ticker].copy()
                if isinstance(_df.columns, pd.MultiIndex):
                    _df.columns = [str(c[0]).capitalize() for c in _df.columns]
                else:
                    _df.columns = [str(c).capitalize() for c in _df.columns]
                if _df.index.tz is not None:
                    _df.index = _df.index.tz_localize(None)
                _df.dropna(subset=["Close"], inplace=True)
                if not _df.empty:
                    raw[f"{name}_close"] = _df["Close"]
                    raw[f"{name}_volume"] = _df.get("Volume", 0)
            except Exception:
                continue

        raw = raw.ffill().dropna()
        if len(raw) < 200:
            return None

        nk = raw["nikkei_close"]
        feat = pd.DataFrame(index=raw.index)

        # ── 特徴量計算（学習時と完全に一致） ──────────────────

        # リターン
        for d in [1, 2, 3, 5, 10, 20, 60]:
            feat[f"nk_ret_{d}d"] = nk.pct_change(d) * 100

        # SMA 乖離率
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
        feat["nk_rsi_5"] = 100 - 100 / (
            1 + delta.clip(lower=0).rolling(5).mean()
            / (-delta.clip(upper=0)).rolling(5).mean().replace(0, np.nan)
        )

        # MACD
        ema12 = nk.ewm(span=12, adjust=False).mean()
        ema26 = nk.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        feat["nk_macd_hist"] = macd_line - macd_line.ewm(span=9, adjust=False).mean()
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

        # ── ストキャスティクス (%K, %D) ──────────────────────
        for period in [14, 9]:
            low_min = nk.rolling(period).min()
            high_max = nk.rolling(period).max()
            k = (nk - low_min) / (high_max - low_min).replace(0, np.nan) * 100
            d = k.rolling(3).mean()
            feat[f"nk_stoch_k_{period}"] = k
            feat[f"nk_stoch_d_{period}"] = d

        # ── CCI (Commodity Channel Index) ────────────────────
        for period in [20, 14]:
            tp_sma = nk.rolling(period).mean()
            tp_mad = nk.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            feat[f"nk_cci_{period}"] = (nk - tp_sma) / (0.015 * tp_mad).replace(0, np.nan)

        # ── ADX (Average Directional Index) ──────────────────
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

        # ── ATR ──────────────────────────────────────────────
        feat["nk_atr_14"] = nk_diff.abs().rolling(14).mean()
        feat["nk_atr_pct"] = feat["nk_atr_14"] / nk * 100

        # ── 一目均衡表 (Ichimoku Cloud) ──────────────────────
        high_9 = nk.rolling(9).max()
        low_9 = nk.rolling(9).min()
        high_26 = nk.rolling(26).max()
        low_26 = nk.rolling(26).min()
        high_52 = nk.rolling(52).max()
        low_52 = nk.rolling(52).min()
        tenkan = (high_9 + low_9) / 2
        kijun = (high_26 + low_26) / 2
        senkou_a = (tenkan + kijun) / 2
        senkou_b = (high_52 + low_52) / 2
        feat["nk_ichimoku_tenkan_dev"] = (nk - tenkan) / tenkan.replace(0, np.nan) * 100
        feat["nk_ichimoku_kijun_dev"] = (nk - kijun) / kijun.replace(0, np.nan) * 100
        feat["nk_ichimoku_tk_cross"] = (tenkan - kijun) / kijun.replace(0, np.nan) * 100
        feat["nk_ichimoku_cloud_top"] = (nk - senkou_a.shift(26)) / nk * 100
        feat["nk_ichimoku_cloud_bottom"] = (nk - senkou_b.shift(26)) / nk * 100
        feat["nk_ichimoku_cloud_thickness"] = (senkou_a - senkou_b) / nk * 100
        above_cloud = ((nk > senkou_a.shift(26)) & (nk > senkou_b.shift(26))).astype(int)
        below_cloud = ((nk < senkou_a.shift(26)) & (nk < senkou_b.shift(26))).astype(int)
        feat["nk_ichimoku_above_cloud"] = above_cloud
        feat["nk_ichimoku_below_cloud"] = below_cloud

        # ── Williams %R ──────────────────────────────────────
        for period in [14, 28]:
            highest = nk.rolling(period).max()
            lowest = nk.rolling(period).min()
            feat[f"nk_williams_r_{period}"] = (highest - nk) / (highest - lowest).replace(0, np.nan) * -100

        # ── OBV トレンド ─────────────────────────────────────
        if "nikkei_volume" in raw.columns:
            vol = raw["nikkei_volume"]
            obv_sign = np.sign(nk.diff()).fillna(0)
            obv = (obv_sign * vol).cumsum()
            obv_sma20 = obv.rolling(20).mean()
            feat["nk_obv_dev"] = (obv - obv_sma20) / obv_sma20.abs().replace(0, np.nan) * 100
            feat["nk_obv_slope"] = obv.pct_change(5) * 100

        # ── MA クロスオーバーシグナル ─────────────────────────
        sma5 = nk.rolling(5).mean()
        sma25 = nk.rolling(25).mean()
        sma75 = nk.rolling(75).mean()
        feat["nk_golden_cross_5_25"] = ((sma5 > sma25) & (sma5.shift(1) <= sma25.shift(1))).astype(int)
        feat["nk_dead_cross_5_25"] = ((sma5 < sma25) & (sma5.shift(1) >= sma25.shift(1))).astype(int)
        feat["nk_golden_cross_25_75"] = ((sma25 > sma75) & (sma25.shift(1) <= sma75.shift(1))).astype(int)
        feat["nk_dead_cross_25_75"] = ((sma25 < sma75) & (sma25.shift(1) >= sma75.shift(1))).astype(int)
        gc_5_25 = feat["nk_golden_cross_5_25"].replace(0, np.nan)
        dc_5_25 = feat["nk_dead_cross_5_25"].replace(0, np.nan)
        feat["nk_days_since_gc_5_25"] = gc_5_25.groupby(gc_5_25.cumsum()).cumcount()
        feat["nk_days_since_dc_5_25"] = dc_5_25.groupby(dc_5_25.cumsum()).cumcount()

        # ── ドンチャンチャネル ────────────────────────────────
        for period in [20, 50]:
            dc_high = nk.rolling(period).max()
            dc_low = nk.rolling(period).min()
            feat[f"nk_donchian_pos_{period}"] = (nk - dc_low) / (dc_high - dc_low).replace(0, np.nan)

        # ── TRIX ─────────────────────────────────────────────
        ema1 = nk.ewm(span=15, adjust=False).mean()
        ema2 = ema1.ewm(span=15, adjust=False).mean()
        ema3 = ema2.ewm(span=15, adjust=False).mean()
        feat["nk_trix"] = ema3.pct_change() * 10000

        # ── 出来高比率 ───────────────────────────────────────
        if "nikkei_volume" in raw.columns:
            nvol = raw["nikkei_volume"]
            feat["nk_vol_ratio_5_20"] = nvol.rolling(5).mean() / nvol.rolling(20).mean().replace(0, np.nan)
            feat["nk_vol_spike"] = nvol / nvol.rolling(20).mean().replace(0, np.nan)

        # ── カレンダー ───────────────────────────────────────
        feat["weekday"] = raw.index.dayofweek
        feat["month"] = raw.index.month
        feat["is_first_half"] = (raw.index.month <= 6).astype(int)
        feat["is_month_end"] = (raw.index.day >= 25).astype(int)
        feat["is_month_start"] = (raw.index.day <= 5).astype(int)

        # ── 米国市場 ─────────────────────────────────────────
        for name in ["sp500", "nasdaq", "dow"]:
            col = f"{name}_close"
            if col in raw.columns:
                feat[f"{name}_ret_1d"] = raw[col].pct_change() * 100
                feat[f"{name}_ret_5d"] = raw[col].pct_change(5) * 100
        if "sox_close" in raw.columns:
            feat["sox_ret_1d"] = raw["sox_close"].pct_change() * 100
            feat["sox_ret_5d"] = raw["sox_close"].pct_change(5) * 100

        # ── VIX ──────────────────────────────────────────────
        if "vix_close" in raw.columns:
            feat["vix"] = raw["vix_close"]
            feat["vix_change"] = raw["vix_close"].pct_change() * 100
            feat["vix_ma5_dev"] = (raw["vix_close"] - raw["vix_close"].rolling(5).mean()) / raw["vix_close"].rolling(5).mean() * 100
            feat["vix_ma20_dev"] = (raw["vix_close"] - raw["vix_close"].rolling(20).mean()) / raw["vix_close"].rolling(20).mean() * 100
            feat["vix_regime"] = pd.cut(raw["vix_close"], bins=[0, 15, 20, 30, 100], labels=[0, 1, 2, 3]).astype(float)

        # ── 為替 ─────────────────────────────────────────────
        if "usdjpy_close" in raw.columns:
            feat["usdjpy"] = raw["usdjpy_close"]
            feat["usdjpy_ret_1d"] = raw["usdjpy_close"].pct_change() * 100
            feat["usdjpy_ret_5d"] = raw["usdjpy_close"].pct_change(5) * 100
            feat["usdjpy_ret_20d"] = raw["usdjpy_close"].pct_change(20) * 100

        # ── 金利 ─────────────────────────────────────────────
        if "us10y_close" in raw.columns:
            feat["us10y"] = raw["us10y_close"]
            feat["us10y_change"] = raw["us10y_close"].diff()

        # ── コモディティ ─────────────────────────────────────
        for name in ["gold", "oil"]:
            col = f"{name}_close"
            if col in raw.columns:
                feat[f"{name}_ret_1d"] = raw[col].pct_change() * 100
                feat[f"{name}_ret_5d"] = raw[col].pct_change(5) * 100

        # ── 日経 vs S&P500 アルファ ──────────────────────────
        if "sp500_close" in raw.columns:
            feat["nk_alpha_5d"] = feat.get("nk_ret_5d", 0) - feat.get("sp500_ret_5d", 0)

        # 最新行で予測
        row = feat.iloc[-1:]
        for f in features:
            if f not in row.columns:
                row[f] = 0
        row = row[features].fillna(0).replace([np.inf, -np.inf], 0)
        for col in row.columns:
            row[col] = pd.to_numeric(row[col], errors="coerce")
        row = row.fillna(0)

        # 予測（ベース）
        up_prob = float(clf.predict_proba(row)[0][1]) * 100
        expected_ret = float(reg.predict(row)[0])
        current_price = float(nk.iloc[-1])

        # ── ニュースセンチメントで補正 ────────────────────────
        news_sentiment = 0.0
        news_summary = ""
        try:
            from modules.market_news import fetch_all_news
            all_news = fetch_all_news()
            if all_news:
                pos_words = [
                    "上昇", "高値", "好調", "増収", "増益", "上方修正", "反発", "回復",
                    "成長", "好決算", "増配", "最高益", "黒字", "拡大", "買い",
                    "rally", "surge", "gain", "rise", "bull", "beat",
                ]
                neg_words = [
                    "下落", "安値", "低迷", "減収", "減益", "下方修正", "暴落", "悪化",
                    "減配", "赤字", "縮小", "リスク", "懸念", "戦争", "制裁", "売り",
                    "crash", "plunge", "loss", "fall", "bear", "miss",
                ]
                scores = []
                key_headlines = []
                for cat_name, items in all_news.items():
                    for item in items[:5]:
                        title = item.get("title", "").lower()
                        p = sum(1 for w in pos_words if w in title)
                        n = sum(1 for w in neg_words if w in title)
                        if p + n > 0:
                            s = (p - n) / (p + n)
                            scores.append(s)
                            if abs(s) > 0.3:
                                key_headlines.append(item.get("title", ""))
                if scores:
                    news_sentiment = np.mean(scores)

                # ニュースの影響を要約
                if key_headlines:
                    news_summary = key_headlines[0][:50]
        except Exception:
            pass

        # センチメントでML予測を補正（最大±10%の補正）
        sentiment_adjustment = news_sentiment * 10  # -10% 〜 +10%
        up_prob_adjusted = max(0, min(100, up_prob + sentiment_adjustment))
        ret_adjustment = news_sentiment * 0.3  # 最大±0.3%の変動幅補正
        expected_ret_adjusted = expected_ret + ret_adjustment

        expected_price = current_price * (1 + expected_ret_adjusted / 100)

        direction = "上昇" if up_prob_adjusted > 50 else "下落"
        if up_prob_adjusted > 65:
            confidence = "高い"
        elif up_prob_adjusted > 55:
            confidence = "やや高い"
        elif up_prob_adjusted < 35:
            confidence = "高い（下落）"
        elif up_prob_adjusted < 45:
            confidence = "やや高い（下落）"
        else:
            confidence = "五分五分"

        return {
            "direction": direction,
            "probability": round(up_prob_adjusted, 1),
            "probability_base": round(up_prob, 1),
            "expected_return": round(expected_ret_adjusted, 2),
            "expected_price": round(expected_price, 0),
            "current_price": round(current_price, 0),
            "confidence": confidence,
            "news_sentiment": round(news_sentiment, 2),
            "news_impact": "強気" if news_sentiment > 0.2 else ("弱気" if news_sentiment < -0.2 else "中立"),
            "news_headline": news_summary,
        }
    except Exception:
        return None


def get_available_models() -> dict[str, bool]:
    """利用可能なモデルの一覧を返す。"""
    return {
        "XGBoost方向予測": (_MODELS_DIR / "xgboost_direction.pkl").exists(),
        "LSTM方向予測": (_MODELS_DIR / "lstm_direction.pt").exists(),
        "決算サプライズ": (_MODELS_DIR / "xgboost_earnings.pkl").exists(),
        "最適売買タイミング": (_MODELS_DIR / "xgboost_timing.pkl").exists(),
        "日経平均翌日予測": (_MODELS_DIR / "nikkei_forecast.pkl").exists(),
    }


def calc_optimal_thresholds(df: pd.DataFrame) -> dict:
    """学習済みモデルの予測確率分布から最適な売買閾値を計算する。

    過去データに対する予測確率を算出し、
    実際のリターンとの関係から最もシャープレシオが高くなる閾値を探索する。

    Returns:
        {"buy": float, "sell": float, "method": str}
    """
    data = _load_pickle("xgboost_timing.pkl") or _load_pickle("xgboost_direction.pkl")
    if data is None or len(df) < 350:
        return {"buy": 60, "sell": 40, "method": "デフォルト"}

    model = data["model"]
    features = data["features"]

    try:
        feat = _calc_features(df)
        # 5日後リターン
        future_ret = df["Close"].shift(-5) / df["Close"] - 1
        feat["future_ret"] = future_ret
        feat = feat.dropna()
        if len(feat) < 100:
            return {"buy": 60, "sell": 40, "method": "データ不足"}

        # 予測確率を計算
        X = feat.drop(columns=["future_ret"])
        for f in features:
            if f not in X.columns:
                X[f] = 0
        X = X[features].fillna(0).replace([np.inf, -np.inf], 0)
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors="coerce")
        X = X.fillna(0)

        probs = model.predict_proba(X)[:, 1] * 100
        rets = feat["future_ret"].values

        # グリッドサーチで最適閾値を探索
        best_sharpe = -999
        best_buy = 60
        best_sell = 40

        for buy_th in range(55, 80, 5):
            for sell_th in range(25, buy_th - 5, 5):
                # シミュレーション
                in_pos = False
                trade_rets = []
                for i in range(len(probs)):
                    if not in_pos and probs[i] > buy_th:
                        in_pos = True
                        entry_ret = rets[i]
                    elif in_pos and probs[i] < sell_th:
                        in_pos = False
                        trade_rets.append(entry_ret)

                if len(trade_rets) < 5:
                    continue
                arr = np.array(trade_rets)
                mean_r = arr.mean()
                std_r = arr.std()
                if std_r > 0:
                    sharpe = mean_r / std_r * np.sqrt(52)  # 週次換算
                    if sharpe > best_sharpe:
                        best_sharpe = sharpe
                        best_buy = buy_th
                        best_sell = sell_th

        return {
            "buy": best_buy,
            "sell": best_sell,
            "sharpe": round(best_sharpe, 2),
            "method": "ML最適化",
        }
    except Exception:
        return {"buy": 60, "sell": 40, "method": "計算エラー"}
