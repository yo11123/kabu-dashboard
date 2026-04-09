"""
改善版 全MLモデル一括学習（v3）

v2 からの改善点:
  1. NPMM ラベリング（局所極値ベースのラベル付け）
  2. Purged Cross-Validation + Embargo
  3. 遺伝的アルゴリズムによる特徴量選択（方向モデル）
  4. サンプルウェイト（指数減衰 + イベント重み）
  5. 分数階差分（Fractional Differentiation）特徴量
  6. レジーム検出（HMM）特徴量
  7. セクター相対特徴量
  8. ニュースセンチメント（方向モデルにも追加）
  9. 3モデルスタッキング（XGBoost + LightGBM + CatBoost → Logistic Regression）

使い方:
    python train/train_all_v3.py
"""
import os
import sys
import warnings
import pickle
import json
import time
import random
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

# オプション依存ライブラリ
try:
    from scipy.signal import argrelextrema
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("[WARN] scipy 未インストール。NPMMラベリング無効。")

try:
    from hmmlearn.hmm import GaussianHMM
    HAS_HMM = True
except ImportError:
    HAS_HMM = False
    print("[WARN] hmmlearn 未インストール。レジーム検出無効。")

try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False
    print("[WARN] catboost 未インストール。CatBoostスタッキング無効。")


# ═══════════════════════════════════════════════════════════════════
# 銘柄リスト取得（セクター情報付き）
# ═══════════════════════════════════════════════════════════════════


def load_all_tse_tickers() -> tuple[list[str], dict[str, str]]:
    """東証全銘柄のティッカーコードとセクターマッピングを取得する。"""
    import io

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

            try:
                df = pd.read_excel(io.BytesIO(resp.content), dtype=str)
            except Exception:
                df = pd.read_excel(io.BytesIO(resp.content), dtype=str, engine="xlrd")

            # コード列を探す
            code_col = None
            sector_col = None
            for col in df.columns:
                col_str = str(col).strip()
                if "コード" in col_str or "code" in col_str.lower():
                    code_col = col
                if "業種" in col_str or "33" in col_str:
                    sector_col = col
            if code_col is None:
                code_col = df.columns[0]

            codes = df[code_col].dropna().astype(str).str.strip().str.replace(".0", "", regex=False)
            tickers = [f"{c}.T" for c in codes if c.isdigit() and len(c) == 4]

            # セクターマッピング構築
            ticker_to_sector = {}
            if sector_col is not None:
                for _, row in df.iterrows():
                    c = str(row[code_col]).strip().replace(".0", "")
                    s = str(row[sector_col]).strip() if pd.notna(row[sector_col]) else "不明"
                    if c.isdigit() and len(c) == 4:
                        ticker_to_sector[f"{c}.T"] = s

            if len(tickers) > 500:
                print(f"JPXから {len(tickers)} 銘柄を取得 (セクター情報: {len(ticker_to_sector)} 件)")
                return tickers, ticker_to_sector
        except Exception as e:
            print(f"JPXリスト取得試行失敗 ({url[:50]}...): {e}")
            continue

    # フォールバック: ローカルのdata_loaderを使う
    try:
        sys.path.insert(0, str(ROOT))
        from modules.data_loader import _fetch_tse_raw
        stocks = _fetch_tse_raw()
        tickers = [s["code"] for s in stocks]
        ticker_to_sector = {s["code"]: s.get("sector", "不明") for s in stocks}
        print(f"data_loaderから {len(tickers)} 銘柄を取得")
        return tickers, ticker_to_sector
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
    tickers = [c for c in codes if c.endswith(".T")]
    print(f"最終フォールバック: 日経225 ({len(tickers)} 銘柄)")
    return tickers, {}


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
# 改善5: 分数階差分（Fractional Differentiation）
# ═══════════════════════════════════════════════════════════════════


def _get_frac_diff_weights(d: float, thresh: float = 1e-5) -> np.ndarray:
    """Lopez de Prado の固定幅ウィンドウ分数階差分の重みを計算。"""
    w = [1.0]
    k = 1
    while True:
        w_new = -w[-1] * (d - k + 1) / k
        if abs(w_new) < thresh:
            break
        w.append(w_new)
        k += 1
    return np.array(w[::-1])


def frac_diff(series: pd.Series, d: float = 0.4, thresh: float = 1e-5) -> pd.Series:
    """固定幅ウィンドウ分数階差分。記憶を保持しつつ定常性を向上させる。"""
    weights = _get_frac_diff_weights(d, thresh)
    width = len(weights)
    result = pd.Series(index=series.index, dtype=float)
    for i in range(width - 1, len(series)):
        window = series.iloc[i - width + 1:i + 1].values
        if len(window) == width:
            result.iloc[i] = np.dot(weights, window)
    return result


# ═══════════════════════════════════════════════════════════════════
# 改善6: レジーム検出（HMM）
# ═══════════════════════════════════════════════════════════════════

# グローバルにHMMモデルをキャッシュ（マーケット全体で1つ）
_hmm_model_cache = None


def fit_regime_model(market: pd.DataFrame) -> object | None:
    """マーケットリターン+ボラティリティからHMM（3状態）をフィット。"""
    global _hmm_model_cache
    if _hmm_model_cache is not None:
        return _hmm_model_cache
    if not HAS_HMM:
        return None
    try:
        nikkei_col = "mkt_nikkei"
        if nikkei_col not in market.columns:
            return None
        ret = market[nikkei_col].pct_change().dropna()
        vol = ret.rolling(20).std().dropna()
        common_idx = ret.index.intersection(vol.index)
        if len(common_idx) < 100:
            return None
        X_hmm = np.column_stack([ret.loc[common_idx].values, vol.loc[common_idx].values])
        X_hmm = np.nan_to_num(X_hmm, nan=0, posinf=0, neginf=0)
        hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=200, random_state=42)
        hmm.fit(X_hmm)
        _hmm_model_cache = hmm
        print("  HMMレジーム検出モデルをフィット完了（3状態）")
        return hmm
    except Exception as e:
        print(f"  HMMフィット失敗: {e}")
        return None


def predict_regime(market: pd.DataFrame, hmm_model) -> pd.DataFrame:
    """HMMでレジーム状態と確率を予測し、DataFrameで返す。"""
    regime_df = pd.DataFrame(index=market.index)
    if hmm_model is None or not HAS_HMM:
        return regime_df
    try:
        nikkei_col = "mkt_nikkei"
        ret = market[nikkei_col].pct_change().fillna(0)
        vol = ret.rolling(20).std().fillna(0)
        X_hmm = np.column_stack([ret.values, vol.values])
        X_hmm = np.nan_to_num(X_hmm, nan=0, posinf=0, neginf=0)
        states = hmm_model.predict(X_hmm)
        probs = hmm_model.predict_proba(X_hmm)
        regime_df["regime_state"] = states
        for i in range(probs.shape[1]):
            regime_df[f"regime_prob_{i}"] = probs[:, i]
    except Exception:
        pass
    return regime_df


# ═══════════════════════════════════════════════════════════════════
# 改善1: NPMM ラベリング
# ═══════════════════════════════════════════════════════════════════


def npmm_label(close: pd.Series, order: int = 10, threshold: float = 0.02,
               fallback_days: int = 5) -> pd.Series:
    """
    N-Period Min-Max ラベリング。
    局所極小→1（買いポイント）、局所極大→0（売りポイント）、
    それ以外は従来の閾値ラベルにフォールバック。
    """
    labels = pd.Series(np.nan, index=close.index)

    if HAS_SCIPY and len(close) > order * 2:
        # 局所極小点 → 上昇転換 → 1
        local_min_idx = argrelextrema(close.values, np.less_equal, order=order)[0]
        # 局所極大点 → 下降転換 → 0
        local_max_idx = argrelextrema(close.values, np.greater_equal, order=order)[0]

        for idx in local_min_idx:
            labels.iloc[idx] = 1
        for idx in local_max_idx:
            labels.iloc[idx] = 0

    # 極値でないポイントは従来の閾値ラベルにフォールバック
    fallback_mask = labels.isna()
    future_ret = close.shift(-fallback_days) / close - 1
    labels[fallback_mask] = (future_ret[fallback_mask] > threshold).astype(float)

    return labels


# ═══════════════════════════════════════════════════════════════════
# 改善4: サンプルウェイト（指数減衰 + イベント + ボラティリティ）
# ═══════════════════════════════════════════════════════════════════


def compute_sample_weights(dates: pd.DatetimeIndex, market: pd.DataFrame | None = None,
                           earnings_dates: set | None = None,
                           half_life: int = 504) -> np.ndarray:
    """
    指数減衰ウェイト + 決算日周辺1.5x + 高VIX期間1.2x。
    """
    n = len(dates)
    if n == 0:
        return np.array([])

    # 指数減衰: 最新=1.0, half_life日前=0.5
    days_ago = (dates.max() - dates).days.values.astype(float)
    decay = np.exp(-np.log(2) * days_ago / half_life)

    weights = decay.copy()

    # 決算日周辺 ±3日 → 1.5x
    if earnings_dates:
        for i, dt in enumerate(dates):
            for ed in earnings_dates:
                if abs((dt - ed).days) <= 3:
                    weights[i] *= 1.5
                    break

    # 高VIX期間 → 1.2x
    if market is not None and "mkt_vix" in market.columns:
        vix_series = market["mkt_vix"].reindex(dates).ffill().fillna(20)
        high_vix_mask = vix_series.values > 25
        weights[high_vix_mask] *= 1.2

    # 正規化（平均1.0にする）
    weights = weights / weights.mean()
    return weights


# ═══════════════════════════════════════════════════════════════════
# 改善2: Purged K-Fold Cross-Validation with Embargo
# ═══════════════════════════════════════════════════════════════════


class PurgedKFold:
    """
    時系列用 Purged K-Fold CV。
    - purge_gap: 訓練と検証の間に設けるバッファ日数
    - embargo_pct: テストフォールド後に除外する割合
    """

    def __init__(self, n_splits: int = 5, purge_gap: int = 10, embargo_pct: float = 0.02):
        self.n_splits = n_splits
        self.purge_gap = purge_gap
        self.embargo_pct = embargo_pct

    def split(self, X):
        n = len(X)
        embargo = int(n * self.embargo_pct)
        fold_size = n // self.n_splits

        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = min((i + 1) * fold_size, n)

            # 訓練インデックス: テスト期間の前後を除外
            train_idx = []
            for j in range(n):
                # パージ: テスト開始の purge_gap 日前から除外
                if j < test_start - self.purge_gap:
                    train_idx.append(j)
                # エンバーゴ: テスト終了後 embargo 日間を除外
                elif j >= test_end + embargo:
                    train_idx.append(j)

            test_idx = list(range(test_start, test_end))
            if len(train_idx) > 0 and len(test_idx) > 0:
                yield np.array(train_idx), np.array(test_idx)


# ═══════════════════════════════════════════════════════════════════
# 改善3: 遺伝的アルゴリズム特徴量選択
# ═══════════════════════════════════════════════════════════════════


def ga_feature_selection(X: pd.DataFrame, y: pd.Series,
                         sample_weight: np.ndarray | None = None,
                         pop_size: int = 30, n_gen: int = 20,
                         mutation_rate: float = 0.05,
                         top_k: int = 10, threshold: float = 0.6) -> list[str]:
    """
    遺伝的アルゴリズムで最適な特徴量サブセットを選択。
    fitness = Purged CV の平均AUC。
    """
    from xgboost import XGBClassifier
    from sklearn.metrics import roc_auc_score

    n_features = X.shape[1]
    feature_names = list(X.columns)

    print(f"\n=== GA特徴量選択 ({n_features} 特徴量, {pop_size}個体 x {n_gen}世代) ===")

    # 初期個体群: ランダムバイナリマスク（最低10特徴量）
    population = []
    for _ in range(pop_size):
        mask = np.random.binomial(1, 0.5, n_features).astype(bool)
        if mask.sum() < 10:
            idx = np.random.choice(n_features, 10, replace=False)
            mask[idx] = True
        population.append(mask)

    # サンプリングで高速化（最大10万サンプル）
    if len(X) > 100_000:
        sample_idx = np.random.choice(len(X), 100_000, replace=False)
        X_ga = X.iloc[sample_idx].reset_index(drop=True)
        y_ga = y.iloc[sample_idx].reset_index(drop=True)
        w_ga = sample_weight[sample_idx] if sample_weight is not None else None
    else:
        X_ga = X.reset_index(drop=True)
        y_ga = y.reset_index(drop=True)
        w_ga = sample_weight

    def evaluate(mask):
        """1個体の適応度を評価（簡易2-fold CV）"""
        selected = np.where(mask)[0]
        if len(selected) < 5:
            return 0.0
        X_sel = X_ga.iloc[:, selected]
        split = int(len(X_sel) * 0.7)
        X_tr, X_te = X_sel.iloc[:split], X_sel.iloc[split:]
        y_tr, y_te = y_ga.iloc[:split], y_ga.iloc[split:]
        w_tr = w_ga[:split] if w_ga is not None else None

        try:
            model = XGBClassifier(
                n_estimators=100, max_depth=5, learning_rate=0.1,
                tree_method="hist", device="cuda",
                eval_metric="auc", random_state=42, verbosity=0,
            )
            model.fit(X_tr, y_tr, sample_weight=w_tr, verbose=False)
            prob = model.predict_proba(X_te)[:, 1]
            return roc_auc_score(y_te, prob)
        except Exception:
            return 0.0

    best_fitness_history = []

    for gen in range(n_gen):
        # 適応度評価
        fitness = np.array([evaluate(m) for m in population])
        best_idx = np.argmax(fitness)
        best_fitness_history.append(fitness[best_idx])

        if (gen + 1) % 5 == 0 or gen == 0:
            print(f"  世代 {gen+1:2d}: 最高AUC={fitness[best_idx]:.4f}, "
                  f"平均AUC={fitness.mean():.4f}, "
                  f"特徴量数={population[best_idx].sum()}")

        # 次世代生成
        new_pop = [population[best_idx].copy()]  # エリート保存

        while len(new_pop) < pop_size:
            # トーナメント選択 (k=3)
            def tournament():
                candidates = random.sample(range(pop_size), 3)
                winner = max(candidates, key=lambda i: fitness[i])
                return population[winner]

            p1, p2 = tournament(), tournament()

            # 一様交叉
            child = np.where(np.random.random(n_features) < 0.5, p1, p2)

            # 突然変異
            mut_mask = np.random.random(n_features) < mutation_rate
            child[mut_mask] = ~child[mut_mask]

            # 最低10特徴量を保証
            if child.sum() < 10:
                idx = np.random.choice(n_features, 10, replace=False)
                child[idx] = True

            new_pop.append(child)

        population = new_pop

    # 最終世代のトップ10個体で頻度が60%以上の特徴量を採用
    final_fitness = np.array([evaluate(m) for m in population])
    top_indices = np.argsort(final_fitness)[-top_k:]
    freq = np.zeros(n_features)
    for idx in top_indices:
        freq += population[idx].astype(float)
    freq /= top_k

    selected_mask = freq >= threshold
    selected_features = [feature_names[i] for i in range(n_features) if selected_mask[i]]

    print(f"\n  GA結果: {n_features} → {len(selected_features)} 特徴量を選択")
    print(f"  最終世代最高AUC: {final_fitness.max():.4f}")

    # 最低限の特徴量を保証
    if len(selected_features) < 20:
        # 重要度上位で補填
        top_all = np.argsort(final_fitness)[-1]
        remaining = [feature_names[i] for i in range(n_features)
                     if feature_names[i] not in selected_features and population[top_all][i]]
        selected_features.extend(remaining[:20 - len(selected_features)])

    return selected_features


# ═══════════════════════════════════════════════════════════════════
# ニュースセンチメント（改善8: 方向モデルにも追加）
# ═══════════════════════════════════════════════════════════════════


def _news_sentiment(text: str) -> float:
    """キーワードベースのニュースセンチメントスコア。"""
    pos = ["上昇", "高値", "好調", "増収", "増益", "上方修正", "反発", "回復", "成長",
           "好決算", "増配", "自社株買い", "最高益", "黒字", "拡大",
           "surge", "rally", "gain", "rise", "bull", "upgrade", "beat",
           "outperform", "strong", "positive", "record"]
    neg = ["下落", "安値", "低迷", "減収", "減益", "下方修正", "暴落", "悪化",
           "減配", "赤字", "縮小", "リスク", "懸念", "不安", "戦争", "制裁",
           "crash", "plunge", "loss", "fall", "bear", "downgrade", "miss",
           "weak", "negative", "warning", "decline"]
    t = text.lower()
    p = sum(1 for w in pos if w in t)
    n = sum(1 for w in neg if w in t)
    return (p - n) / max(p + n, 1)


def get_news_sentiment(ticker: str) -> float:
    """銘柄のニュースセンチメントを取得。"""
    try:
        news = yf.Ticker(ticker).news
        titles = [n.get("title", "") for n in (news if isinstance(news, list) else [])][:20]
        if titles:
            return float(np.mean([_news_sentiment(t) for t in titles]))
    except Exception:
        pass
    return 0.0


# ═══════════════════════════════════════════════════════════════════
# 特徴量計算（v3: 分数階差分 + レジーム + セクター相対）
# ═══════════════════════════════════════════════════════════════════


def calc_features_v3(df: pd.DataFrame, market: pd.DataFrame | None = None,
                     regime_df: pd.DataFrame | None = None,
                     sector_medians: pd.DataFrame | None = None,
                     news_sentiment: float = 0.0) -> pd.DataFrame:
    """
    v3 特徴量: v2 の全特徴量 + 分数階差分 + レジーム + セクター相対 + ニュース。
    """
    close = df["Close"].copy()
    high = df["High"].copy()
    low = df["Low"].copy()
    volume = df["Volume"].copy() if "Volume" in df.columns else pd.Series(0, index=df.index)
    opn = df["Open"].copy() if "Open" in df.columns else close.copy()

    feat = pd.DataFrame(index=df.index)

    # ══════════════════════════════════════════════════
    # v2 互換テクニカル指標（全て維持）
    # ══════════════════════════════════════════════════

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    feat["rsi_14"] = 100 - 100 / (1 + gain / loss)
    gain5 = delta.clip(lower=0).rolling(5).mean()
    loss5 = (-delta.clip(upper=0)).rolling(5).mean().replace(0, np.nan)
    feat["rsi_5"] = 100 - 100 / (1 + gain5 / loss5)

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    feat["macd"] = ema12 - ema26
    feat["macd_signal"] = feat["macd"].ewm(span=9, adjust=False).mean()
    feat["macd_hist"] = feat["macd"] - feat["macd_signal"]
    feat["macd_hist_diff"] = feat["macd_hist"].diff()

    # ボリンジャーバンド
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    feat["bb_position"] = (close - bb_mid) / bb_std.replace(0, np.nan)
    feat["bb_width"] = (bb_std * 4) / bb_mid.replace(0, np.nan) * 100
    feat["bb_width_change"] = feat["bb_width"].pct_change(5) * 100

    # 移動平均乖離率
    for period in [5, 25, 75, 200]:
        sma = close.rolling(period).mean()
        feat[f"sma{period}_dev"] = (close - sma) / sma * 100

    sma25 = close.rolling(25).mean()
    sma75 = close.rolling(75).mean()
    feat["sma25_slope"] = sma25.pct_change(5) * 100
    feat["sma75_slope"] = sma75.pct_change(10) * 100

    if len(close) >= 75:
        feat["sma_cross_gap"] = (sma25 - sma75) / sma75 * 100

    # リターン
    for days in [1, 2, 3, 5, 10, 20, 60]:
        feat[f"return_{days}d"] = close.pct_change(days) * 100

    # ボラティリティ
    feat["volatility_20d"] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    feat["volatility_5d"] = close.pct_change().rolling(5).std() * np.sqrt(252) * 100
    feat["vol_change"] = feat["volatility_5d"] - feat["volatility_20d"]

    # ATR
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    feat["atr_14"] = tr.rolling(14).mean() / close * 100

    # 出来高
    vol_ma20 = volume.rolling(20).mean()
    feat["volume_ratio"] = volume / vol_ma20.replace(0, np.nan)
    feat["volume_change_5d"] = volume.rolling(5).mean() / volume.rolling(20).mean()
    up_mask = close > opn
    up_vol = (volume * up_mask.astype(float)).rolling(10).mean()
    dn_vol = (volume * (~up_mask).astype(float)).rolling(10).mean()
    feat["volume_up_dn_ratio"] = up_vol / dn_vol.replace(0, np.nan)

    # ストキャスティクス
    low14 = low.rolling(14).min()
    high14 = high.rolling(14).max()
    feat["stoch_k"] = (close - low14) / (high14 - low14).replace(0, np.nan) * 100
    feat["stoch_d"] = feat["stoch_k"].rolling(3).mean()

    # CCI
    tp = (high + low + close) / 3
    feat["cci_20"] = (tp - tp.rolling(20).mean()) / (tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean()) * 0.015)

    # 52週高安
    feat["from_52w_high"] = (close / close.rolling(252).max() - 1) * 100
    feat["from_52w_low"] = (close / close.rolling(252).min() - 1) * 100

    # 自己相関・上昇日比率
    feat["autocorr_5d"] = close.pct_change().rolling(20).apply(
        lambda x: x.autocorr(lag=1) if len(x.dropna()) > 5 else np.nan, raw=False
    )
    feat["up_day_ratio_10d"] = (close.diff() > 0).rolling(10).mean()
    feat["up_day_ratio_20d"] = (close.diff() > 0).rolling(20).mean()

    # シャープレシオ
    ret20 = close.pct_change().rolling(20)
    feat["sharpe_20d"] = ret20.mean() / ret20.std().replace(0, np.nan) * np.sqrt(252)

    # ハースト指数近似
    feat["hurst_proxy"] = close.pct_change().rolling(60).apply(
        lambda x: np.log(x.std()) / np.log(len(x)) if x.std() > 0 else np.nan, raw=False
    )

    # VWAP乖離
    if volume.sum() > 0:
        vwap = (close * volume).rolling(20).sum() / volume.rolling(20).sum().replace(0, np.nan)
        feat["vwap_dev"] = (close - vwap) / vwap * 100

    # ローソク足形状
    feat["candle_body"] = (close - opn) / opn * 100
    feat["candle_body_avg5"] = feat["candle_body"].rolling(5).mean()
    feat["upper_shadow"] = (high - pd.concat([close, opn], axis=1).max(axis=1)) / close * 100
    feat["lower_shadow"] = (pd.concat([close, opn], axis=1).min(axis=1) - low) / close * 100

    # 一目均衡表
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

    # ADX / DMI
    if len(close) >= 28:
        plus_dm = (high.diff()).clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        feat["adx_plus_di"] = 100 * plus_dm.rolling(14).mean() / tr.rolling(14).mean().replace(0, np.nan)
        feat["adx_minus_di"] = 100 * minus_dm.rolling(14).mean() / tr.rolling(14).mean().replace(0, np.nan)
        di_diff = (feat["adx_plus_di"] - feat["adx_minus_di"]).abs()
        di_sum = (feat["adx_plus_di"] + feat["adx_minus_di"]).replace(0, np.nan)
        feat["adx"] = (di_diff / di_sum * 100).rolling(14).mean()
        feat["di_diff"] = feat["adx_plus_di"] - feat["adx_minus_di"]

    # Williams %R
    for period in [14, 28]:
        highest = high.rolling(period).max()
        lowest = low.rolling(period).min()
        feat[f"williams_r_{period}"] = (highest - close) / (highest - lowest).replace(0, np.nan) * -100

    # ドンチャンチャネル
    for period in [20, 50]:
        dc_high = high.rolling(period).max()
        dc_low = low.rolling(period).min()
        feat[f"donchian_pos_{period}"] = (close - dc_low) / (dc_high - dc_low).replace(0, np.nan)

    # TRIX
    e1 = close.ewm(span=15, adjust=False).mean()
    e2 = e1.ewm(span=15, adjust=False).mean()
    e3 = e2.ewm(span=15, adjust=False).mean()
    feat["trix"] = e3.pct_change() * 10000

    # MAクロスシグナル
    if len(close) >= 75:
        feat["golden_cross_5_25"] = ((sma25 > sma75) & (sma25.shift(1) <= sma75.shift(1))).astype(int)
        feat["dead_cross_5_25"] = ((sma25 < sma75) & (sma25.shift(1) >= sma75.shift(1))).astype(int)

    # OBV
    if volume.sum() > 0:
        obv_sign = np.sign(close.diff()).fillna(0)
        obv = (obv_sign * volume).cumsum()
        obv_sma20 = obv.rolling(20).mean()
        feat["obv_dev"] = (obv - obv_sma20) / obv_sma20.abs().replace(0, np.nan) * 100
        feat["obv_slope"] = obv.pct_change(5) * 100

    feat["weekday"] = df.index.dayofweek
    feat["month"] = df.index.month

    # ══════════════════════════════════════════════════
    # v3 新規特徴量
    # ══════════════════════════════════════════════════

    # 改善5: 分数階差分（d=0.3, 0.4）
    if len(close) > 100:
        for d_val in [0.3, 0.4]:
            fd = frac_diff(close, d=d_val)
            feat[f"frac_diff_close_d{str(d_val).replace('.', '')}"] = fd

    # 改善8: ニュースセンチメント（スカラー値を全行に設定）
    feat["news_sentiment"] = news_sentiment

    # マーケット全体指標をマージ
    if market is not None:
        for col in market.columns:
            feat[col] = market[col].reindex(feat.index).ffill()

        # 個別銘柄 vs 市場の相対リターン（アルファ）
        if "mkt_nikkei_ret5d" in market.columns:
            feat["alpha_5d"] = feat.get("return_5d", 0) - market["mkt_nikkei_ret5d"].reindex(feat.index).ffill()
        if "mkt_nikkei_ret20d" in market.columns:
            feat["alpha_20d"] = feat.get("return_20d", 0) - market["mkt_nikkei_ret20d"].reindex(feat.index).ffill()

    # 改善6: レジーム特徴量
    if regime_df is not None and not regime_df.empty:
        for col in regime_df.columns:
            feat[col] = regime_df[col].reindex(feat.index).ffill()

    # 改善7: セクター相対特徴量
    if sector_medians is not None and not sector_medians.empty:
        for metric in ["return_5d", "return_20d", "volatility_20d", "volume_ratio"]:
            sector_col = f"sector_median_{metric}"
            if sector_col in sector_medians.columns and metric in feat.columns:
                feat[f"sector_rel_{metric}"] = (
                    feat[metric] - sector_medians[sector_col].reindex(feat.index).ffill()
                )

    return feat


# ═══════════════════════════════════════════════════════════════════
# セクター中央値の事前計算
# ═══════════════════════════════════════════════════════════════════


def precompute_sector_medians(tickers: list[str], ticker_to_sector: dict,
                              market: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    セクターごとの中央値指標を事前計算する。
    返り値: {sector_name: DataFrame(日付 x metric)} のdict。
    """
    print("\nセクター相対指標を事前計算中...")
    sector_data = {}  # sector -> [(dates, return_5d, return_20d, vol20, vol_ratio)]

    # サンプリング: 各セクターから最大50銘柄
    sector_tickers = {}
    for t in tickers:
        s = ticker_to_sector.get(t, "不明")
        if s not in sector_tickers:
            sector_tickers[s] = []
        sector_tickers[s].append(t)

    for sector, stickers in sector_tickers.items():
        sample = stickers[:50] if len(stickers) > 50 else stickers
        metrics_list = []

        for ticker in sample:
            try:
                df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
                if df is None or df.empty or len(df) < 100:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [str(c[0]).capitalize() for c in df.columns]
                else:
                    df.columns = [str(c).capitalize() for c in df.columns]
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)

                close = df["Close"]
                volume = df["Volume"] if "Volume" in df.columns else pd.Series(0, index=df.index)
                row = pd.DataFrame(index=df.index)
                row["return_5d"] = close.pct_change(5) * 100
                row["return_20d"] = close.pct_change(20) * 100
                row["volatility_20d"] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
                row["volume_ratio"] = volume / volume.rolling(20).mean().replace(0, np.nan)
                metrics_list.append(row)
            except Exception:
                continue

        if metrics_list:
            combined = pd.concat(metrics_list)
            median_df = combined.groupby(combined.index).median()
            median_df.columns = [f"sector_median_{c}" for c in median_df.columns]
            sector_data[sector] = median_df

    print(f"  {len(sector_data)} セクターの中央値を計算完了")
    return sector_data


# ═══════════════════════════════════════════════════════════════════
# 共通: yfinance データ取得ヘルパー
# ═══════════════════════════════════════════════════════════════════


def _download_and_prepare(ticker: str, period: str = "5y") -> pd.DataFrame | None:
    """yfinanceからダウンロードして前処理。失敗時はNone。"""
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 300:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(c[0]).capitalize() for c in df.columns]
        else:
            df.columns = [str(c).capitalize() for c in df.columns]
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
# 改善9: 3モデルスタッキング
# ═══════════════════════════════════════════════════════════════════


def train_stacked_ensemble(X_train, y_train, X_test, y_test,
                           sample_weight_train=None,
                           pos_weight=1.0, n_folds=5):
    """
    XGBoost + LightGBM + CatBoost → Logistic Regression メタラーナー。
    out-of-fold 予測でメタラーナーを学習。
    """
    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    # ── ベースモデル定義 ────────────────────────────
    xgb_params = dict(
        n_estimators=800, max_depth=7, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        scale_pos_weight=pos_weight,
        tree_method="hist", device="cuda",
        eval_metric="auc", early_stopping_rounds=40, random_state=42, verbosity=0,
    )
    lgbm_params = dict(
        n_estimators=800, max_depth=7, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7, reg_alpha=0.1, reg_lambda=1.0,
        scale_pos_weight=pos_weight,
        device="gpu", verbose=-1, random_state=42,
    )

    base_models = [
        ("xgb", XGBClassifier(**xgb_params)),
        ("lgbm", LGBMClassifier(**lgbm_params)),
    ]

    if HAS_CATBOOST:
        cat_params = dict(
            iterations=800, depth=7, learning_rate=0.03,
            l2_leaf_reg=3.0, task_type="GPU", verbose=0, random_seed=42,
            auto_class_weights="Balanced",
        )
        base_models.append(("catboost", CatBoostClassifier(**cat_params)))

    # ── Out-of-Fold 予測 ────────────────────────────
    n_train = len(X_train)
    oof_preds = {name: np.zeros(n_train) for name, _ in base_models}
    test_preds = {name: np.zeros(len(X_test)) for name, _ in base_models}

    fold_size = n_train // n_folds
    print(f"\n  スタッキング: {len(base_models)} ベースモデル x {n_folds} フォールド")

    for name, model_template in base_models:
        print(f"\n  --- {name} OOF学習 ---")
        for fold in range(n_folds):
            val_start = fold * fold_size
            val_end = min((fold + 1) * fold_size, n_train)
            val_idx = list(range(val_start, val_end))
            train_idx = list(range(0, val_start)) + list(range(val_end, n_train))

            X_tr = X_train.iloc[train_idx]
            y_tr = y_train.iloc[train_idx]
            X_val = X_train.iloc[val_idx]
            y_val = y_train.iloc[val_idx]
            w_tr = sample_weight_train[train_idx] if sample_weight_train is not None else None

            # モデルをクローン
            import copy
            model = copy.deepcopy(model_template)

            try:
                if name == "xgb":
                    model.fit(X_tr, y_tr, sample_weight=w_tr,
                              eval_set=[(X_val, y_val)], verbose=False)
                elif name == "lgbm":
                    try:
                        model.fit(X_tr, y_tr, sample_weight=w_tr,
                                  eval_set=[(X_val, y_val)])
                    except Exception:
                        model.set_params(device="cpu")
                        model.fit(X_tr, y_tr, sample_weight=w_tr,
                                  eval_set=[(X_val, y_val)])
                elif name == "catboost":
                    model.fit(X_tr, y_tr, sample_weight=w_tr,
                              eval_set=(X_val, y_val), early_stopping_rounds=40)
            except Exception as e:
                print(f"    fold {fold+1} 学習失敗: {e}")
                continue

            oof_preds[name][val_idx] = model.predict_proba(X_val)[:, 1]
            test_preds[name] += model.predict_proba(X_test)[:, 1] / n_folds

        auc = roc_auc_score(y_test, test_preds[name])
        print(f"  {name} テストAUC: {auc:.4f}")

    # ── メタラーナー（Logistic Regression）────────────
    meta_X_train = np.column_stack([oof_preds[name] for name, _ in base_models])
    meta_X_test = np.column_stack([test_preds[name] for name, _ in base_models])

    meta_model = LogisticRegression(C=1.0, random_state=42)
    meta_model.fit(meta_X_train, y_train)
    meta_prob = meta_model.predict_proba(meta_X_test)[:, 1]
    meta_auc = roc_auc_score(y_test, meta_prob)
    print(f"\n  メタラーナー（Logistic Regression）テストAUC: {meta_auc:.4f}")
    print(f"  メタラーナー係数: {dict(zip([n for n, _ in base_models], meta_model.coef_[0]))}")

    # 最終モデルを全データで再学習
    final_models = {}
    X_all = pd.concat([X_train, X_test], ignore_index=True)
    y_all = pd.concat([y_train, y_test], ignore_index=True)
    w_all = (np.concatenate([sample_weight_train, np.ones(len(X_test))])
             if sample_weight_train is not None else None)

    for name, model_template in base_models:
        print(f"  {name} 全データ再学習...")
        import copy
        model = copy.deepcopy(model_template)
        # early_stopping を無効化（全データ学習）
        if hasattr(model, "early_stopping_rounds"):
            model.set_params(early_stopping_rounds=None)
        try:
            if name == "catboost":
                model.set_params(early_stopping_rounds=None) if hasattr(model, "set_params") else None
                model.fit(X_all, y_all, sample_weight=w_all)
            elif name == "lgbm":
                try:
                    model.fit(X_all, y_all, sample_weight=w_all)
                except Exception:
                    model.set_params(device="cpu")
                    model.fit(X_all, y_all, sample_weight=w_all)
            else:
                model.fit(X_all, y_all, sample_weight=w_all)
            final_models[name] = model
        except Exception as e:
            print(f"  {name} 全データ学習失敗: {e}")

    return final_models, meta_model, meta_auc


# ═══════════════════════════════════════════════════════════════════
# モデル1: アンサンブル株価方向予測（v3: スタッキング + GA + NPMM + PurgedCV）
# ═══════════════════════════════════════════════════════════════════


def train_ensemble_direction_v3(tickers: list[str], market: pd.DataFrame,
                                ticker_to_sector: dict,
                                sector_medians: dict,
                                regime_df: pd.DataFrame):
    """v3 方向予測: NPMM + PurgedCV + GA特徴量選択 + サンプルウェイト + スタッキング。"""
    print("\n" + "=" * 60)
    print("モデル1: アンサンブル方向予測 v3")
    print(f"  改善: NPMM, PurgedCV, GA特徴量選択, サンプルウェイト, 3モデルスタッキング")
    print(f"  対象: {len(tickers)} 銘柄")
    print("=" * 60)

    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    from sklearn.metrics import classification_report, roc_auc_score

    all_X, all_y, all_dates = [], [], []
    processed = 0

    for ticker in tqdm(tickers, desc="データ取得+特徴量計算"):
        try:
            df = _download_and_prepare(ticker)
            if df is None:
                continue

            sector = ticker_to_sector.get(ticker, "不明")
            s_medians = sector_medians.get(sector)

            # ニュースセンチメント（改善8）
            ns = get_news_sentiment(ticker)

            feat = calc_features_v3(df, market, regime_df, s_medians, news_sentiment=ns)

            # 改善1: NPMM ラベリング
            feat["target"] = npmm_label(df["Close"], order=10, threshold=0.02, fallback_days=5)

            feat = feat.dropna(subset=["target"])
            feat = feat.dropna(thresh=int(len(feat.columns) * 0.7))
            if len(feat) < 100:
                continue

            all_X.append(feat.drop(columns=["target"]))
            all_y.append(feat["target"])
            all_dates.append(feat.index.to_series())
            processed += 1
        except Exception:
            continue

    if not all_X:
        print("データ不足。スキップ。")
        return

    X = pd.concat(all_X, ignore_index=True).fillna(0)
    y = pd.concat(all_y, ignore_index=True)
    dates = pd.concat(all_dates, ignore_index=True)
    X = X.replace([np.inf, -np.inf], 0)
    # 全カラムをfloat型に強制変換
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)
    feature_names_all = list(X.columns)
    print(f"学習データ: {len(X):,} サンプル, {X.shape[1]} 特徴量, {processed} 銘柄")
    print(f"正例率: {y.mean():.1%}")

    # 改善4: サンプルウェイト
    sample_weights = compute_sample_weights(
        pd.DatetimeIndex(dates), market=market
    )

    # ── 改善2: Purged Cross-Validation でAUC報告 ──
    print("\n--- Purged 5-Fold CV ---")
    pkf = PurgedKFold(n_splits=5, purge_gap=10, embargo_pct=0.02)
    cv_aucs = []
    for fold_i, (train_idx, test_idx) in enumerate(pkf.split(X)):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        w_tr = sample_weights[train_idx]
        pw = len(y_tr[y_tr == 0]) / max(len(y_tr[y_tr == 1]), 1)

        model_cv = XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            scale_pos_weight=pw,
            tree_method="hist", device="cuda",
            eval_metric="auc", early_stopping_rounds=20, random_state=42, verbosity=0,
        )
        model_cv.fit(X_tr, y_tr, sample_weight=w_tr,
                     eval_set=[(X_te, y_te)], verbose=False)
        prob = model_cv.predict_proba(X_te)[:, 1]
        auc = roc_auc_score(y_te, prob)
        cv_aucs.append(auc)
        print(f"  Fold {fold_i+1}: AUC = {auc:.4f}")

    print(f"  Purged CV 平均AUC: {np.mean(cv_aucs):.4f} (+/- {np.std(cv_aucs):.4f})")

    # ── 改善3: GA 特徴量選択 ──
    selected_features = ga_feature_selection(X, y, sample_weights)
    print(f"GA選択後の特徴量数: {len(selected_features)}")

    # GA選択特徴量でフィルタ
    X_selected = X[selected_features]

    # ── 最終訓練: 80/20 スプリット + スタッキング ──
    split = int(len(X_selected) * 0.8)
    X_train = X_selected.iloc[:split]
    X_test = X_selected.iloc[split:]
    y_train = y.iloc[:split]
    y_test = y.iloc[split:]
    w_train = sample_weights[:split]

    pos_weight = len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1)

    # 改善9: スタッキング
    final_models, meta_model, meta_auc = train_stacked_ensemble(
        X_train, y_train, X_test, y_test,
        sample_weight_train=w_train, pos_weight=pos_weight,
    )

    # 分類レポート
    xgb_model = final_models.get("xgb")
    lgbm_model = final_models.get("lgbm")

    if xgb_model:
        xgb_prob = xgb_model.predict_proba(X_test)[:, 1]
        print(f"\n最終 XGBoost AUC: {roc_auc_score(y_test, xgb_prob):.4f}")
    if lgbm_model:
        lgbm_prob = lgbm_model.predict_proba(X_test)[:, 1]
        print(f"最終 LightGBM AUC: {roc_auc_score(y_test, lgbm_prob):.4f}")

    # 特徴量重要度
    if xgb_model:
        importance = pd.Series(xgb_model.feature_importances_, index=selected_features).sort_values(ascending=False)
        print("\n特徴量重要度 TOP15:")
        print(importance.head(15))

    # 保存（v2互換: feature_names は全特徴量リストを保存、選択情報も含める）
    if xgb_model:
        with open(MODELS_DIR / "xgboost_direction.pkl", "wb") as f:
            pickle.dump({
                "model": xgb_model,
                "features": selected_features,
                "all_features": feature_names_all,
                "meta_model": meta_model,
                "ga_selected": selected_features,
            }, f)
    if lgbm_model:
        with open(MODELS_DIR / "lgbm_direction.pkl", "wb") as f:
            pickle.dump({
                "model": lgbm_model,
                "features": selected_features,
                "all_features": feature_names_all,
                "meta_model": meta_model,
            }, f)
    print(f"\n保存完了: xgboost_direction.pkl, lgbm_direction.pkl")

    return selected_features  # タイミングモデルで再利用


# ═══════════════════════════════════════════════════════════════════
# モデル2: LSTM 方向予測（v3: サンプルウェイト + 分数階差分 + レジーム）
# ═══════════════════════════════════════════════════════════════════


def train_lstm_direction_v3(tickers: list[str], market: pd.DataFrame,
                            ticker_to_sector: dict,
                            sector_medians: dict,
                            regime_df: pd.DataFrame):
    """v3 LSTM: 新特徴量を含むBidirectional LSTM + Attention。"""
    print("\n" + "=" * 60)
    print("モデル2: LSTM 方向予測 v3（分数階差分+レジーム特徴量追加）")
    print("=" * 60)

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    from sklearn.preprocessing import RobustScaler
    from sklearn.metrics import roc_auc_score
    import tempfile
    import gc

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"デバイス: {device}")

    SEQ_LEN = 30

    # ── Pass 1: スケーラーを学習 ─────────────────────
    print("Pass 1: スケーラー学習（サンプリング）...")
    sample_rows = []
    sample_tickers = tickers[::10]
    for ticker in tqdm(sample_tickers, desc="スケーラー学習"):
        try:
            df = _download_and_prepare(ticker)
            if df is None:
                continue
            sector = ticker_to_sector.get(ticker, "不明")
            s_medians = sector_medians.get(sector)
            feat = calc_features_v3(df, market, regime_df, s_medians).dropna()
            if len(feat) > 50:
                sample_rows.append(feat.iloc[::5].values)
        except Exception:
            continue

    if not sample_rows:
        print("サンプルデータ不足。LSTMスキップ。")
        return

    scaler = RobustScaler()
    sample_data = np.vstack(sample_rows)
    n_features = sample_data.shape[1]
    scaler.fit(np.nan_to_num(sample_data, nan=0, posinf=0, neginf=0))
    del sample_rows, sample_data
    gc.collect()
    print(f"  特徴量数: {n_features}")

    # ── Pass 2: シーケンス構築 ──────────────────────
    print("Pass 2: シーケンス構築...")
    tmp_dir = Path(tempfile.mkdtemp())
    total_seqs = 0
    chunk_id = 0
    CHUNK_SIZE = 50_000

    buf_X = np.zeros((CHUNK_SIZE, SEQ_LEN, n_features), dtype=np.float32)
    buf_y = np.zeros(CHUNK_SIZE, dtype=np.float32)
    buf_w = np.zeros(CHUNK_SIZE, dtype=np.float32)  # サンプルウェイト
    buf_idx = 0

    def _flush_buffer():
        nonlocal buf_idx, chunk_id, total_seqs
        if buf_idx == 0:
            return
        np.save(tmp_dir / f"X_{chunk_id}.npy", buf_X[:buf_idx])
        np.save(tmp_dir / f"y_{chunk_id}.npy", buf_y[:buf_idx])
        np.save(tmp_dir / f"w_{chunk_id}.npy", buf_w[:buf_idx])
        total_seqs += buf_idx
        chunk_id += 1
        buf_idx = 0

    for ticker in tqdm(tickers, desc="シーケンス構築"):
        try:
            df = _download_and_prepare(ticker)
            if df is None:
                continue

            sector = ticker_to_sector.get(ticker, "不明")
            s_medians = sector_medians.get(sector)
            feat = calc_features_v3(df, market, regime_df, s_medians)

            # NPMM ラベリング
            target = npmm_label(df["Close"], order=10, threshold=0.02, fallback_days=5)
            feat["target"] = target
            feat = feat.dropna()
            if len(feat) < SEQ_LEN + 10:
                continue

            # サンプルウェイト
            weights = compute_sample_weights(feat.index, market=market)

            values = feat.drop(columns=["target"]).values
            values = np.nan_to_num(scaler.transform(np.nan_to_num(values, nan=0, posinf=0, neginf=0)),
                                   nan=0, posinf=0, neginf=0).astype(np.float32)
            labels = feat["target"].values

            for i in range(SEQ_LEN, len(values) - 5):
                buf_X[buf_idx] = values[i - SEQ_LEN:i]
                buf_y[buf_idx] = labels[i]
                buf_w[buf_idx] = weights[i]
                buf_idx += 1
                if buf_idx >= CHUNK_SIZE:
                    _flush_buffer()
        except Exception:
            continue

    _flush_buffer()
    del buf_X, buf_y, buf_w
    gc.collect()

    if total_seqs == 0:
        print("シーケンスデータなし。LSTMスキップ。")
        return

    print(f"データ: {total_seqs:,} シーケンス, {chunk_id} チャンク")

    # ── Pass 3: 学習 ────────────────────────────────
    split_chunk = max(int(chunk_id * 0.8), 1)

    test_Xs, test_ys = [], []
    for i in range(split_chunk, chunk_id):
        test_Xs.append(np.load(tmp_dir / f"X_{i}.npy"))
        test_ys.append(np.load(tmp_dir / f"y_{i}.npy"))
    if not test_Xs:
        print("テストデータなし。LSTMスキップ。")
        return
    X_test_np = np.concatenate(test_Xs); del test_Xs
    y_test_np = np.concatenate(test_ys); del test_ys; gc.collect()
    test_ds = TensorDataset(torch.tensor(X_test_np), torch.tensor(y_test_np))
    test_dl = DataLoader(test_ds, batch_size=1024)
    print(f"テスト: {len(X_test_np):,}")
    del X_test_np; gc.collect()

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
            weights = torch.softmax(self.attn(out), dim=1)
            context = (out * weights).sum(dim=1)
            return self.head(context).squeeze(-1)

    model = BiLSTMAttention(n_features).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)

    _test_y_np = np.concatenate([np.load(tmp_dir / f"y_{i}.npy") for i in range(split_chunk, chunk_id)])
    _pw = (_test_y_np == 0).sum() / max((_test_y_np == 1).sum(), 1)
    del _test_y_np
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([_pw]).to(device), reduction='none')

    best_auc = 0
    for epoch in range(40):
        model.train()
        losses = []
        random.shuffle(train_chunk_ids)
        for cid in train_chunk_ids:
            _cx = torch.tensor(np.load(tmp_dir / f"X_{cid}.npy"))
            _cy = torch.tensor(np.load(tmp_dir / f"y_{cid}.npy"))
            _cw = torch.tensor(np.load(tmp_dir / f"w_{cid}.npy"))
            _cdl = DataLoader(TensorDataset(_cx, _cy, _cw), batch_size=512, shuffle=True)
            for xb, yb, wb in _cdl:
                xb, yb, wb = xb.to(device), yb.to(device), wb.to(device)
                pred = model(xb)
                loss_per_sample = criterion(pred, yb)
                # サンプルウェイト適用
                loss = (loss_per_sample * wb).mean()
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                losses.append(loss.item())
            del _cx, _cy, _cw, _cdl
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

    # 一時ファイルクリーンアップ
    import shutil
    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# モデル3: 決算サプライズ予測（v3: サンプルウェイト + 新特徴量）
# ═══════════════════════════════════════════════════════════════════


def train_earnings_surprise_v3(tickers: list[str], market: pd.DataFrame,
                               ticker_to_sector: dict,
                               sector_medians: dict,
                               regime_df: pd.DataFrame):
    """v3 決算サプライズ: サンプルウェイト + レジーム + セクター相対。"""
    print("\n" + "=" * 60)
    print("モデル3: 決算サプライズ予測 v3")
    print("=" * 60)

    from xgboost import XGBClassifier
    from sklearn.metrics import classification_report, roc_auc_score

    all_X, all_y, all_dates = [], [], []
    feature_names = None

    for ticker in tqdm(tickers, desc="決算データ収集"):
        try:
            t = yf.Ticker(ticker)
            earn_df = t.get_earnings_dates(limit=20)
            if earn_df is None or earn_df.empty:
                continue
            if earn_df.index.tz is not None:
                earn_df.index = earn_df.index.tz_localize(None)

            df = _download_and_prepare(ticker)
            if df is None or len(df) < 100:
                continue

            sector = ticker_to_sector.get(ticker, "不明")
            s_medians = sector_medians.get(sector)
            feat = calc_features_v3(df, market, regime_df, s_medians)
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
                all_dates.append(dt)
        except Exception:
            continue

    if len(all_X) < 50:
        print("決算データ不足。スキップ。")
        return

    X = pd.DataFrame(all_X, columns=feature_names).fillna(0).replace([np.inf, -np.inf], 0)
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)
    y = np.array(all_y)
    dates_arr = pd.DatetimeIndex(all_dates)
    print(f"データ: {len(X):,} 件, 正例率: {y.mean():.1%}")

    # サンプルウェイト
    sample_weights = compute_sample_weights(dates_arr, market=market)

    # Purged CV でAUC報告
    print("\n--- Purged 5-Fold CV ---")
    pkf = PurgedKFold(n_splits=5, purge_gap=5, embargo_pct=0.02)
    cv_aucs = []
    for fold_i, (train_idx, test_idx) in enumerate(pkf.split(X)):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]
        w_tr = sample_weights[train_idx]
        try:
            m = XGBClassifier(
                n_estimators=300, max_depth=6, learning_rate=0.05,
                tree_method="hist", device="cuda",
                eval_metric="auc", early_stopping_rounds=20, random_state=42, verbosity=0,
            )
            m.fit(X_tr, y_tr, sample_weight=w_tr, eval_set=[(X_te, y_te)], verbose=False)
            prob = m.predict_proba(X_te)[:, 1]
            auc = roc_auc_score(y_te, prob)
            cv_aucs.append(auc)
            print(f"  Fold {fold_i+1}: AUC = {auc:.4f}")
        except Exception:
            continue
    if cv_aucs:
        print(f"  Purged CV 平均AUC: {np.mean(cv_aucs):.4f} (+/- {np.std(cv_aucs):.4f})")

    # 全データで最終学習
    model = XGBClassifier(
        n_estimators=500, max_depth=6, learning_rate=0.03,
        tree_method="hist", device="cuda",
        eval_metric="auc", random_state=42, verbosity=0,
    )
    split = int(len(X) * 0.8)
    model.fit(X.iloc[:split], y[:split], sample_weight=sample_weights[:split],
              eval_set=[(X.iloc[split:], y[split:])],
              verbose=50)
    y_prob = model.predict_proba(X.iloc[split:])[:, 1]
    test_auc = roc_auc_score(y[split:], y_prob)
    print(f"テストAUC: {test_auc:.4f}")

    with open(MODELS_DIR / "xgboost_earnings.pkl", "wb") as f:
        pickle.dump({"model": model, "features": feature_names}, f)
    print("保存完了: xgboost_earnings.pkl")


# ═══════════════════════════════════════════════════════════════════
# モデル4: 最適売買タイミング（v3: GA特徴量再利用 + スタッキング）
# ═══════════════════════════════════════════════════════════════════


def train_optimal_timing_v3(tickers: list[str], market: pd.DataFrame,
                            ticker_to_sector: dict,
                            sector_medians: dict,
                            regime_df: pd.DataFrame,
                            ga_selected_features: list[str] | None = None):
    """v3 タイミング: NPMM + サンプルウェイト + セクター相対 + スタッキング。"""
    print("\n" + "=" * 60)
    print("モデル4: 最適売買タイミング v3")
    print("=" * 60)

    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    from sklearn.metrics import classification_report, roc_auc_score

    all_X, all_y, all_dates = [], [], []
    processed = 0

    for ticker in tqdm(tickers, desc="マルチソースデータ"):
        try:
            df = _download_and_prepare(ticker)
            if df is None:
                continue

            sector = ticker_to_sector.get(ticker, "不明")
            s_medians = sector_medians.get(sector)

            # ニュースセンチメント
            ns = get_news_sentiment(ticker)

            feat = calc_features_v3(df, market, regime_df, s_medians, news_sentiment=ns)

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

            # NPMM ラベリング（タイミングは10日後、閾値3%）
            feat["target"] = npmm_label(df["Close"], order=10, threshold=0.03, fallback_days=10)
            feat = feat.dropna(subset=["target"])
            feat = feat.dropna(thresh=int(len(feat.columns) * 0.6))
            if len(feat) < 100:
                continue

            all_X.append(feat.drop(columns=["target"]))
            all_y.append(feat["target"])
            all_dates.append(feat.index.to_series())
            processed += 1
        except Exception:
            continue

    if not all_X:
        print("データ不足。スキップ。")
        return

    X = pd.concat(all_X, ignore_index=True).fillna(0).replace([np.inf, -np.inf], 0)
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)
    y = pd.concat(all_y, ignore_index=True)
    dates = pd.concat(all_dates, ignore_index=True)
    features = list(X.columns)
    print(f"データ: {len(X):,} サンプル, {X.shape[1]} 特徴量, {processed} 銘柄")
    print(f"正例率: {y.mean():.1%}")

    # サンプルウェイト
    sample_weights = compute_sample_weights(pd.DatetimeIndex(dates), market=market)

    # GA特徴量を再利用（方向モデルから）: 存在する特徴量のみ
    if ga_selected_features:
        available = [f for f in ga_selected_features if f in X.columns]
        # タイミング固有の特徴量も追加
        timing_specific = [f for f in features if f.startswith("fund_") or f == "news_sentiment"]
        selected = list(set(available + timing_specific))
        if len(selected) >= 20:
            X = X[selected]
            features = selected
            print(f"GA選択特徴量を再利用: {len(features)} 特徴量")

    # Purged CV
    print("\n--- Purged 5-Fold CV ---")
    pkf = PurgedKFold(n_splits=5, purge_gap=10, embargo_pct=0.02)
    cv_aucs = []
    for fold_i, (train_idx, test_idx) in enumerate(pkf.split(X)):
        try:
            X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
            y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
            w_tr = sample_weights[train_idx]
            pw = len(y_tr[y_tr == 0]) / max(len(y_tr[y_tr == 1]), 1)
            m = XGBClassifier(
                n_estimators=300, max_depth=6, learning_rate=0.05,
                scale_pos_weight=pw,
                tree_method="hist", device="cuda",
                eval_metric="auc", early_stopping_rounds=20, random_state=42, verbosity=0,
            )
            m.fit(X_tr, y_tr, sample_weight=w_tr, eval_set=[(X_te, y_te)], verbose=False)
            prob = m.predict_proba(X_te)[:, 1]
            auc = roc_auc_score(y_te, prob)
            cv_aucs.append(auc)
            print(f"  Fold {fold_i+1}: AUC = {auc:.4f}")
        except Exception:
            continue
    if cv_aucs:
        print(f"  Purged CV 平均AUC: {np.mean(cv_aucs):.4f} (+/- {np.std(cv_aucs):.4f})")

    # スタッキング
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    w_train = sample_weights[:split]
    pos_weight = len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1)

    final_models, meta_model, meta_auc = train_stacked_ensemble(
        X_train, y_train, X_test, y_test,
        sample_weight_train=w_train, pos_weight=pos_weight,
    )

    # XGBoostモデルを保存（タイミング用）
    xgb_model = final_models.get("xgb")
    if xgb_model:
        importance = pd.Series(xgb_model.feature_importances_, index=features).sort_values(ascending=False)
        print("\n特徴量重要度 TOP15:")
        print(importance.head(15))

        with open(MODELS_DIR / "xgboost_timing.pkl", "wb") as f:
            pickle.dump({
                "model": xgb_model,
                "features": features,
                "meta_model": meta_model,
            }, f)
        print("保存完了: xgboost_timing.pkl")


# ═══════════════════════════════════════════════════════════════════
# メイン
# ═══════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    start_time = time.time()
    print("[START] 改善版MLモデル学習 v3")
    print(f"保存先: {MODELS_DIR}")
    print(f"改善点: NPMM, PurgedCV, GA特徴量選択, サンプルウェイト, 分数階差分, "
          f"レジーム検出, セクター相対, ニュースセンチメント, 3モデルスタッキング")

    try:
        import torch
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            print("[INFO] CUDA利用不可。CPUで実行。")
    except ImportError:
        print("[WARN] PyTorch未インストール")

    # 銘柄取得（セクター情報付き）
    tickers, ticker_to_sector = load_all_tse_tickers()
    print(f"対象銘柄: {len(tickers)}")

    # マーケット全体指標
    market = fetch_market_data("5y")

    # レジーム検出（改善6）
    hmm_model = fit_regime_model(market)
    regime_df = predict_regime(market, hmm_model)
    print(f"レジーム特徴量: {len(regime_df.columns)} カラム")

    # セクター中央値事前計算（改善7）
    # 計算コストが高いのでサンプリング: 各セクターから最大30銘柄
    sector_medians = {}
    if ticker_to_sector:
        sector_medians = precompute_sector_medians(tickers, ticker_to_sector, market)

    # ── 1. アンサンブル方向予測 ──
    ga_selected = train_ensemble_direction_v3(
        tickers, market, ticker_to_sector, sector_medians, regime_df
    )

    # ── 2. LSTM方向予測 ──
    try:
        import torch
        train_lstm_direction_v3(
            tickers, market, ticker_to_sector, sector_medians, regime_df
        )
    except ImportError:
        print("[WARN] PyTorch未インストール。LSTMスキップ。")

    # ── 3. 決算サプライズ ──
    train_earnings_surprise_v3(
        tickers, market, ticker_to_sector, sector_medians, regime_df
    )

    # ── 4. 最適タイミング ──
    train_optimal_timing_v3(
        tickers, market, ticker_to_sector, sector_medians, regime_df,
        ga_selected_features=ga_selected,
    )

    elapsed = time.time() - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)

    print("\n" + "=" * 60)
    print(f"[DONE] 全モデル学習完了! (v3) - 所要時間: {hours}h {minutes}m")
    for f in sorted(MODELS_DIR.glob("*")):
        if f.is_file() and not f.name.startswith("."):
            print(f"  {f.name} ({f.stat().st_size / 1e6:.1f} MB)")
