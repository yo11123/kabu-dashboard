"""
決算サプライズ予測モデル v3 — 専用学習スクリプト

data/earnings_combined.csv を読み込み、決算前の株価特徴量 + 決算固有特徴量で
「決算後5日間で3%以上上昇するか」を予測するモデルを学習する。

改善点 (v2 → v3):
  - 複数ソース統合データ（IRBank + yfinance + Kabutan）
  - 決算固有特徴量（サプライズ%, YoY利益成長, 過去ビート実績 etc.）
  - XGBoost + LightGBM スタッキング
  - Purged Cross-Validation
  - 目標: 5,000+ イベント, AUC > 0.65

使い方:
    python train/train_earnings_v3.py
"""
import os
import sys
import copy
import warnings
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd
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

# train_all_v3 からユーティリティをインポート
sys.path.insert(0, str(ROOT / "train"))
try:
    from train_all_v3 import (
        calc_features_v3,
        PurgedKFold,
        compute_sample_weights,
        fetch_market_data,
        frac_diff,
        _download_and_prepare,
    )
    print("train_all_v3 からインポート成功")
except ImportError as e:
    print(f"train_all_v3 インポート失敗: {e}")
    print("train_all_v3.py が train/ ディレクトリに存在するか確認してください。")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# 決算データ読み込み
# ═══════════════════════════════════════════════════════════════════


def load_earnings_data() -> pd.DataFrame:
    """data/earnings_combined.csv を読み込む。なければ収集スクリプトを案内。"""
    path = DATA_DIR / "earnings_combined.csv"
    if not path.exists():
        print(f"エラー: {path} が見つかりません。")
        print("先に python train/collect_earnings_data.py を実行してください。")
        sys.exit(1)

    df = pd.read_csv(path, parse_dates=["earnings_date"], dtype={"code": str})
    print(f"決算データ読み込み: {len(df):,} 行, {df['code'].nunique()} 社")

    # 基本フィルタリング
    df = df.dropna(subset=["earnings_date"])
    df = df[df["earnings_date"] < pd.Timestamp.now()]  # 未来の日付を除外
    df = df[df["earnings_date"] > pd.Timestamp("2018-01-01")]  # 古すぎるデータを除外

    # コードの正規化
    df["code"] = df["code"].astype(str).str.strip().str.zfill(4)
    df["ticker"] = df["code"] + ".T"

    print(f"フィルタ後: {len(df):,} 行, 日付範囲: {df['earnings_date'].min():%Y-%m-%d} ～ {df['earnings_date'].max():%Y-%m-%d}")
    return df


# ═══════════════════════════════════════════════════════════════════
# 株価データ取得（決算日周辺）
# ═══════════════════════════════════════════════════════════════════


def fetch_price_around_earnings(ticker: str, earnings_date: pd.Timestamp,
                                 days_before: int = 80, days_after: int = 10) -> pd.DataFrame | None:
    """決算日の前後の株価データを取得する。"""
    try:
        start = earnings_date - pd.Timedelta(days=days_before + 30)  # バッファ
        end = earnings_date + pd.Timedelta(days=days_after + 5)

        df = yf.download(
            ticker, start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d", progress=False, auto_adjust=True,
        )
        if df is None or df.empty or len(df) < 60:
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
# 決算固有特徴量の計算
# ═══════════════════════════════════════════════════════════════════


def calc_earnings_specific_features(
    earnings_row: pd.Series,
    price_df: pd.DataFrame,
    earnings_date: pd.Timestamp,
    historical_surprises: list[float],
    sector_beat_rate: float | None = None,
) -> dict:
    """決算イベントに固有の特徴量を計算する。"""
    feat = {}

    # ── EPS サプライズ % ──
    surprise = earnings_row.get("surprise_pct")
    if pd.notna(surprise):
        feat["eps_surprise_pct"] = float(surprise)
    else:
        reported = earnings_row.get("reported_eps")
        estimate = earnings_row.get("eps_estimate")
        if pd.notna(reported) and pd.notna(estimate) and estimate != 0:
            feat["eps_surprise_pct"] = ((reported - estimate) / abs(estimate)) * 100
        else:
            feat["eps_surprise_pct"] = 0.0

    # ── YoY 利益成長 ──
    for col in ["sales_yoy", "operating_profit_yoy", "net_profit_yoy", "eps_yoy"]:
        val = earnings_row.get(col)
        feat[col] = float(val) if pd.notna(val) else 0.0

    # ── 決算前モメンタム（20日リターン）──
    close = price_df["Close"]
    pre_mask = price_df.index < earnings_date
    pre_prices = close[pre_mask]
    if len(pre_prices) >= 20:
        feat["pre_earn_momentum_20d"] = (pre_prices.iloc[-1] / pre_prices.iloc[-20] - 1) * 100
    else:
        feat["pre_earn_momentum_20d"] = 0.0

    # ── 決算前5日モメンタム ──
    if len(pre_prices) >= 5:
        feat["pre_earn_momentum_5d"] = (pre_prices.iloc[-1] / pre_prices.iloc[-5] - 1) * 100
    else:
        feat["pre_earn_momentum_5d"] = 0.0

    # ── 決算前RSI（14日）──
    if len(pre_prices) >= 15:
        delta = pre_prices.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
        last_rsi = rsi.dropna()
        feat["pre_earn_rsi_14"] = float(last_rsi.iloc[-1]) if not last_rsi.empty else 50.0
    else:
        feat["pre_earn_rsi_14"] = 50.0

    # ── 決算前ボリュームスパイク ──
    if "Volume" in price_df.columns:
        vol = price_df["Volume"][pre_mask]
        if len(vol) >= 20:
            vol_ma20 = vol.rolling(20).mean()
            last_vol_ratio = vol.iloc[-1] / vol_ma20.iloc[-1] if vol_ma20.iloc[-1] > 0 else 1.0
            feat["pre_earn_volume_spike"] = float(last_vol_ratio)
            # 直近5日の平均出来高比率
            feat["pre_earn_vol_5d_ratio"] = float(vol.iloc[-5:].mean() / vol_ma20.iloc[-1]) if vol_ma20.iloc[-1] > 0 else 1.0
        else:
            feat["pre_earn_volume_spike"] = 1.0
            feat["pre_earn_vol_5d_ratio"] = 1.0
    else:
        feat["pre_earn_volume_spike"] = 1.0
        feat["pre_earn_vol_5d_ratio"] = 1.0

    # ── 決算前ボラティリティ ──
    if len(pre_prices) >= 20:
        ret = pre_prices.pct_change().dropna()
        feat["pre_earn_volatility_20d"] = float(ret.tail(20).std() * np.sqrt(252) * 100)
        feat["pre_earn_volatility_5d"] = float(ret.tail(5).std() * np.sqrt(252) * 100) if len(ret) >= 5 else feat["pre_earn_volatility_20d"]
    else:
        feat["pre_earn_volatility_20d"] = 30.0
        feat["pre_earn_volatility_5d"] = 30.0

    # ── 過去のサプライズ実績（ビート率）──
    if historical_surprises:
        beat_count = sum(1 for s in historical_surprises if s > 0)
        feat["historical_beat_rate"] = beat_count / len(historical_surprises)
        feat["historical_beat_count"] = len(historical_surprises)
        feat["historical_avg_surprise"] = float(np.mean(historical_surprises))
        feat["historical_surprise_std"] = float(np.std(historical_surprises)) if len(historical_surprises) > 1 else 0.0
        # 直近のサプライズ（最新2件）
        recent = historical_surprises[-2:] if len(historical_surprises) >= 2 else historical_surprises
        feat["recent_avg_surprise"] = float(np.mean(recent))
    else:
        feat["historical_beat_rate"] = 0.5
        feat["historical_beat_count"] = 0
        feat["historical_avg_surprise"] = 0.0
        feat["historical_surprise_std"] = 0.0
        feat["recent_avg_surprise"] = 0.0

    # ── セクター決算トレンド（同セクターのビート率）──
    feat["sector_beat_rate"] = float(sector_beat_rate) if sector_beat_rate is not None else 0.5

    # ── 決算前の52週高安からの位置 ──
    if len(pre_prices) >= 252:
        h52 = pre_prices.rolling(252).max().iloc[-1]
        l52 = pre_prices.rolling(252).min().iloc[-1]
        rng = h52 - l52
        feat["pre_earn_52w_pos"] = (pre_prices.iloc[-1] - l52) / rng * 100 if rng > 0 else 50.0
    elif len(pre_prices) >= 20:
        h = pre_prices.max()
        l = pre_prices.min()
        rng = h - l
        feat["pre_earn_52w_pos"] = (pre_prices.iloc[-1] - l) / rng * 100 if rng > 0 else 50.0
    else:
        feat["pre_earn_52w_pos"] = 50.0

    # ── ボリンジャーバンド位置 ──
    if len(pre_prices) >= 20:
        bb_mid = pre_prices.rolling(20).mean().iloc[-1]
        bb_std = pre_prices.rolling(20).std().iloc[-1]
        feat["pre_earn_bb_pos"] = (pre_prices.iloc[-1] - bb_mid) / bb_std if bb_std > 0 else 0.0
    else:
        feat["pre_earn_bb_pos"] = 0.0

    return feat


# ═══════════════════════════════════════════════════════════════════
# ターゲットラベルの計算
# ═══════════════════════════════════════════════════════════════════


def calc_post_earnings_return(price_df: pd.DataFrame, earnings_date: pd.Timestamp,
                                hold_days: int = 5, threshold: float = 0.03) -> int | None:
    """決算後hold_days日間のリターンがthreshold以上なら1、そうでなければ0。"""
    post_mask = price_df.index >= earnings_date
    post_prices = price_df["Close"][post_mask]

    if len(post_prices) < hold_days + 1:
        return None

    # 決算当日の終値 vs hold_days日後の終値
    entry_price = post_prices.iloc[0]
    exit_price = post_prices.iloc[min(hold_days, len(post_prices) - 1)]
    ret = (exit_price / entry_price) - 1

    return 1 if ret > threshold else 0


# ═══════════════════════════════════════════════════════════════════
# セクターベース情報の計算
# ═══════════════════════════════════════════════════════════════════


def compute_sector_beat_rates(earnings_df: pd.DataFrame) -> dict:
    """
    セクターごとの直近ビート率を計算する。
    yfinance のセクター情報を使い、同セクター内の直近決算でのビート率を返す。
    """
    # セクターは ticker → sector のマッピングが必要
    # ここでは簡易的にコードの上2桁（業種コード的な分類）で代用
    sector_surprises = {}  # sector_key -> [surprise_pct, ...]

    for _, row in earnings_df.iterrows():
        code = str(row.get("code", ""))
        surprise = row.get("surprise_pct")
        if not code or pd.isna(surprise):
            continue
        # コード上2桁で業種を近似
        sector_key = code[:2]
        if sector_key not in sector_surprises:
            sector_surprises[sector_key] = []
        sector_surprises[sector_key].append(float(surprise))

    # 各セクターの直近ビート率
    sector_beat_rates = {}
    for key, surprises in sector_surprises.items():
        if surprises:
            beat_count = sum(1 for s in surprises if s > 0)
            sector_beat_rates[key] = beat_count / len(surprises)

    return sector_beat_rates


# ═══════════════════════════════════════════════════════════════════
# メイン学習パイプライン
# ═══════════════════════════════════════════════════════════════════


def main():
    start_time = time.time()

    print("=" * 60)
    print("決算サプライズ予測モデル v3 — 学習スクリプト")
    print("=" * 60)

    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, roc_auc_score

    # ── 1. 決算データ読み込み ──
    earnings_df = load_earnings_data()

    # ── 2. マーケット指標取得 ──
    print("\nマーケット指標を取得中...")
    market = fetch_market_data(period="10y")

    # ── 3. セクタービート率の事前計算 ──
    print("\nセクタービート率を計算中...")
    sector_beat_rates = compute_sector_beat_rates(earnings_df)
    print(f"  {len(sector_beat_rates)} セクターのビート率計算完了")

    # ── 4. 銘柄ごとに過去サプライズ実績を整理 ──
    print("\n銘柄別の過去サプライズ実績を整理中...")
    # code → [(date, surprise_pct), ...] のソート済みリスト
    historical_by_code = {}
    for _, row in earnings_df.sort_values("earnings_date").iterrows():
        code = row["code"]
        surprise = row.get("surprise_pct")
        if pd.notna(surprise):
            if code not in historical_by_code:
                historical_by_code[code] = []
            historical_by_code[code].append((row["earnings_date"], float(surprise)))

    # ── 5. 決算イベントごとにデータ構築 ──
    print("\n決算イベントの特徴量計算開始...")

    # ユニーク銘柄 × 決算日のペアを作成
    events = earnings_df[["code", "ticker", "earnings_date"]].drop_duplicates(
        subset=["code", "earnings_date"]
    ).sort_values("earnings_date")

    # 株価データキャッシュ（同一銘柄の複数決算を効率化）
    price_cache = {}

    all_features = []
    all_targets = []
    all_dates = []
    all_event_info = []
    skipped_no_price = 0
    skipped_no_target = 0
    skipped_too_few = 0

    # 各銘柄の全株価データをまとめて取得（効率化）
    unique_tickers = events["ticker"].unique()
    print(f"  ユニーク銘柄: {len(unique_tickers)}")

    # 株価データを事前取得
    print("\n株価データを事前取得中...")
    for ticker in tqdm(unique_tickers, desc="株価取得"):
        if ticker in price_cache:
            continue
        try:
            df = yf.download(
                ticker, period="10y", interval="1d",
                progress=False, auto_adjust=True,
            )
            if df is not None and not df.empty and len(df) >= 60:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [str(c[0]).capitalize() for c in df.columns]
                else:
                    df.columns = [str(c).capitalize() for c in df.columns]
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                price_cache[ticker] = df
        except Exception:
            continue

    print(f"  株価取得成功: {len(price_cache)} 銘柄")

    # 決算イベントのイテレーション
    print("\n特徴量計算中...")
    for _, event in tqdm(events.iterrows(), total=len(events), desc="特徴量計算"):
        code = event["code"]
        ticker = event["ticker"]
        earn_date = event["earnings_date"]

        # 株価データ取得
        price_df = price_cache.get(ticker)
        if price_df is None:
            skipped_no_price += 1
            continue

        # ターゲット: 決算後5日間で3%以上上昇したか
        target = calc_post_earnings_return(price_df, earn_date, hold_days=5, threshold=0.03)
        if target is None:
            skipped_no_target += 1
            continue

        # 決算前の株価データで特徴量計算
        pre_mask = price_df.index < earn_date
        pre_df = price_df[pre_mask]
        if len(pre_df) < 60:
            skipped_too_few += 1
            continue

        # v3 テクニカル特徴量（calc_features_v3 を使用）
        try:
            tech_feat = calc_features_v3(pre_df, market=market)
            if tech_feat.empty:
                continue
            # 決算前日の特徴量を取得
            last_feat = tech_feat.iloc[-1]
            if last_feat.isna().sum() > len(last_feat) * 0.5:
                continue
        except Exception:
            continue

        # 決算固有特徴量
        # 過去サプライズ実績（この決算日より前のもの）
        hist = historical_by_code.get(code, [])
        past_surprises = [s for d, s in hist if d < earn_date]

        # セクタービート率
        sector_key = code[:2]
        s_beat_rate = sector_beat_rates.get(sector_key, 0.5)

        # 該当決算行の取得
        earn_row = earnings_df[
            (earnings_df["code"] == code) &
            (earnings_df["earnings_date"] == earn_date)
        ]
        if earn_row.empty:
            continue
        earn_row = earn_row.iloc[0]

        earn_feat = calc_earnings_specific_features(
            earn_row, price_df, earn_date,
            historical_surprises=past_surprises,
            sector_beat_rate=s_beat_rate,
        )

        # テクニカル特徴量と決算固有特徴量を結合
        combined_feat = last_feat.to_dict()
        combined_feat.update(earn_feat)

        all_features.append(combined_feat)
        all_targets.append(target)
        all_dates.append(earn_date)
        all_event_info.append({
            "code": code, "ticker": ticker,
            "earnings_date": earn_date, "target": target,
        })

    print(f"\n  処理結果:")
    print(f"    有効イベント: {len(all_features):,}")
    print(f"    株価なしスキップ: {skipped_no_price:,}")
    print(f"    ターゲット計算不可: {skipped_no_target:,}")
    print(f"    データ不足: {skipped_too_few:,}")

    if len(all_features) < 100:
        print("\nエラー: 学習データが少なすぎます（100件未満）。")
        print("collect_earnings_data.py でより多くのデータを収集してください。")
        return

    # ── 6. DataFrame構築 ──
    X = pd.DataFrame(all_features).fillna(0).replace([np.inf, -np.inf], 0)
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)
    y = pd.Series(all_targets, dtype=float)
    dates = pd.DatetimeIndex(all_dates)
    feature_names = list(X.columns)

    print(f"\n学習データ:")
    print(f"  サンプル数: {len(X):,}")
    print(f"  特徴量数: {X.shape[1]}")
    print(f"  正例率（3%以上上昇）: {y.mean():.1%}")
    print(f"  日付範囲: {dates.min():%Y-%m-%d} ～ {dates.max():%Y-%m-%d}")

    # ── 7. サンプルウェイト ──
    sample_weights = compute_sample_weights(dates, market=market)

    # ── 8. Purged Cross-Validation ──
    print("\n" + "=" * 60)
    print("Purged 5-Fold Cross-Validation")
    print("=" * 60)

    pkf = PurgedKFold(n_splits=5, purge_gap=10, embargo_pct=0.02)
    cv_aucs_xgb = []
    cv_aucs_lgbm = []

    pos_weight = len(y[y == 0]) / max(len(y[y == 1]), 1)
    print(f"  クラス比率（neg/pos）: {pos_weight:.2f}")

    for fold_i, (train_idx, test_idx) in enumerate(pkf.split(X)):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        w_tr = sample_weights[train_idx]

        # XGBoost
        try:
            xgb_cv = XGBClassifier(
                n_estimators=500, max_depth=7, learning_rate=0.03,
                subsample=0.8, colsample_bytree=0.7,
                reg_alpha=0.1, reg_lambda=1.0,
                scale_pos_weight=pos_weight,
                tree_method="hist", device="cuda",
                eval_metric="auc", early_stopping_rounds=30,
                random_state=42, verbosity=0,
            )
            xgb_cv.fit(X_tr, y_tr, sample_weight=w_tr,
                       eval_set=[(X_te, y_te)], verbose=False)
            xgb_prob = xgb_cv.predict_proba(X_te)[:, 1]
            xgb_auc = roc_auc_score(y_te, xgb_prob)
            cv_aucs_xgb.append(xgb_auc)
        except Exception as e:
            print(f"  XGBoost Fold {fold_i+1} 失敗: {e}")
            xgb_auc = 0

        # LightGBM
        try:
            lgbm_cv = LGBMClassifier(
                n_estimators=500, max_depth=7, learning_rate=0.03,
                subsample=0.8, colsample_bytree=0.7,
                reg_alpha=0.1, reg_lambda=1.0,
                scale_pos_weight=pos_weight,
                device="gpu", verbose=-1, random_state=42,
            )
            try:
                lgbm_cv.fit(X_tr, y_tr, sample_weight=w_tr,
                            eval_set=[(X_te, y_te)])
            except Exception:
                lgbm_cv.set_params(device="cpu")
                lgbm_cv.fit(X_tr, y_tr, sample_weight=w_tr,
                            eval_set=[(X_te, y_te)])
            lgbm_prob = lgbm_cv.predict_proba(X_te)[:, 1]
            lgbm_auc = roc_auc_score(y_te, lgbm_prob)
            cv_aucs_lgbm.append(lgbm_auc)
        except Exception as e:
            print(f"  LightGBM Fold {fold_i+1} 失敗: {e}")
            lgbm_auc = 0

        print(f"  Fold {fold_i+1}: XGBoost AUC={xgb_auc:.4f}, LightGBM AUC={lgbm_auc:.4f}")

    if cv_aucs_xgb:
        print(f"\n  XGBoost Purged CV: {np.mean(cv_aucs_xgb):.4f} (+/- {np.std(cv_aucs_xgb):.4f})")
    if cv_aucs_lgbm:
        print(f"  LightGBM Purged CV: {np.mean(cv_aucs_lgbm):.4f} (+/- {np.std(cv_aucs_lgbm):.4f})")

    # ── 9. スタッキング学習 ──
    print("\n" + "=" * 60)
    print("XGBoost + LightGBM スタッキング")
    print("=" * 60)

    # 時系列分割 80/20
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    w_train = sample_weights[:split]
    dates_train = dates[:split]
    dates_test = dates[split:]

    print(f"  訓練: {len(X_train):,} サンプル ({dates_train.min():%Y-%m-%d} ～ {dates_train.max():%Y-%m-%d})")
    print(f"  テスト: {len(X_test):,} サンプル ({dates_test.min():%Y-%m-%d} ～ {dates_test.max():%Y-%m-%d})")

    # XGBoost パラメータ
    xgb_params = dict(
        n_estimators=800, max_depth=7, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7,
        reg_alpha=0.1, reg_lambda=1.0,
        scale_pos_weight=pos_weight,
        tree_method="hist", device="cuda",
        eval_metric="auc", early_stopping_rounds=40,
        random_state=42, verbosity=0,
    )

    # LightGBM パラメータ
    lgbm_params = dict(
        n_estimators=800, max_depth=7, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7,
        reg_alpha=0.1, reg_lambda=1.0,
        scale_pos_weight=pos_weight,
        device="gpu", verbose=-1, random_state=42,
    )

    base_models = [
        ("xgb", XGBClassifier(**xgb_params)),
        ("lgbm", LGBMClassifier(**lgbm_params)),
    ]

    # Out-of-Fold 予測でメタ学習
    n_train = len(X_train)
    n_folds = 5
    fold_size = n_train // n_folds

    oof_preds = {name: np.zeros(n_train) for name, _ in base_models}
    test_preds = {name: np.zeros(len(X_test)) for name, _ in base_models}

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
            w_tr = w_train[train_idx]

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
            except Exception as e:
                print(f"    fold {fold+1} 失敗: {e}")
                continue

            oof_preds[name][val_idx] = model.predict_proba(X_val)[:, 1]
            test_preds[name] += model.predict_proba(X_test)[:, 1] / n_folds

        auc = roc_auc_score(y_test, test_preds[name])
        print(f"  {name} テストAUC: {auc:.4f}")

    # メタラーナー
    meta_X_train = np.column_stack([oof_preds[name] for name, _ in base_models])
    meta_X_test = np.column_stack([test_preds[name] for name, _ in base_models])

    meta_model = LogisticRegression(C=1.0, random_state=42)
    meta_model.fit(meta_X_train, y_train)
    meta_prob = meta_model.predict_proba(meta_X_test)[:, 1]
    meta_auc = roc_auc_score(y_test, meta_prob)
    print(f"\n  メタラーナー テストAUC: {meta_auc:.4f}")
    print(f"  メタラーナー係数: {dict(zip([n for n, _ in base_models], meta_model.coef_[0]))}")

    # ── 10. 最終モデルの全データ学習 ──
    print("\n最終モデル（全データ再学習）...")
    X_all = pd.concat([X_train, X_test], ignore_index=True)
    y_all = pd.concat([y_train, y_test], ignore_index=True)
    w_all = np.concatenate([w_train, np.ones(len(X_test))])

    final_models = {}
    for name, model_template in base_models:
        model = copy.deepcopy(model_template)
        # early_stopping を無効化
        if hasattr(model, "early_stopping_rounds"):
            model.set_params(early_stopping_rounds=None)
        try:
            if name == "lgbm":
                try:
                    model.fit(X_all, y_all, sample_weight=w_all)
                except Exception:
                    model.set_params(device="cpu")
                    model.fit(X_all, y_all, sample_weight=w_all)
            else:
                model.fit(X_all, y_all, sample_weight=w_all)
            final_models[name] = model
            print(f"  {name}: 学習完了")
        except Exception as e:
            print(f"  {name}: 学習失敗 - {e}")

    # 分類レポート
    if final_models.get("xgb"):
        xgb_prob_final = final_models["xgb"].predict_proba(X_test)[:, 1]
        print(f"\n最終 XGBoost AUC: {roc_auc_score(y_test, xgb_prob_final):.4f}")
        y_pred = (xgb_prob_final > 0.5).astype(int)
        print("\n分類レポート（XGBoost）:")
        print(classification_report(y_test, y_pred, target_names=["下落/横ばい", "3%以上上昇"]))

    # 特徴量重要度
    if final_models.get("xgb"):
        importance = pd.Series(
            final_models["xgb"].feature_importances_,
            index=feature_names
        ).sort_values(ascending=False)
        print("\n特徴量重要度 TOP20:")
        for i, (feat_name, imp) in enumerate(importance.head(20).items()):
            print(f"  {i+1:2d}. {feat_name}: {imp:.4f}")

        # 決算固有特徴量の重要度
        earnings_feats = [f for f in feature_names if any(k in f for k in [
            "surprise", "yoy", "momentum", "beat", "sector_beat",
            "pre_earn", "historical", "recent",
        ])]
        if earnings_feats:
            earn_imp = importance[importance.index.isin(earnings_feats)].sort_values(ascending=False)
            print("\n決算固有特徴量の重要度:")
            for feat_name, imp in earn_imp.items():
                print(f"  {feat_name}: {imp:.4f}")

    # ── 11. モデル保存 ──
    # v2互換フォーマット（ml_predictor.py で読めるように）
    xgb_model = final_models.get("xgb")
    if xgb_model:
        save_data = {
            "model": xgb_model,
            "features": feature_names,
            "meta_model": meta_model,
            "base_models": final_models,
            "meta_auc": meta_auc,
            "cv_aucs_xgb": cv_aucs_xgb,
            "cv_aucs_lgbm": cv_aucs_lgbm,
            "n_samples": len(X),
            "pos_rate": float(y.mean()),
            "version": "v3_earnings",
        }

        save_path = MODELS_DIR / "xgboost_earnings.pkl"
        with open(save_path, "wb") as f:
            pickle.dump(save_data, f)
        print(f"\n保存完了: {save_path}")
        print(f"  サンプル数: {len(X):,}")
        print(f"  特徴量数: {len(feature_names)}")
        print(f"  メタAUC: {meta_auc:.4f}")
    else:
        print("\nエラー: XGBoostモデルの学習に失敗しました。")

    # ── 12. 最終サマリー ──
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("学習完了サマリー")
    print("=" * 60)
    print(f"  総イベント数: {len(X):,}")
    print(f"  ユニーク銘柄数: {len(set(e['code'] for e in all_event_info)):,}")
    print(f"  正例率: {y.mean():.1%}")
    print(f"  Purged CV AUC (XGBoost): {np.mean(cv_aucs_xgb):.4f}" if cv_aucs_xgb else "  XGBoost CV: N/A")
    print(f"  Purged CV AUC (LightGBM): {np.mean(cv_aucs_lgbm):.4f}" if cv_aucs_lgbm else "  LightGBM CV: N/A")
    print(f"  メタラーナー AUC: {meta_auc:.4f}")
    print(f"  処理時間: {elapsed/60:.1f} 分")


if __name__ == "__main__":
    main()
