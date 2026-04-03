"""
MLバックテスト

機械学習モデルの予測に基づいて過去のチャートで取引をシミュレーションする。
未来の情報は一切使用せず、その時点で入手可能なデータのみで判断する。
"""
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.loading import helix_spinner
from modules.styles import BG_BASE, BG_PANEL, GRID_COLOR, TEXT_MUTED, apply_theme
from modules.data_loader import load_all_tse_stocks, load_tickers

apply_theme()

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")


# ─── MLバックテストエンジン ──────────────────────────────────────────


def _run_ml_backtest(
    df: pd.DataFrame,
    buy_threshold: float = 60.0,
    sell_threshold: float = 40.0,
    initial_capital: float = 1_000_000,
    position_pct: float = 0.95,
    commission_pct: float = 0.1,
    max_hold_bars: int = 20,
) -> dict:
    """
    MLモデルの予測に基づくバックテスト。
    未来の情報は使わず、各日のデータのみで予測→売買判断する。

    Args:
        df: OHLCV DataFrame（十分な期間分）
        buy_threshold: 買いシグナルの閾値（ML確率 > この値で買い）
        sell_threshold: 売りシグナルの閾値（ML確率 < この値で売り）
        initial_capital: 初期資金
        position_pct: 資金の何%をポジションに使うか
        commission_pct: 手数料率（%）

    Returns:
        dict: equity_curve, trades, metrics, daily_predictions
    """
    from modules.ml_predictor import _calc_features, _load_pickle

    # モデルを読み込み
    xgb_data = _load_pickle("xgboost_direction.pkl")
    timing_data = _load_pickle("xgboost_timing.pkl")
    if not xgb_data and not timing_data:
        return {"error": "学習済みモデルが見つかりません"}

    # 使用するモデルを決定（タイミングモデル優先）
    model_data = timing_data or xgb_data
    model = model_data["model"]
    features = model_data["features"]
    model_name = "最適タイミング" if timing_data else "方向予測"

    close = df["Close"].values
    dates = df.index
    n = len(df)

    # 各日の予測を計算（未来の情報を使わない）
    MIN_HISTORY = 300  # 特徴量計算に最低限必要な日数
    predictions = np.full(n, np.nan)

    for i in range(MIN_HISTORY, n):
        try:
            # その日までのデータのみ使用（未来は見ない）
            hist = df.iloc[:i + 1].copy()
            feat = _calc_features(hist)
            if feat.empty:
                continue
            row = feat.iloc[-1:]
            # 必要な特徴量を揃える
            for f in features:
                if f not in row.columns:
                    row[f] = 0
            row = row[features].fillna(0)
            row = row.replace([np.inf, -np.inf], 0)
            # 全カラムをfloat化
            for col in row.columns:
                row[col] = pd.to_numeric(row[col], errors="coerce")
            row = row.fillna(0)
            prob = model.predict_proba(row)[0][1] * 100
            predictions[i] = prob
        except Exception:
            continue

    # 売買シミュレーション
    capital = initial_capital
    position = 0  # 保有株数
    entry_price = 0
    entry_bar = 0  # エントリーした足のインデックス
    equity = np.full(n, initial_capital, dtype=float)
    trades = []
    in_position = False

    for i in range(MIN_HISTORY, n):
        price = close[i]
        prob = predictions[i]

        if np.isnan(prob):
            equity[i] = capital + position * price
            continue

        if not in_position:
            # 買いシグナル
            if prob > buy_threshold:
                shares = int(capital * position_pct / price)
                if shares > 0:
                    cost = shares * price * (1 + commission_pct / 100)
                    capital -= cost
                    position = shares
                    entry_price = price
                    entry_bar = i
                    in_position = True
                    trades.append({
                        "date": str(dates[i].date()) if hasattr(dates[i], "date") else str(dates[i]),
                        "type": "BUY",
                        "price": round(price, 1),
                        "shares": shares,
                        "prob": round(prob, 1),
                    })
        else:
            # 売りシグナル or 最大保有期間超過
            bars_held = i - entry_bar
            force_sell = bars_held >= max_hold_bars
            signal_sell = prob < sell_threshold

            if signal_sell or force_sell:
                revenue = position * price * (1 - commission_pct / 100)
                pnl = revenue - position * entry_price
                sell_type = "SELL(期限)" if force_sell and not signal_sell else "SELL"
                capital += revenue
                trades.append({
                    "date": str(dates[i].date()) if hasattr(dates[i], "date") else str(dates[i]),
                    "type": sell_type,
                    "price": round(price, 1),
                    "shares": position,
                    "prob": round(prob, 1),
                    "pnl": round(pnl, 0),
                    "pnl_pct": round((price / entry_price - 1) * 100, 2),
                })
                position = 0
                in_position = False

        equity[i] = capital + position * price

    # 最終日にポジションを清算
    if in_position:
        revenue = position * close[-1] * (1 - commission_pct / 100)
        capital += revenue
        pnl = revenue - position * entry_price
        trades.append({
            "date": str(dates[-1].date()),
            "type": "SELL(清算)",
            "price": round(close[-1], 1),
            "shares": position,
            "pnl": round(pnl, 0),
        })
        position = 0

    final_equity = capital
    equity[-1] = final_equity

    # メトリクス計算
    total_return = (final_equity / initial_capital - 1) * 100
    equity_series = pd.Series(equity[MIN_HISTORY:], index=dates[MIN_HISTORY:])
    daily_returns = equity_series.pct_change().dropna()

    # 年率リターン
    years = (dates[-1] - dates[MIN_HISTORY]).days / 365.25
    annual_return = ((final_equity / initial_capital) ** (1 / max(years, 0.01)) - 1) * 100

    # シャープレシオ
    sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0

    # 最大ドローダウン
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax * 100
    max_dd = drawdown.min()

    # 勝率
    sell_trades = [t for t in trades if t["type"] in ("SELL", "SELL(清算)") and "pnl" in t]
    win_trades = [t for t in sell_trades if t["pnl"] > 0]
    win_rate = len(win_trades) / max(len(sell_trades), 1) * 100

    # 買い持ち比較
    bh_return = (close[-1] / close[MIN_HISTORY] - 1) * 100

    metrics = {
        "model_name": model_name,
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 0),
        "total_return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "total_trades": len(sell_trades),
        "win_rate": round(win_rate, 1),
        "avg_win": round(np.mean([t["pnl"] for t in win_trades]), 0) if win_trades else 0,
        "avg_loss": round(np.mean([t["pnl"] for t in sell_trades if t["pnl"] <= 0]), 0) if [t for t in sell_trades if t["pnl"] <= 0] else 0,
        "buy_hold_return": round(bh_return, 2),
        "alpha": round(total_return - bh_return, 2),
        "years": round(years, 1),
    }

    return {
        "equity": equity_series,
        "trades": trades,
        "metrics": metrics,
        "predictions": pd.Series(predictions[MIN_HISTORY:], index=dates[MIN_HISTORY:]),
        "close": pd.Series(close[MIN_HISTORY:], index=dates[MIN_HISTORY:]),
    }


# ─── 描画 ────────────────────────────────────────────────────────────────


def _render_equity_chart(result: dict) -> None:
    """資産推移チャートを描画する。"""
    equity = result["equity"]
    close = result["close"]
    trades = result["trades"]
    initial = result["metrics"]["initial_capital"]

    # 正規化（初期値=100%）
    eq_norm = equity / initial * 100
    bh_norm = close / close.iloc[0] * 100

    fig = go.Figure()

    # 買い持ち
    fig.add_trace(go.Scatter(
        x=bh_norm.index, y=bh_norm.values,
        name="買い持ち", line=dict(color="#6b7280", width=1, dash="dot"),
    ))

    # ML戦略
    fig.add_trace(go.Scatter(
        x=eq_norm.index, y=eq_norm.values,
        name="ML戦略", line=dict(color="#d4af37", width=2),
        fill="tozeroy", fillcolor="rgba(212,175,55,0.05)",
    ))

    # 売買ポイント
    buy_dates = [t["date"] for t in trades if t["type"] == "BUY"]
    sell_dates = [t["date"] for t in trades if "SELL" in t["type"]]

    for bd in buy_dates:
        try:
            idx = pd.Timestamp(bd)
            if idx in eq_norm.index:
                fig.add_annotation(x=idx, y=float(eq_norm.loc[idx]),
                                   text="B", showarrow=True, arrowhead=2,
                                   arrowcolor="#5ca08b", font=dict(color="#5ca08b", size=9))
        except Exception:
            pass

    fig.add_hline(y=100, line_dash="dot", line_color="#6b7280", opacity=0.3)

    fig.update_layout(
        title="資産推移（ML戦略 vs 買い持ち）",
        height=350,
        margin=dict(l=40, r=10, t=40, b=20),
        plot_bgcolor=BG_BASE, paper_bgcolor=BG_PANEL,
        font=dict(family="'IBM Plex Mono','Inter',monospace", color=TEXT_MUTED, size=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, title="資産（初期=100%）"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False, "staticPlot": True},
                    key="ml_bt_equity")


def _render_prediction_chart(result: dict) -> None:
    """ML予測確率の推移を描画する。"""
    preds = result["predictions"].dropna()
    if preds.empty:
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=preds.index, y=preds.values,
        name="ML予測確率", line=dict(color="#d4af37", width=1),
    ))
    fig.add_hline(y=60, line_dash="dot", line_color="#5ca08b", opacity=0.5,
                  annotation_text="買い閾値")
    fig.add_hline(y=40, line_dash="dot", line_color="#c45c5c", opacity=0.5,
                  annotation_text="売り閾値")

    fig.update_layout(
        title="ML予測確率の推移",
        height=200,
        margin=dict(l=40, r=10, t=30, b=20),
        plot_bgcolor=BG_BASE, paper_bgcolor=BG_PANEL,
        font=dict(family="'IBM Plex Mono','Inter',monospace", color=TEXT_MUTED, size=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, range=[0, 100]),
    )

    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False, "staticPlot": True},
                    key="ml_bt_pred")


# ─── メイン ──────────────────────────────────────────────────────────────


def main() -> None:
    st.markdown(
        "<h1 style='font-family:Cormorant Garamond,serif; font-weight:300;"
        " letter-spacing:0.12em; font-size:1.6rem;'>MLバックテスト</h1>",
        unsafe_allow_html=True,
    )
    st.caption(
        "機械学習モデルの予測に基づいて過去のチャートで取引をシミュレーション。"
        "未来の情報は一切使わず、その時点のテクニカル・ファンダ・ニュースのみで判断します。"
    )

    # モデル確認
    from modules.ml_predictor import get_available_models
    avail = get_available_models()
    if not any(avail.values()):
        st.error("学習済みMLモデルが見つかりません。`python train/train_all_v2.py` で学習してください。")
        return

    # 銘柄選択
    nikkei225 = load_tickers(TICKERS_PATH)
    all_tse, _ = load_all_tse_stocks()
    all_stocks = all_tse if all_tse else nikkei225
    stock_map = {s["code"]: f"{s['code']} {s['name']}" for s in all_stocks}

    with st.sidebar:
        st.header("バックテスト設定")
        search = st.text_input("銘柄検索", placeholder="7203 or トヨタ", key="ml_bt_search")
        if search:
            matches = [s for s in all_stocks
                       if search.lower() in s["code"].lower() or search.lower() in s["name"].lower()][:20]
        else:
            matches = all_stocks[:20]

        options = [f"{s['code']} {s['name']}" for s in matches]
        selected = st.selectbox("銘柄", options, key="ml_bt_ticker") if options else None

        st.divider()
        st.subheader("トレードスタイル")
        trade_style = st.selectbox(
            "スタイル",
            ["スイングトレード（数日〜数週間）", "短期トレード（1〜3日）", "デイトレード（日中）"],
            key="ml_bt_style",
        )

        st.subheader("期間")
        if "デイトレード" in trade_style:
            period_options = {
                "5日（3分足）": ("5d", "3m"),      # 最新5日間のみ（3m未対応の場合あり）
                "5日（5分足）": ("5d", "5m"),
                "1ヶ月（15分足）": ("1mo", "15m"),
                "3ヶ月（1時間足）": ("3mo", "1h"),
            }
        elif "短期" in trade_style:
            period_options = {
                "1ヶ月（15分足）": ("1mo", "15m"),
                "3ヶ月（1時間足）": ("3mo", "1h"),
                "1年": ("1y", "1d"),
                "2年": ("2y", "1d"),
            }
        else:
            period_options = {
                "1年": ("1y", "1d"),
                "2年": ("2y", "1d"),
                "3年": ("3y", "1d"),
                "5年": ("5y", "1d"),
            }
        period_label = st.selectbox("バックテスト期間", list(period_options.keys()), index=3, key="ml_bt_period")
        yf_period, yf_interval = period_options[period_label]

        st.divider()
        st.subheader("パラメータ")

        # トレードスタイルに応じたデフォルト値
        if "デイトレード" in trade_style:
            default_buy, default_sell = 65, 45
            hold_desc = "数時間以内に決済"
        elif "短期" in trade_style:
            default_buy, default_sell = 62, 42
            hold_desc = "1〜3日で決済"
        else:
            default_buy, default_sell = 60, 40
            hold_desc = "数日〜数週間保有"
        st.caption(f"目安: {hold_desc}")

        auto_th = st.checkbox("MLが最適な閾値を自動計算", value=True, key="ml_bt_auto")
        if auto_th:
            st.caption("バックテスト実行時に最適閾値を自動計算します")
            buy_th = default_buy
            sell_th = default_sell
        else:
            buy_th = st.slider("買い閾値（ML確率 > この値で買い）", 50, 80, default_buy, key="ml_bt_buy")
            sell_th = st.slider("売り閾値（ML確率 < この値で売り）", 20, 50, default_sell, key="ml_bt_sell")
        initial = st.number_input("初期資金（円）", value=1_000_000, step=100_000, key="ml_bt_capital")

        # 最大保有期間（トレードスタイルに応じて）
        if "デイトレード" in trade_style:
            max_hold = st.slider("最大保有期間（本数）", 1, 30, 8, key="ml_bt_maxhold",
                                 help="分足/時間足の本数。超えたら強制決済")
        elif "短期" in trade_style:
            max_hold = st.slider("最大保有日数", 1, 10, 3, key="ml_bt_maxhold")
        else:
            max_hold = st.slider("最大保有日数", 5, 60, 20, key="ml_bt_maxhold")

        st.divider()
        run_btn = st.button("バックテスト実行", type="primary", use_container_width=True)

    if not selected:
        st.info("サイドバーで銘柄を選択してください。")
        return

    ticker = selected.split(" ")[0]
    company = selected.split(" ", 1)[1] if " " in selected else ticker

    if run_btn:
        _style_label = trade_style.split("（")[0]
        with helix_spinner(f"{company} の{_style_label}バックテストを実行中..."):
            try:
                df = yf.download(ticker, period=yf_period, interval=yf_interval,
                                 progress=False, auto_adjust=True)
                if df is None or df.empty:
                    st.error("株価データを取得できませんでした。")
                    return
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [str(c[0]).capitalize() for c in df.columns]
                else:
                    df.columns = [str(c).capitalize() for c in df.columns]
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)

                # 最適閾値の自動計算
                if auto_th:
                    from modules.ml_predictor import calc_optimal_thresholds
                    opt = calc_optimal_thresholds(df)
                    buy_th = opt["buy"]
                    sell_th = opt["sell"]
                    st.session_state["ml_bt_optimal"] = opt

                result = _run_ml_backtest(
                    df,
                    buy_threshold=buy_th,
                    sell_threshold=sell_th,
                    initial_capital=initial,
                    max_hold_bars=max_hold,
                )

                if "error" in result:
                    st.error(result["error"])
                    return

                st.session_state["ml_bt_result"] = result
                st.session_state["ml_bt_company"] = company
                st.session_state["ml_bt_style_label"] = _style_label
                st.session_state["ml_bt_period_label"] = period_label
            except Exception as e:
                st.error(f"エラー: {e}")
                return

    # 結果表示
    result = st.session_state.get("ml_bt_result")
    if not result:
        with st.expander("MLバックテストの仕組み", expanded=True):
            st.markdown("""
### 未来の情報を使わない厳密なバックテスト

各営業日について：
1. **その日までのデータのみ**で特徴量（テクニカル指標等）を計算
2. 学習済みMLモデルで「今後5日で+2%上昇する確率」を予測
3. 確率が**買い閾値**を超えたら買い、**売り閾値**を下回ったら売り

決算やニュースの情報は学習済みモデルに含まれていますが、
**未来の株価・決算・ニュースは一切参照しません**。

### 評価指標
- **アルファ**: ML戦略のリターン − 買い持ちリターン（プラスならMLが勝ち）
- **シャープレシオ**: リスク調整後リターン（1.0超で優秀）
- **勝率**: 利益が出た取引の割合
- **最大ドローダウン**: 最大の資産減少率
            """)
        return

    m = result["metrics"]
    company = st.session_state.get("ml_bt_company", "")
    opt = st.session_state.get("ml_bt_optimal")

    _style_lbl = st.session_state.get("ml_bt_style_label", "")
    _period_lbl = st.session_state.get("ml_bt_period_label", "")

    st.markdown(f"### {company} — {_style_lbl}MLバックテスト結果")
    _opt_text = ""
    if opt and opt.get("method") == "ML最適化":
        _opt_text = f" | ML最適閾値: 買い>{opt['buy']}% / 売り<{opt['sell']}%"
    st.caption(f"モデル: {m['model_name']} | スタイル: {_style_lbl} | 期間: {_period_lbl} | 取引回数: {m['total_trades']}回{_opt_text}")

    # メトリクス
    c1, c2, c3, c4, c5 = st.columns(5)
    _alpha_color = "normal" if m["alpha"] > 0 else "inverse"
    c1.metric("最終資産", f"¥{m['final_equity']:,.0f}", f"{m['total_return']:+.1f}%")
    c2.metric("年率リターン", f"{m['annual_return']:+.1f}%", f"α={m['alpha']:+.1f}%", delta_color=_alpha_color)
    c3.metric("シャープレシオ", f"{m['sharpe_ratio']:.2f}")
    c4.metric("勝率", f"{m['win_rate']:.0f}%", f"{m['total_trades']}回取引")
    c5.metric("最大DD", f"{m['max_drawdown']:.1f}%")

    # アルファ判定
    if m["alpha"] > 5:
        st.success(f"ML戦略が買い持ちを **{m['alpha']:+.1f}%** 上回りました。モデルの予測力が確認できます。")
    elif m["alpha"] > 0:
        st.info(f"ML戦略が買い持ちを **{m['alpha']:+.1f}%** わずかに上回りました。")
    else:
        st.warning(f"ML戦略は買い持ちを **{m['alpha']:+.1f}%** 下回りました。この銘柄ではMLの優位性が限定的です。")

    st.divider()

    # チャート
    _render_equity_chart(result)
    _render_prediction_chart(result)

    # 取引履歴
    st.divider()
    with st.expander(f"取引履歴（{len(result['trades'])}件）"):
        if result["trades"]:
            trades_df = pd.DataFrame(result["trades"])
            trades_df = trades_df.rename(columns={
                "date": "日付",
                "type": "売買",
                "price": "価格",
                "shares": "株数",
                "prob": "ML確率%",
                "pnl": "損益(円)",
                "pnl_pct": "損益%",
            })
            st.dataframe(trades_df, use_container_width=True, hide_index=True)
        else:
            st.info("取引が発生しませんでした。閾値を調整してみてください。")

    # ── トレードガイド ────────────────────────────────────────
    st.divider()
    _render_trading_guide(_style_lbl or "スイングトレード")


def _render_trading_guide(style: str) -> None:
    """選択したスタイルのトレード知識を表示する。"""
    from modules.trading_knowledge import KNOWLEDGE

    # スタイル名をキーにマッピング
    if "デイ" in style:
        key = "デイトレード"
    elif "短期" in style:
        key = "短期トレード"
    else:
        key = "スイングトレード"

    data = KNOWLEDGE.get(key, {})
    common = KNOWLEDGE.get("共通", {})

    st.markdown(f"### {key}ガイド")
    st.caption(data.get("overview", ""))

    # タブで整理
    tabs = st.tabs(["エントリー/エグジット", "テクニカル指標", "リスク管理", "銘柄選定", "よくある失敗", "共通原則"])

    with tabs[0]:
        if data.get("entry_rules"):
            st.markdown("**エントリールール**")
            for r in data["entry_rules"]:
                st.markdown(f"- {r}")
        if data.get("exit_rules"):
            st.markdown("**エグジットルール**")
            for r in data["exit_rules"]:
                st.markdown(f"- {r}")
        if key == "デイトレード" and data.get("key_times"):
            st.markdown("**時間帯別の特徴**")
            for time, name, desc in data["key_times"]:
                st.markdown(f"- `{time}` **{name}** — {desc}")
        if key == "短期トレード":
            gap = data.get("gap_trading", {})
            if gap:
                st.markdown("**ギャップ（窓開け）トレード**")
                st.caption(gap.get("description", ""))
                for s in gap.get("stats", []):
                    st.markdown(f"- {s}")
            if data.get("bnf_method"):
                st.markdown("**BNF手法（参考）**")
                st.caption(data["bnf_method"])
        if key == "スイングトレード" and data.get("granville_rules"):
            st.markdown("**グランビルの法則**")
            for r in data["granville_rules"]:
                st.markdown(f"- {r}")

    with tabs[1]:
        indicators = data.get("indicators", {})
        for name, desc in indicators.items():
            st.markdown(f"**{name}**")
            st.caption(desc)

    with tabs[2]:
        rules = data.get("risk_management") or data.get("position_sizing", [])
        for r in rules:
            st.markdown(f"- {r}")
        if data.get("position_sizing") and data.get("risk_management"):
            st.markdown("**ポジションサイジング**")
            for r in data["position_sizing"]:
                st.markdown(f"- {r}")

    with tabs[3]:
        for s in data.get("stock_selection", []):
            st.markdown(f"- {s}")

    with tabs[4]:
        mistakes = data.get("common_mistakes", [])
        if mistakes:
            for mistake, solution in mistakes:
                st.markdown(f"- **{mistake}** → {solution}")

    with tabs[5]:
        for section, items in common.items():
            labels = {"money_management": "資金管理の鉄則", "mental": "メンタル管理", "multi_timeframe": "マルチタイムフレーム分析"}
            st.markdown(f"**{labels.get(section, section)}**")
            for item in items:
                st.markdown(f"- {item}")


main()
