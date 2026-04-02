"""
全MLモデルの一括学習スクリプト（GPU対応）

使い方:
    python train/train_all.py

4つのモデルを学習:
    1. XGBoost 株価方向予測（5日後に上がるか）
    2. LSTM 株価方向予測（より高精度）
    3. 決算サプライズ予測（EPSが予想を超えるか）
    4. 最適売買タイミング（テクニカル+ファンダ+ニュースセンチメント）

学習済みモデルは models/ に保存され、アプリで使用される。
"""
import os
import sys
import warnings
import pickle
from pathlib import Path

# Windows cp932 エンコードエラー回避
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import yfinance as yf
from tqdm import tqdm

warnings.filterwarnings("ignore")

# パス設定
ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"
MODELS_DIR.mkdir(exist_ok=True)

# 日経225銘柄を読み込み
TICKERS_PATH = DATA_DIR / "nikkei225_tickers.txt"


def load_nikkei225() -> list[str]:
    """日経225の銘柄コードを読み込む。"""
    codes = []
    with open(TICKERS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if parts:
                codes.append(parts[0].strip())
    return [c for c in codes if c.endswith(".T")]


# ═══════════════════════════════════════════════════════════════════
# 特徴量計算
# ═══════════════════════════════════════════════════════════════════


def calc_features(df: pd.DataFrame) -> pd.DataFrame:
    """株価データからMLモデル用の特徴量を計算する。"""
    close = df["Close"].copy()
    high = df["High"].copy()
    low = df["Low"].copy()
    volume = df["Volume"].copy() if "Volume" in df.columns else pd.Series(0, index=df.index)

    feat = pd.DataFrame(index=df.index)

    # ── テクニカル指標 ──────────────────────────────────────────
    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    feat["rsi_14"] = 100 - 100 / (1 + gain / loss)

    # RSI(5) - 短期
    gain5 = delta.clip(lower=0).rolling(5).mean()
    loss5 = (-delta.clip(upper=0)).rolling(5).mean().replace(0, np.nan)
    feat["rsi_5"] = 100 - 100 / (1 + gain5 / loss5)

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    feat["macd"] = ema12 - ema26
    feat["macd_signal"] = feat["macd"].ewm(span=9, adjust=False).mean()
    feat["macd_hist"] = feat["macd"] - feat["macd_signal"]

    # ボリンジャーバンド
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    feat["bb_position"] = (close - bb_mid) / bb_std.replace(0, np.nan)
    feat["bb_width"] = (bb_std * 4) / bb_mid.replace(0, np.nan) * 100  # バンド幅(%)

    # 移動平均乖離率
    for period in [5, 25, 75]:
        sma = close.rolling(period).mean()
        feat[f"sma{period}_dev"] = (close - sma) / sma * 100

    # SMA の傾き
    sma25 = close.rolling(25).mean()
    feat["sma25_slope"] = sma25.pct_change(5) * 100

    # モメンタム
    for days in [1, 3, 5, 10, 20]:
        feat[f"return_{days}d"] = close.pct_change(days) * 100

    # ボラティリティ
    feat["volatility_20d"] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    feat["volatility_5d"] = close.pct_change().rolling(5).std() * np.sqrt(252) * 100

    # ATR(14)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    feat["atr_14"] = tr.rolling(14).mean() / close * 100

    # 出来高比
    vol_ma20 = volume.rolling(20).mean()
    feat["volume_ratio"] = volume / vol_ma20.replace(0, np.nan)

    # 出来高変化率
    feat["volume_change_5d"] = volume.rolling(5).mean() / volume.rolling(20).mean()

    # ストキャスティクス
    low14 = low.rolling(14).min()
    high14 = high.rolling(14).max()
    feat["stoch_k"] = (close - low14) / (high14 - low14).replace(0, np.nan) * 100
    feat["stoch_d"] = feat["stoch_k"].rolling(3).mean()

    # CCI(20)
    tp = (high + low + close) / 3
    feat["cci_20"] = (tp - tp.rolling(20).mean()) / (tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean()) * 0.015)

    # 52週高値/安値からの乖離
    feat["from_52w_high"] = (close / close.rolling(252).max() - 1) * 100
    feat["from_52w_low"] = (close / close.rolling(252).min() - 1) * 100

    # 日次リターンの自己相関（モメンタム持続性）
    feat["autocorr_5d"] = close.pct_change().rolling(20).apply(
        lambda x: x.autocorr(lag=1) if len(x.dropna()) > 5 else np.nan, raw=False
    )

    # 上昇日比率
    feat["up_day_ratio_10d"] = (close.diff() > 0).rolling(10).mean()
    feat["up_day_ratio_20d"] = (close.diff() > 0).rolling(20).mean()

    # 曜日（ワンホット）
    feat["weekday"] = df.index.dayofweek

    # 月（季節性）
    feat["month"] = df.index.month

    return feat


def calc_fundamental_features(ticker: str) -> dict:
    """ファンダメンタル特徴量を取得する（静的、リアルタイム）。"""
    try:
        info = yf.Ticker(ticker).info
        return {
            "per": info.get("trailingPE"),
            "pbr": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "dividend_yield": info.get("dividendYield"),
            "revenue_growth": info.get("revenueGrowth"),
            "operating_margin": info.get("operatingMargins"),
            "beta": info.get("beta"),
            "market_cap_log": np.log10(info["marketCap"]) if info.get("marketCap") else None,
        }
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════
# モデル1: XGBoost 株価方向予測
# ═══════════════════════════════════════════════════════════════════


def train_xgboost_direction():
    """5日後に+2%以上上がるかを予測するXGBoostモデルを学習する。"""
    print("\n" + "=" * 60)
    print("モデル1: XGBoost 株価方向予測")
    print("=" * 60)

    from xgboost import XGBClassifier
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import classification_report, roc_auc_score

    tickers = load_nikkei225()
    all_X, all_y = [], []

    print(f"日経225 ({len(tickers)}銘柄) のデータを取得中...")
    for ticker in tqdm(tickers):
        try:
            df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < 300:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]

            feat = calc_features(df)
            # ターゲット: 5日後に+2%以上上昇
            feat["target"] = (df["Close"].shift(-5) / df["Close"] - 1 > 0.02).astype(int)
            feat = feat.dropna()
            if len(feat) < 100:
                continue

            all_X.append(feat.drop(columns=["target"]))
            all_y.append(feat["target"])
        except Exception:
            continue

    X = pd.concat(all_X, ignore_index=True)
    y = pd.concat(all_y, ignore_index=True)
    print(f"学習データ: {len(X):,} サンプル、特徴量: {X.shape[1]}")
    print(f"正例率: {y.mean():.1%}")

    # 時系列分割
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1),
        tree_method="hist",
        device="cuda",
        eval_metric="auc",
        early_stopping_rounds=30,
        random_state=42,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # 評価
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    print("\n=== テスト結果 ===")
    print(classification_report(y_test, y_pred, target_names=["下落/横ばい", "上昇"]))
    print(f"AUC: {roc_auc_score(y_test, y_prob):.4f}")

    # 特徴量重要度
    importance = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\n=== 特徴量重要度 TOP10 ===")
    print(importance.head(10))

    # 保存
    model_path = MODELS_DIR / "xgboost_direction.pkl"
    with open(model_path, "wb") as f:
        pickle.dump({"model": model, "features": list(X.columns)}, f)
    print(f"\n保存: {model_path} ({model_path.stat().st_size / 1e6:.1f} MB)")


# ═══════════════════════════════════════════════════════════════════
# モデル2: LSTM 株価方向予測
# ═══════════════════════════════════════════════════════════════════


def train_lstm_direction():
    """LSTM で5日後の株価方向を予測するモデルを学習する。"""
    print("\n" + "=" * 60)
    print("モデル2: LSTM 株価方向予測")
    print("=" * 60)

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"デバイス: {device}")

    SEQ_LEN = 20  # 過去20日分を入力
    tickers = load_nikkei225()

    all_sequences = []
    all_labels = []

    print(f"シーケンスデータを構築中...")
    for ticker in tqdm(tickers):
        try:
            df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < 300:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]

            feat = calc_features(df)
            target = (df["Close"].shift(-5) / df["Close"] - 1 > 0.02).astype(float)
            feat["target"] = target
            feat = feat.dropna()
            if len(feat) < SEQ_LEN + 10:
                continue

            values = feat.drop(columns=["target"]).values
            labels = feat["target"].values

            for i in range(SEQ_LEN, len(values) - 5):
                seq = values[i - SEQ_LEN:i]
                if not np.any(np.isnan(seq)) and not np.any(np.isinf(seq)):
                    all_sequences.append(seq)
                    all_labels.append(labels[i])
        except Exception:
            continue

    X = np.array(all_sequences, dtype=np.float32)
    y = np.array(all_labels, dtype=np.float32)
    print(f"データ: {X.shape[0]:,} シーケンス, 特徴量: {X.shape[2]}, 系列長: {SEQ_LEN}")

    # 正規化
    n_samples, seq_len, n_features = X.shape
    X_flat = X.reshape(-1, n_features)
    scaler = StandardScaler()
    X_flat = scaler.fit_transform(X_flat)
    X = X_flat.reshape(n_samples, seq_len, n_features).astype(np.float32)

    # NaN/Inf チェック
    mask = ~(np.isnan(X).any(axis=(1, 2)) | np.isinf(X).any(axis=(1, 2)))
    X, y = X[mask], y[mask]

    # 分割
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    test_ds = TensorDataset(torch.tensor(X_test), torch.tensor(y_test))
    train_dl = DataLoader(train_ds, batch_size=256, shuffle=True)
    test_dl = DataLoader(test_ds, batch_size=512)

    # モデル定義
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

    model = LSTMPredictor(n_features).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=30)
    criterion = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor([(y_train == 0).sum() / max((y_train == 1).sum(), 1)]).to(device)
    )

    best_auc = 0
    for epoch in range(30):
        model.train()
        losses = []
        for xb, yb in train_dl:
            xb, yb = xb.to(device), yb.to(device)
            pred = model(xb)
            loss = criterion(pred, yb)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(loss.item())
        scheduler.step()

        # 評価
        model.eval()
        all_prob, all_true = [], []
        with torch.no_grad():
            for xb, yb in test_dl:
                xb = xb.to(device)
                prob = torch.sigmoid(model(xb)).cpu().numpy()
                all_prob.extend(prob)
                all_true.extend(yb.numpy())
        auc = roc_auc_score(all_true, all_prob)
        if auc > best_auc:
            best_auc = auc
            torch.save(model.state_dict(), MODELS_DIR / "lstm_direction.pt")
        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1:2d} | Loss: {np.mean(losses):.4f} | AUC: {auc:.4f} | Best: {best_auc:.4f}")

    print(f"\nBest AUC: {best_auc:.4f}")

    # スケーラーと設定を保存
    with open(MODELS_DIR / "lstm_config.pkl", "wb") as f:
        pickle.dump({
            "scaler": scaler,
            "n_features": n_features,
            "seq_len": SEQ_LEN,
        }, f)
    print(f"保存: {MODELS_DIR / 'lstm_direction.pt'}")


# ═══════════════════════════════════════════════════════════════════
# モデル3: 決算サプライズ予測
# ═══════════════════════════════════════════════════════════════════


def train_earnings_surprise():
    """決算でEPS予想を超過するかを予測するモデルを学習する。"""
    print("\n" + "=" * 60)
    print("モデル3: 決算サプライズ予測")
    print("=" * 60)

    from xgboost import XGBClassifier
    from sklearn.metrics import classification_report, roc_auc_score

    tickers = load_nikkei225()
    all_X, all_y = [], []

    print("決算データを収集中...")
    for ticker in tqdm(tickers):
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

            feat = calc_features(df)

            for dt, row in earn_df.iterrows():
                eps_act = row.get("Reported EPS")
                eps_est = row.get("EPS Estimate")
                if pd.isna(eps_act) or pd.isna(eps_est) or eps_est == 0:
                    continue

                # 決算発表5日前の特徴量
                mask = feat.index <= dt - pd.Timedelta(days=1)
                if mask.sum() < 5:
                    continue
                pre_earn = feat.loc[mask].iloc[-1]
                if pre_earn.isna().sum() > 5:
                    continue

                beat = 1 if float(eps_act) > float(eps_est) else 0
                all_X.append(pre_earn.values)
                all_y.append(beat)
        except Exception:
            continue

    if len(all_X) < 50:
        print("決算データが不足しています（50件未満）。スキップ。")
        return

    feature_names = feat.columns.tolist()
    X = pd.DataFrame(all_X, columns=feature_names)
    y = np.array(all_y)
    # NaN/Inf除去
    mask = ~(X.isna().any(axis=1) | np.isinf(X).any(axis=1))
    X, y = X[mask].reset_index(drop=True), y[mask.values]

    print(f"データ: {len(X):,} 件、正例率（予想超過）: {y.mean():.1%}")

    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y[:split], y[split:]

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        tree_method="hist",
        device="cuda",
        eval_metric="auc",
        early_stopping_rounds=20,
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=30)

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    print("\n=== テスト結果 ===")
    print(classification_report(y_test, y_pred, target_names=["未達", "超過"]))
    print(f"AUC: {roc_auc_score(y_test, y_prob):.4f}")

    with open(MODELS_DIR / "xgboost_earnings.pkl", "wb") as f:
        pickle.dump({"model": model, "features": feature_names}, f)
    print(f"保存: {MODELS_DIR / 'xgboost_earnings.pkl'}")


# ═══════════════════════════════════════════════════════════════════
# モデル4: 最適売買タイミング（テクニカル+ファンダ+ニュース）
# ═══════════════════════════════════════════════════════════════════


def _news_sentiment_score(text: str) -> float:
    """ニュースタイトルから簡易センチメントスコアを計算する。"""
    pos_words = [
        "上昇", "高値", "好調", "増収", "増益", "上方修正", "買い", "反発", "回復",
        "成長", "好決算", "増配", "自社株買い", "最高益", "黒字", "拡大",
        "surge", "rally", "gain", "rise", "bull", "upgrade", "beat",
    ]
    neg_words = [
        "下落", "安値", "低迷", "減収", "減益", "下方修正", "売り", "暴落", "悪化",
        "減配", "赤字", "縮小", "リスク", "懸念", "不安", "戦争", "制裁",
        "crash", "plunge", "loss", "fall", "bear", "downgrade", "miss",
    ]
    t = text.lower()
    pos = sum(1 for w in pos_words if w in t)
    neg = sum(1 for w in neg_words if w in t)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def train_optimal_timing():
    """テクニカル+ファンダ+ニュースセンチメントで最適売買タイミングを学習する。"""
    print("\n" + "=" * 60)
    print("モデル4: 最適売買タイミング（テクニカル+ファンダ+ニュース）")
    print("=" * 60)

    from xgboost import XGBClassifier
    from sklearn.metrics import classification_report, roc_auc_score

    tickers = load_nikkei225()
    all_X, all_y = [], []

    print("マルチソースデータを収集中...")
    for ticker in tqdm(tickers):
        try:
            df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
            if df is None or df.empty or len(df) < 300:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]

            # テクニカル特徴量
            feat = calc_features(df)

            # ファンダメンタル特徴量（静的、全行に同じ値）
            fund = calc_fundamental_features(ticker)
            for k, v in fund.items():
                feat[f"fund_{k}"] = v if v is not None else np.nan

            # ニュースセンチメント（yfinanceのニュースから計算）
            try:
                news = yf.Ticker(ticker).news
                if news:
                    titles = [
                        n.get("title", "")
                        for n in (news if isinstance(news, list) else [])
                    ][:20]
                    avg_sentiment = np.mean([_news_sentiment_score(t) for t in titles]) if titles else 0
                else:
                    avg_sentiment = 0
            except Exception:
                avg_sentiment = 0
            feat["news_sentiment"] = avg_sentiment

            # ── ターゲット: 「この日に買って10日後に売ったら利益が出たか」 ──
            future_return = df["Close"].shift(-10) / df["Close"] - 1

            # 買いシグナル: 10日後に+3%以上
            feat["target_buy"] = (future_return > 0.03).astype(int)

            # 売りシグナル: 10日後に-3%以下
            feat["target_sell"] = (future_return < -0.03).astype(int)

            feat = feat.dropna(subset=["target_buy"])
            feat = feat.dropna(thresh=int(len(feat.columns) * 0.7))  # 70%以上のカラムに値がある行
            if len(feat) < 100:
                continue

            all_X.append(feat.drop(columns=["target_buy", "target_sell"]))
            all_y.append(feat["target_buy"])
        except Exception:
            continue

    X = pd.concat(all_X, ignore_index=True)
    y = pd.concat(all_y, ignore_index=True)
    X = X.fillna(0)

    print(f"データ: {len(X):,} サンプル、特徴量: {X.shape[1]}")
    print(f"買いシグナル率: {y.mean():.1%}")

    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = XGBClassifier(
        n_estimators=500,
        max_depth=7,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.7,
        scale_pos_weight=len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1),
        tree_method="hist",
        device="cuda",
        eval_metric="auc",
        early_stopping_rounds=30,
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    print("\n=== テスト結果 ===")
    print(classification_report(y_test, y_pred, target_names=["見送り", "買い"]))
    print(f"AUC: {roc_auc_score(y_test, y_prob):.4f}")

    # 特徴量重要度
    importance = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\n=== 特徴量重要度 TOP15 ===")
    print(importance.head(15))

    with open(MODELS_DIR / "xgboost_timing.pkl", "wb") as f:
        pickle.dump({"model": model, "features": list(X.columns)}, f)
    print(f"保存: {MODELS_DIR / 'xgboost_timing.pkl'}")


# ═══════════════════════════════════════════════════════════════════
# メイン
# ═══════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    print("[START] 全MLモデル学習開始")
    print(f"モデル保存先: {MODELS_DIR}")

    # GPU確認
    try:
        import torch
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            print("[WARN] GPU未検出。CPUで学習します。")
    except ImportError:
        print("[WARN] PyTorch未インストール。LSTMモデルはスキップされます。")

    # 1. XGBoost方向予測
    train_xgboost_direction()

    # 2. LSTM方向予測
    try:
        import torch
        train_lstm_direction()
    except ImportError:
        print("\n[WARN] PyTorchが未インストールのためLSTMモデルをスキップ")
        print("  pip install torch でインストールしてください")

    # 3. 決算サプライズ予測
    train_earnings_surprise()

    # 4. 最適売買タイミング
    train_optimal_timing()

    print("\n" + "=" * 60)
    print("[DONE] 全モデル学習完了!")
    print(f"保存先: {MODELS_DIR}")
    print("\nモデルファイル:")
    for f in MODELS_DIR.glob("*"):
        if f.is_file() and not f.name.startswith("."):
            print(f"  {f.name} ({f.stat().st_size / 1e6:.1f} MB)")
    print("\n次のステップ:")
    print("  git add models/ && git commit -m 'MLモデル追加' && git push")
