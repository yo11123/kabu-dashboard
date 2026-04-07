"""
AIレコメンド — ML + テクニカルスコアで全銘柄を評価し上位を表示

処理フロー:
  1. 日経225銘柄のデータを並列ダウンロード
  2. 各銘柄に対して ML予測 + テクニカルスコアを算出
  3. 複合スコア (0-100) でランキング
  4. 上位銘柄を詳細カード + ソート可能テーブルで表示
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from modules.data_loader import load_tickers
from modules.ml_predictor import predict_direction_xgb, predict_buy_timing, get_available_models
from modules.styles import apply_theme
from modules.loading import helix_spinner

apply_theme()

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")


# ─── テクニカルスコア (フォールバック) ──────────────────────────────────

def _calc_technical_score(df: pd.DataFrame) -> tuple[float, dict[str, str]]:
    """
    MLモデル不要のテクニカルスコア (0-100) と根拠を返す。

    配点:
      RSI(14)             : 20pt  (売られ過ぎ=20, 中立=10, 買われ過ぎ=0)
      MACDヒストグラム正  : 15pt
      SMA25 上回り        : 10pt
      SMA75 上回り        : 10pt
      出来高 > 20日平均   : 10pt
      BB位置 < -1σ        : 15pt  (押し目買い)
      5日リターン > 0     : 10pt  (モメンタム)
      52週安値圏からの回復 : 10pt
    """
    close = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(0, index=df.index)
    score = 0.0
    signals: dict[str, str] = {}

    # ── RSI (14) ──────────────────────────────────────────────────
    if len(close) >= 15:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
        rsi_s = 100 - 100 / (1 + gain / loss)
        rsi = float(rsi_s.iloc[-1]) if not pd.isna(rsi_s.iloc[-1]) else None
        if rsi is not None:
            if rsi < 30:
                score += 20; signals["RSI"] = f"{rsi:.1f} (売られ過ぎ)"
            elif rsi < 50:
                score += 10; signals["RSI"] = f"{rsi:.1f} (中立)"
            else:
                signals["RSI"] = f"{rsi:.1f} (買われ過ぎ)"

    # ── MACD ヒストグラム ─────────────────────────────────────────
    if len(close) >= 35:
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal = macd_line.ewm(span=9, adjust=False).mean()
        hist = float((macd_line - signal).iloc[-1])
        if hist > 0:
            score += 15; signals["MACD"] = "ヒストグラム正 (強気)"
        else:
            signals["MACD"] = "ヒストグラム負"

    # ── SMA25 上回り ──────────────────────────────────────────────
    if len(close) >= 25:
        sma25 = float(close.rolling(25).mean().iloc[-1])
        last = float(close.iloc[-1])
        if last > sma25:
            score += 10; signals["SMA25"] = "上回り"
        else:
            signals["SMA25"] = "下回り"

    # ── SMA75 上回り ──────────────────────────────────────────────
    if len(close) >= 75:
        sma75 = float(close.rolling(75).mean().iloc[-1])
        last = float(close.iloc[-1])
        if last > sma75:
            score += 10; signals["SMA75"] = "上回り"
        else:
            signals["SMA75"] = "下回り"

    # ── 出来高 > 20日平均 ─────────────────────────────────────────
    if len(volume) >= 20:
        vol_now = float(volume.iloc[-1])
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        if vol_avg > 0 and vol_now > vol_avg:
            score += 10; signals["出来高"] = f"{vol_now / vol_avg:.1f}倍"
        else:
            signals["出来高"] = "平均以下"

    # ── ボリンジャーバンド位置 < -1σ ──────────────────────────────
    if len(close) >= 20:
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        std_v = float(bb_std.iloc[-1])
        if std_v > 0:
            sigma = (float(close.iloc[-1]) - float(bb_mid.iloc[-1])) / std_v
            if sigma < -1:
                score += 15; signals["BB"] = f"{sigma:.1f}σ (押し目)"
            else:
                signals["BB"] = f"{sigma:.1f}σ"

    # ── 5日リターン > 0 (モメンタム) ──────────────────────────────
    if len(close) >= 6:
        ret5 = (float(close.iloc[-1]) - float(close.iloc[-6])) / float(close.iloc[-6]) * 100
        if ret5 > 0:
            score += 10; signals["モメンタム"] = f"+{ret5:.1f}%"
        else:
            signals["モメンタム"] = f"{ret5:.1f}%"

    # ── 52週安値圏からの回復 ──────────────────────────────────────
    if len(close) >= 20:
        low52 = float(close.tail(min(len(close), 252)).min())
        last = float(close.iloc[-1])
        if low52 > 0:
            pct_from_low = (last - low52) / low52 * 100
            if 5 < pct_from_low < 30:
                score += 10; signals["安値圏回復"] = f"+{pct_from_low:.1f}%"
            elif pct_from_low <= 5:
                signals["安値圏回復"] = f"安値付近 (+{pct_from_low:.1f}%)"
            else:
                signals["安値圏回復"] = f"安値から遠い (+{pct_from_low:.1f}%)"

    return min(score, 100.0), signals


# ─── テクニカルシグナル要約 ───────────────────────────────────────────

def _summarize_signals(signals: dict[str, str]) -> str:
    """テクニカルシグナルの辞書から短い要約文字列を生成する。"""
    bullish = []
    bearish = []
    for key, val in signals.items():
        if any(w in val for w in ["売られ過ぎ", "正", "上回り", "押し目", "倍"]):
            bullish.append(key)
        elif any(w in val for w in ["買われ過ぎ", "負", "下回り", "平均以下"]):
            bearish.append(key)
    if len(bullish) >= 4:
        return "強い買い"
    elif len(bullish) >= 2:
        return "買い"
    elif len(bearish) >= 4:
        return "売り"
    elif len(bearish) >= 2:
        return "弱い"
    return "中立"


# ─── 1銘柄のスコアリング ─────────────────────────────────────────────

def _score_single_stock(code: str, name: str, sector: str,
                        ml_available: bool) -> dict | None:
    """
    1銘柄のデータ取得・スコアリングを行い結果辞書を返す。
    失敗時は None を返す。
    """
    try:
        t = yf.Ticker(code)
        df = t.history(period="1y", interval="1d", auto_adjust=True)
        if df is None or df.empty:
            return None

        # カラム正規化
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(c[0]).capitalize() for c in df.columns]
        else:
            df.columns = [str(c).capitalize() for c in df.columns]
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.dropna(subset=["Close"], inplace=True)

        if len(df) < 30:
            return None

        last = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-2]) if len(df) >= 2 else last
        chg_pct = (last - prev) / prev * 100 if prev > 0 else 0.0

        # テクニカルスコア（常に計算）
        tech_score, tech_signals = _calc_technical_score(df)

        # ML予測（モデルがある場合のみ）
        direction_prob = None
        timing_prob = None
        if ml_available:
            direction_prob = predict_direction_xgb(df)
            timing_prob = predict_buy_timing(df)

        # 複合スコア算出 (0-100)
        if direction_prob is not None and timing_prob is not None:
            # ML利用可能: ML 60% + テクニカル 40%
            ml_score = (direction_prob * 0.5 + timing_prob * 0.5)
            composite = ml_score * 0.6 + tech_score * 0.4
        elif direction_prob is not None:
            # 方向予測のみ
            composite = direction_prob * 0.5 + tech_score * 0.5
        elif timing_prob is not None:
            # タイミング予測のみ
            composite = timing_prob * 0.5 + tech_score * 0.5
        else:
            # MLなし: テクニカルのみ
            composite = tech_score

        composite = max(0.0, min(100.0, composite))

        # 方向予測テキスト
        if direction_prob is not None:
            if direction_prob >= 60:
                dir_text = "上昇"
            elif direction_prob <= 40:
                dir_text = "下落"
            else:
                dir_text = "横ばい"
            confidence = direction_prob if direction_prob >= 50 else (100 - direction_prob)
        else:
            dir_text = _summarize_signals(tech_signals)
            confidence = tech_score

        return {
            "銘柄コード": code.replace(".T", ""),
            "銘柄名": name,
            "セクター": sector,
            "現在値": last,
            "前日比(%)": round(chg_pct, 2),
            "MLスコア": round(composite, 1),
            "方向予測": dir_text,
            "信頼度": round(confidence, 1),
            "テクニカルシグナル": _summarize_signals(tech_signals),
            # 詳細用（テーブルには非表示）
            "_ticker": code,
            "_tech_score": round(tech_score, 1),
            "_direction_prob": direction_prob,
            "_timing_prob": timing_prob,
            "_tech_signals": tech_signals,
            "_last_price": last,
            "_change_pct": chg_pct,
        }
    except Exception:
        return None


# ─── メインスキャン（キャッシュ付き）────────────────────────────────────

@st.cache_data(ttl=14400, show_spinner=False)
def _run_recommend_scan(
    ticker_codes: tuple,
    ticker_names: tuple,
    ticker_sectors: tuple,
) -> list[dict]:
    """
    全銘柄を並列スコアリングし、スコア降順のリストを返す（4時間キャッシュ）。
    """
    models = get_available_models()
    ml_available = models.get("XGBoost方向予測", False) or models.get("最適売買タイミング", False)

    results: list[dict] = []

    # 並列データ取得 + スコアリング
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for code, name, sector in zip(ticker_codes, ticker_names, ticker_sectors):
            f = executor.submit(_score_single_stock, code, name, sector, ml_available)
            futures[f] = code

        for future in as_completed(futures):
            try:
                result = future.result(timeout=30)
                if result is not None:
                    results.append(result)
            except Exception:
                continue

    # スコア降順ソート
    results.sort(key=lambda x: x["MLスコア"], reverse=True)
    return results


# ─── カード描画 ───────────────────────────────────────────────────────

def _render_detail_card(rank: int, item: dict) -> None:
    """上位銘柄の詳細カードを描画する。"""
    score = item["MLスコア"]
    direction = item["方向予測"]
    chg = item["前日比(%)"]
    chg_sign = "▲" if chg >= 0 else "▼"
    chg_color = "#5ca08b" if chg >= 0 else "#c45c5c"

    # スコアに応じた色
    if score >= 70:
        score_color = "#00c853"
    elif score >= 50:
        score_color = "#d4af37"
    elif score >= 30:
        score_color = "#ff9800"
    else:
        score_color = "#f44336"

    # 方向に応じた色
    dir_colors = {
        "上昇": "#5ca08b", "強い買い": "#00c853", "買い": "#5ca08b",
        "下落": "#c45c5c", "売り": "#f44336",
        "横ばい": "#9e9e9e", "中立": "#9e9e9e", "弱い": "#ff9800",
    }
    dir_color = dir_colors.get(direction, "#9e9e9e")

    with st.container(border=True):
        # ── ヘッダー行 ────────────────────────────────────────────
        h1, h2, h3 = st.columns([4, 3, 3])
        with h1:
            st.markdown(
                f"<span style='color:{score_color};font-family:Cormorant Garamond,serif;"
                f"font-size:1.5em;font-weight:600'>{rank}</span>"
                f"&ensp;<b style='font-size:1.1em'>{item['銘柄名']}</b>"
                f"&ensp;<span style='color:#6b7280;font-size:0.85em'>{item['銘柄コード']}</span>"
                f"&ensp;<span style='color:#6b7280;font-size:0.75em'>{item['セクター']}</span>",
                unsafe_allow_html=True,
            )
        with h2:
            st.markdown(
                f"<span style='font-size:1.2em;font-weight:bold;color:{score_color}'>"
                f"Score {score:.0f}</span>"
                f"&ensp;<span style='color:{dir_color};font-size:1em'>{direction}</span>",
                unsafe_allow_html=True,
            )
        with h3:
            st.markdown(
                f"<b>¥{item['現在値']:,.0f}</b>"
                f"&ensp;<span style='color:{chg_color}'>{chg_sign}{abs(chg):.2f}%</span>",
                unsafe_allow_html=True,
            )

        # ── スコアバー ────────────────────────────────────────────
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("複合スコア", f"{score:.0f} / 100")
        sc2.metric("テクニカル", f"{item['_tech_score']:.0f} / 100")
        dp = item.get("_direction_prob")
        sc3.metric("方向予測(ML)", f"{dp:.0f}%" if dp is not None else "N/A")
        tp = item.get("_timing_prob")
        sc4.metric("タイミング(ML)", f"{tp:.0f}%" if tp is not None else "N/A")

        # ── テクニカルシグナル詳細 ────────────────────────────────
        with st.expander("テクニカルシグナル詳細"):
            signals = item.get("_tech_signals", {})
            if signals:
                cols = st.columns(min(len(signals), 4))
                for i, (key, val) in enumerate(signals.items()):
                    with cols[i % len(cols)]:
                        # 色分け
                        if any(w in val for w in ["売られ過ぎ", "正", "上回り", "押し目", "倍"]):
                            sig_color = "#5ca08b"
                        elif any(w in val for w in ["買われ過ぎ", "負", "下回り", "平均以下"]):
                            sig_color = "#c45c5c"
                        else:
                            sig_color = "#9e9e9e"
                        st.markdown(
                            f"<div style='background:#0e1320;padding:8px 12px;border-radius:6px;"
                            f"border-left:3px solid {sig_color};margin:3px 0'>"
                            f"<span style='color:#b8b0a2;font-size:0.8em'>{key}</span><br>"
                            f"<span style='color:{sig_color};font-weight:500'>{val}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
            else:
                st.caption("シグナルなし")

        # ── チャートボタン ────────────────────────────────────────
        if st.button(
            "チャートで詳細確認",
            key=f"rec_chart_{item['_ticker']}_{rank}",
            type="primary",
            use_container_width=True,
            icon=":material/candlestick_chart:",
        ):
            st.session_state["calendar_selected_ticker"] = item["_ticker"]
            st.switch_page("views/dashboard.py")

    st.write("")  # カード間の余白


# ─── ページ本体 ───────────────────────────────────────────────────────

# タイトル
st.markdown(
    "<h1 style='font-family: Cormorant Garamond, serif; font-weight: 300;"
    "letter-spacing: 0.08em; color: #d4af37; margin-bottom: 0.2em'>"
    "AI Recommend</h1>"
    "<p style='color: #6b7280; font-size: 0.85em; margin-bottom: 1.5em'>"
    "ML + テクニカル指標で日経225銘柄をスコアリングし、有望銘柄を自動抽出</p>",
    unsafe_allow_html=True,
)

# MLモデル利用状況
models = get_available_models()
ml_status_parts = []
for name, avail in models.items():
    if name in ("XGBoost方向予測", "最適売買タイミング"):
        icon = "🟢" if avail else "⚪"
        ml_status_parts.append(f"{icon} {name}")
st.caption("　".join(ml_status_parts))

# ── サイドバー: フィルターオプション ──────────────────────────────────

# 銘柄リスト読み込み
tickers = load_tickers(TICKERS_PATH)
if not tickers:
    st.error("銘柄リストが読み込めません。data/nikkei225_tickers.txt を確認してください。")
    st.stop()

# セクター一覧
all_sectors = sorted(set(t.get("sector", "") for t in tickers if t.get("sector")))

with st.sidebar:
    st.markdown("### フィルター設定")
    selected_sectors = st.multiselect(
        "セクター",
        options=all_sectors,
        default=[],
        placeholder="全セクター",
    )
    min_score = st.slider("最低スコア", 0, 80, 30, step=5)
    direction_filter = st.selectbox(
        "方向予測",
        options=["すべて", "上昇", "下落", "横ばい"],
        index=0,
    )
    show_top_n = st.slider("上位カード表示数", 3, 20, 10)

    if st.button("キャッシュクリア", use_container_width=True,
                 icon=":material/refresh:"):
        _run_recommend_scan.clear()
        st.rerun()

# ── スキャン実行 ──────────────────────────────────────────────────────

codes = tuple(t["code"] for t in tickers)
names = tuple(t["name"] for t in tickers)
sectors = tuple(t.get("sector", "") for t in tickers)

with helix_spinner("日経225銘柄をスコアリング中..."):
    all_results = _run_recommend_scan(codes, names, sectors)

if not all_results:
    st.warning("スコアリング結果が得られませんでした。しばらく時間をおいて再試行してください。")
    st.stop()

# ── フィルタリング ────────────────────────────────────────────────────

filtered = all_results.copy()

# セクターフィルター
if selected_sectors:
    filtered = [r for r in filtered if r["セクター"] in selected_sectors]

# 最低スコアフィルター
filtered = [r for r in filtered if r["MLスコア"] >= min_score]

# 方向予測フィルター
if direction_filter != "すべて":
    dir_map = {
        "上昇": ["上昇", "強い買い", "買い"],
        "下落": ["下落", "売り"],
        "横ばい": ["横ばい", "中立", "弱い"],
    }
    allowed = dir_map.get(direction_filter, [])
    filtered = [r for r in filtered if r["方向予測"] in allowed]

st.markdown(
    f"<p style='color:#b8b0a2'>全 <b>{len(all_results)}</b> 銘柄中"
    f" <b style='color:#d4af37'>{len(filtered)}</b> 銘柄が条件に合致</p>",
    unsafe_allow_html=True,
)

if not filtered:
    st.info("条件に合致する銘柄がありません。フィルター条件を緩和してください。")
    st.stop()

# ── 上位銘柄カード ────────────────────────────────────────────────────

st.markdown(
    "<h2 style='font-family: Cormorant Garamond, serif; font-weight: 300;"
    "color: #d4af37; font-size: 1.3em; margin-top: 0.5em'>Top Picks</h2>",
    unsafe_allow_html=True,
)

for i, item in enumerate(filtered[:show_top_n], start=1):
    _render_detail_card(i, item)

# ── ソート可能テーブル ────────────────────────────────────────────────

st.markdown(
    "<h2 style='font-family: Cormorant Garamond, serif; font-weight: 300;"
    "color: #d4af37; font-size: 1.3em; margin-top: 1em'>All Rankings</h2>",
    unsafe_allow_html=True,
)

# テーブル用データフレーム（内部カラムを除外）
display_cols = ["銘柄コード", "銘柄名", "現在値", "前日比(%)", "MLスコア",
                "方向予測", "信頼度", "テクニカルシグナル", "セクター"]
df_table = pd.DataFrame(filtered)[display_cols].copy()

# 現在値をフォーマット
df_table["現在値"] = df_table["現在値"].apply(lambda x: f"¥{x:,.0f}")

st.dataframe(
    df_table,
    use_container_width=True,
    hide_index=True,
    height=min(len(df_table) * 38 + 40, 600),
    column_config={
        "MLスコア": st.column_config.ProgressColumn(
            "MLスコア",
            min_value=0,
            max_value=100,
            format="%.0f",
        ),
        "信頼度": st.column_config.ProgressColumn(
            "信頼度",
            min_value=0,
            max_value=100,
            format="%.0f%%",
        ),
        "前日比(%)": st.column_config.NumberColumn(
            "前日比(%)",
            format="%.2f%%",
        ),
    },
)

# ── フッター ─────────────────────────────────────────────────────────
st.divider()
st.caption(
    "スコアは ML予測 (XGBoost方向予測 + 買いタイミング) とテクニカル指標 "
    "(RSI, MACD, SMA, BB, 出来高, モメンタム) の複合評価です。"
    "MLモデル未学習の場合はテクニカルスコアのみで評価します。"
    "結果は4時間キャッシュされます。投資判断は自己責任でお願いします。"
)
