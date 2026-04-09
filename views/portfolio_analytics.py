"""
ポートフォリオ・アナリティクス
quantstats を使ったパフォーマンス分析ページ。
保有銘柄の加重リターンを計算し、各種指標・チャートを表示する。
"""
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
try:
    import quantstats as qs
except ImportError:
    qs = None
import streamlit as st
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.styles import (
    apply_theme,
    BG_BASE,
    BG_PANEL,
    ACCENT,
    ACCENT_SUB,
    TEXT_PRIMARY,
    TEXT_MUTED,
    GRID_COLOR,
    UP_COLOR,
    DOWN_COLOR,
)
from modules.loading import helix_spinner
from modules.persistence import load_into_session

apply_theme()

if qs is None:
    st.error("quantstats ライブラリがインストールされていません。`pip install quantstats` を実行してください。")
    st.stop()

# ─── 定数 ─────────────────────────────────────────────────────────────────
NIKKEI_TICKER = "^N225"  # 日経225（ベンチマーク）
PERIODS = {"6M": 126, "1Y": 252, "2Y": 504, "3Y": 756, "5Y": 1260, "全期間": None}
_TITLE_STYLE = (
    "font-family:Cormorant Garamond,serif; font-weight:300; "
    "letter-spacing:0.12em; font-size:1.6rem;"
)
_SECTION_STYLE = (
    "font-family:Cormorant Garamond,serif; font-weight:400; "
    "letter-spacing:0.08em; font-size:1.15rem; color:#d4af37; "
    "border-bottom:1px solid rgba(212,175,55,0.15); padding-bottom:4px; "
    "margin-top:1.5rem;"
)
_METRIC_CARD = (
    "background:rgba(10,15,26,0.85); border:1px solid rgba(212,175,55,0.10); "
    "border-radius:8px; padding:14px 18px; text-align:center;"
)


# ─── データ取得 ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_returns(ticker: str, period_days: int | None) -> pd.Series | None:
    """yfinance から日次リターンを取得する。"""
    try:
        if period_days is None:
            df = yf.download(ticker, period="max", progress=False, auto_adjust=True)
        else:
            # 余裕をもって取得（休場日を考慮）
            extra = int(period_days * 1.5) + 30
            df = yf.download(
                ticker,
                period=f"{extra}d",
                progress=False,
                auto_adjust=True,
            )
        if df is None or df.empty:
            return None
        close = df["Close"].dropna()
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        returns = close.pct_change().dropna()
        # 指定期間に切り詰める
        if period_days is not None and len(returns) > period_days:
            returns = returns.iloc[-period_days:]
        returns.name = ticker
        return returns
    except Exception:
        return None


def _build_portfolio_returns(
    holdings: list[dict], period_days: int | None
) -> tuple[pd.Series | None, dict[str, float]]:
    """
    保有銘柄のリターンを加重平均してポートフォリオリターンを算出する。
    ウェイトは各銘柄の保有株数 x 直近株価（時価ベース）で計算。

    Returns:
        (portfolio_returns, weights_dict) — weights_dict はティッカー → ウェイト%
    """
    if not holdings:
        return None, {}

    # 各銘柄のリターンを取得
    ticker_returns: dict[str, pd.Series] = {}
    market_values: dict[str, float] = {}
    for h in holdings:
        code = h["code"]
        shares = h.get("shares", 100)
        ret = _fetch_returns(code, period_days)
        if ret is not None and len(ret) > 10:
            ticker_returns[code] = ret
            # 直近の株価から時価を推定
            try:
                info = yf.Ticker(code).fast_info
                price = info.get("lastPrice", 0) or info.get("previousClose", 0)
            except Exception:
                price = 0
            if price and price == price:  # NaN チェック
                market_values[code] = price * shares
            else:
                market_values[code] = shares  # 株価取得失敗時は株数をフォールバック

    if not ticker_returns:
        return None, {}

    # 時価加重ウェイトを計算
    total_mv = sum(market_values.get(t, 1) for t in ticker_returns)
    weights = {t: market_values.get(t, 1) / total_mv for t in ticker_returns}

    # 共通日付に揃える
    df = pd.DataFrame(ticker_returns)
    df = df.dropna()
    if df.empty or len(df) < 10:
        return None, {}

    # 加重平均リターン
    port_ret = pd.Series(0.0, index=df.index)
    for t, w in weights.items():
        port_ret += df[t] * w
    port_ret.name = "Portfolio"

    # ウェイトを % に変換
    weights_pct = {t: round(w * 100, 1) for t, w in weights.items()}
    return port_ret, weights_pct


def _manual_portfolio_returns(
    tickers: list[str], weights_input: list[float], period_days: int | None
) -> tuple[pd.Series | None, dict[str, float]]:
    """手動入力のティッカー＋ウェイトからポートフォリオリターンを算出する。"""
    total_w = sum(weights_input)
    if total_w <= 0:
        return None, {}
    norm_weights = [w / total_w for w in weights_input]

    ticker_returns: dict[str, pd.Series] = {}
    for t in tickers:
        ret = _fetch_returns(t, period_days)
        if ret is not None and len(ret) > 10:
            ticker_returns[t] = ret

    if not ticker_returns:
        return None, {}

    df = pd.DataFrame(ticker_returns).dropna()
    if df.empty or len(df) < 10:
        return None, {}

    port_ret = pd.Series(0.0, index=df.index)
    weights_dict: dict[str, float] = {}
    for t, w in zip(tickers, norm_weights):
        if t in df.columns:
            port_ret += df[t] * w
            weights_dict[t] = round(w * 100, 1)

    port_ret.name = "Portfolio"
    return port_ret, weights_dict


# ─── Plotly チャート共通設定 ──────────────────────────────────────────────

def _base_layout(title: str = "") -> dict:
    """全チャート共通のレイアウト設定。"""
    return dict(
        template="plotly_dark",
        paper_bgcolor=BG_BASE,
        plot_bgcolor=BG_BASE,
        font=dict(family="Inter, Noto Sans JP, sans-serif", color=TEXT_PRIMARY, size=12),
        title=dict(text=title, font=dict(size=14, color=TEXT_PRIMARY)) if title else None,
        xaxis=dict(gridcolor=GRID_COLOR, zeroline=False),
        yaxis=dict(gridcolor=GRID_COLOR, zeroline=False),
        margin=dict(l=50, r=30, t=40 if title else 20, b=40),
        hovermode="x unified",
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
    )


# ─── チャート作成関数 ─────────────────────────────────────────────────────

def _cumulative_return_chart(
    port_ret: pd.Series, bench_ret: pd.Series | None
) -> go.Figure:
    """累積リターン推移チャート。"""
    fig = go.Figure()
    cum = qs.stats.compsum(port_ret) * 100
    fig.add_trace(go.Scatter(
        x=cum.index, y=cum.values,
        name="ポートフォリオ",
        line=dict(color=ACCENT, width=2),
        hovertemplate="%{y:+.2f}%<extra></extra>",
    ))
    if bench_ret is not None and len(bench_ret) > 0:
        # ポートフォリオと同じ期間に揃える
        common = cum.index.intersection(bench_ret.index)
        if len(common) > 10:
            b = bench_ret.loc[common]
            cum_b = qs.stats.compsum(b) * 100
            fig.add_trace(go.Scatter(
                x=cum_b.index, y=cum_b.values,
                name="日経225",
                line=dict(color=TEXT_MUTED, width=1.5, dash="dot"),
                hovertemplate="%{y:+.2f}%<extra></extra>",
            ))
    layout = _base_layout()
    layout["yaxis"]["title"] = "累積リターン (%)"
    fig.update_layout(**layout)
    return fig


def _drawdown_chart(port_ret: pd.Series) -> go.Figure:
    """ドローダウン推移チャート。"""
    dd = qs.stats.to_drawdown_series(port_ret) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.values,
        fill="tozeroy",
        fillcolor="rgba(196,92,92,0.15)",
        line=dict(color=DOWN_COLOR, width=1.5),
        name="ドローダウン",
        hovertemplate="%{y:.2f}%<extra></extra>",
    ))
    layout = _base_layout()
    layout["yaxis"]["title"] = "ドローダウン (%)"
    fig.update_layout(**layout)
    return fig


def _rolling_sharpe_chart(port_ret: pd.Series, window: int = 126) -> go.Figure:
    """ローリング・シャープレシオ（6ヶ月窓）。"""
    rs = qs.stats.rolling_sharpe(port_ret, rolling_period=window)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rs.index, y=rs.values,
        line=dict(color=ACCENT_SUB, width=1.5),
        name=f"Sharpe ({window}日)",
        hovertemplate="%{y:.2f}<extra></extra>",
    ))
    # ゼロライン
    fig.add_hline(y=0, line_dash="dash", line_color=TEXT_MUTED, line_width=0.8)
    fig.add_hline(y=1, line_dash="dot", line_color="rgba(212,175,55,0.3)", line_width=0.8,
                  annotation_text="1.0", annotation_position="bottom right",
                  annotation_font=dict(size=10, color=TEXT_MUTED))
    layout = _base_layout()
    layout["yaxis"]["title"] = "シャープレシオ"
    fig.update_layout(**layout)
    return fig


def _rolling_volatility_chart(port_ret: pd.Series, window: int = 63) -> go.Figure:
    """ローリング・ボラティリティ（3ヶ月窓）。"""
    rv = qs.stats.rolling_volatility(port_ret, rolling_period=window)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rv.index, y=rv.values * 100,
        line=dict(color="#e07c5a", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(224,124,90,0.08)",
        name=f"Vol ({window}日)",
        hovertemplate="%{y:.1f}%<extra></extra>",
    ))
    layout = _base_layout()
    layout["yaxis"]["title"] = "年率ボラティリティ (%)"
    fig.update_layout(**layout)
    return fig


def _monthly_heatmap(port_ret: pd.Series) -> go.Figure:
    """月次リターン・ヒートマップ。"""
    mtable = qs.stats.monthly_returns(port_ret, eoy=True, compounded=True)
    if mtable is None or mtable.empty:
        return go.Figure()

    # 列名を日本語月名に変換
    month_map = {
        "Jan": "1月", "Feb": "2月", "Mar": "3月", "Apr": "4月",
        "May": "5月", "Jun": "6月", "Jul": "7月", "Aug": "8月",
        "Sep": "9月", "Oct": "10月", "Nov": "11月", "Dec": "12月",
        "EOY": "年間",
    }
    cols = [month_map.get(str(c), str(c)) for c in mtable.columns]
    # 値を % に変換
    z = mtable.values * 100

    # カスタムテキスト（各セルに % 表示）
    text = [[f"{v:+.1f}%" if not np.isnan(v) else "" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=cols,
        y=[str(y) for y in mtable.index],
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=10),
        colorscale=[
            [0.0, DOWN_COLOR],
            [0.5, BG_PANEL],
            [1.0, UP_COLOR],
        ],
        zmid=0,
        showscale=True,
        colorbar=dict(
            title="リターン(%)",
            titlefont=dict(size=10),
            tickfont=dict(size=9),
            len=0.6,
        ),
        hovertemplate="年=%{y} 月=%{x}<br>リターン=%{text}<extra></extra>",
    ))
    layout = _base_layout()
    layout["yaxis"]["autorange"] = "reversed"
    layout["yaxis"]["dtick"] = 1
    layout["xaxis"]["side"] = "top"
    layout["margin"] = dict(l=50, r=30, t=50, b=20)
    fig.update_layout(**layout, height=max(200, len(mtable) * 32 + 80))
    return fig


def _weight_pie(weights: dict[str, float], holdings: list[dict]) -> go.Figure:
    """ポートフォリオ構成比の円グラフ。"""
    # 銘柄名を取得
    name_map = {h["code"]: h.get("name", h["code"]) for h in holdings}
    labels = [f"{name_map.get(t, t)}<br>({t})" for t in weights]
    values = list(weights.values())

    # ゴールド系のカラーパレット
    colors = [
        "#d4af37", "#8fb8a0", "#5ca08b", "#c45c5c", "#e07c5a",
        "#7b9ec4", "#b8a9c9", "#e6c34d", "#6b9e8a", "#d48f6e",
        "#9ab3d4", "#c9b8d4", "#a3c9a8", "#d4c48f", "#8fc4b8",
    ]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker=dict(colors=colors[:len(labels)]),
        textinfo="label+percent",
        textfont=dict(size=10, color=TEXT_PRIMARY),
        hovertemplate="%{label}<br>ウェイト: %{percent}<extra></extra>",
    ))
    layout = _base_layout()
    layout["showlegend"] = False
    layout["margin"] = dict(l=20, r=20, t=20, b=20)
    fig.update_layout(**layout, height=340)
    return fig


# ─── 指標カード表示 ───────────────────────────────────────────────────────

def _metric_html(label: str, value: str, color: str = TEXT_PRIMARY) -> str:
    """1つの指標カードの HTML を返す。"""
    return (
        f'<div style="{_METRIC_CARD}">'
        f'<div style="font-size:0.72em; color:{TEXT_MUTED}; '
        f'font-family:Inter,Noto Sans JP,sans-serif; margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:1.3em; font-weight:600; color:{color}; '
        f'font-family:IBM Plex Mono,monospace;">{value}</div>'
        f'</div>'
    )


def _format_pct(val: float, with_sign: bool = True) -> tuple[str, str]:
    """パーセント値をフォーマットし、色を決定する。"""
    if val != val:  # NaN
        return "N/A", TEXT_MUTED
    color = UP_COLOR if val >= 0 else DOWN_COLOR
    s = f"{val:+.2f}%" if with_sign else f"{val:.2f}%"
    return s, color


def _format_ratio(val: float) -> tuple[str, str]:
    """レシオ値をフォーマットする。"""
    if val != val:
        return "N/A", TEXT_MUTED
    color = UP_COLOR if val >= 0 else DOWN_COLOR
    return f"{val:.3f}", color


# ─── メインページ ─────────────────────────────────────────────────────────

st.markdown(
    f"<h1 style='{_TITLE_STYLE}'>ポートフォリオ・アナリティクス</h1>",
    unsafe_allow_html=True,
)

# ─── セッションステート初期化 ─────────────────────────────────────────
load_into_session("portfolio_holdings", "portfolio_holdings", default=[])

# ─── 入力モード選択 ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"<h3 style='font-family:Cormorant Garamond,serif; font-weight:400; "
        f"color:{ACCENT};'>分析設定</h3>",
        unsafe_allow_html=True,
    )
    input_mode = st.radio(
        "データソース",
        ["保有銘柄から", "手動入力"],
        horizontal=True,
        key="pa_input_mode",
    )
    period_label = st.selectbox(
        "分析期間",
        list(PERIODS.keys()),
        index=1,  # デフォルト 1Y
        key="pa_period",
    )
    period_days = PERIODS[period_label]

holdings_for_chart: list[dict] = []
manual_tickers: list[str] = []
manual_weights: list[float] = []

if input_mode == "保有銘柄から":
    holdings = st.session_state.get("portfolio_holdings", [])
    if not holdings:
        st.info(
            "保有銘柄が登録されていません。「ポートフォリオ」ページで銘柄を追加するか、"
            "下のサイドバーで「手動入力」を選択してください。"
        )
        st.stop()
    holdings_for_chart = holdings
else:
    # 手動入力フォーム
    with st.sidebar:
        st.caption("ティッカーとウェイトを入力してください（.T は自動付与）")
        n_stocks = st.number_input("銘柄数", min_value=1, max_value=20, value=3, key="pa_n")
        for i in range(int(n_stocks)):
            c1, c2 = st.columns([2, 1])
            with c1:
                t = st.text_input(f"銘柄{i+1}", key=f"pa_t_{i}", placeholder="7203")
            with c2:
                w = st.number_input(f"W{i+1}", min_value=0.0, value=1.0, step=0.1, key=f"pa_w_{i}")
            if t:
                t = t.strip()
                if not t.endswith(".T") and not t.startswith("^"):
                    t = f"{t}.T"
                manual_tickers.append(t)
                manual_weights.append(w)

    if not manual_tickers:
        st.info("サイドバーで銘柄を入力してください。")
        st.stop()

# ─── データ取得・計算 ─────────────────────────────────────────────────
with helix_spinner("リターンデータを取得中..."):
    if input_mode == "保有銘柄から":
        port_ret, weights = _build_portfolio_returns(holdings_for_chart, period_days)
    else:
        port_ret, weights = _manual_portfolio_returns(manual_tickers, manual_weights, period_days)
        # 手動入力用のダミー holdings を作成（円グラフ表示用）
        holdings_for_chart = [{"code": t, "name": t} for t in manual_tickers]

    # ベンチマーク（日経225）
    bench_ret = _fetch_returns(NIKKEI_TICKER, period_days)

if port_ret is None or len(port_ret) < 10:
    st.error("十分なリターンデータを取得できませんでした。銘柄コードや期間を確認してください。")
    st.stop()

# ─── 指標計算 ─────────────────────────────────────────────────────────
total_return = float(qs.stats.comp(port_ret)) * 100
cagr = float(qs.stats.cagr(port_ret, periods=252)) * 100
sharpe = float(qs.stats.sharpe(port_ret, periods=252))
sortino = float(qs.stats.sortino(port_ret, periods=252))
max_dd = float(qs.stats.max_drawdown(port_ret)) * 100
volatility = float(qs.stats.volatility(port_ret, periods=252)) * 100
calmar = float(qs.stats.calmar(port_ret, periods=252))
var_95 = float(qs.stats.value_at_risk(port_ret, confidence=0.95)) * 100
win_rate = float(qs.stats.win_rate(port_ret)) * 100
best_day = float(qs.stats.best(port_ret)) * 100
worst_day = float(qs.stats.worst(port_ret)) * 100

# ベンチマーク指標
bench_total = bench_sharpe = bench_cagr = float("nan")
if bench_ret is not None and len(bench_ret) > 10:
    common_idx = port_ret.index.intersection(bench_ret.index)
    if len(common_idx) > 10:
        bench_aligned = bench_ret.loc[common_idx]
        bench_total = float(qs.stats.comp(bench_aligned)) * 100
        bench_sharpe = float(qs.stats.sharpe(bench_aligned, periods=252))
        bench_cagr = float(qs.stats.cagr(bench_aligned, periods=252)) * 100

# ─── 構成比 & サマリー ───────────────────────────────────────────────
col_pie, col_metrics = st.columns([1, 2])

with col_pie:
    st.markdown(f"<h3 style='{_SECTION_STYLE}'>構成比</h3>", unsafe_allow_html=True)
    if weights:
        fig_pie = _weight_pie(weights, holdings_for_chart)
        st.plotly_chart(fig_pie, use_container_width=True, key="pa_pie")
    else:
        st.caption("構成データなし")

with col_metrics:
    st.markdown(f"<h3 style='{_SECTION_STYLE}'>パフォーマンス・サマリー</h3>", unsafe_allow_html=True)

    # 1段目: メイン指標
    m1, m2, m3, m4 = st.columns(4)
    tr_s, tr_c = _format_pct(total_return)
    cagr_s, cagr_c = _format_pct(cagr)
    sh_s, sh_c = _format_ratio(sharpe)
    so_s, so_c = _format_ratio(sortino)
    with m1:
        st.markdown(_metric_html("トータルリターン", tr_s, tr_c), unsafe_allow_html=True)
    with m2:
        st.markdown(_metric_html("CAGR", cagr_s, cagr_c), unsafe_allow_html=True)
    with m3:
        st.markdown(_metric_html("シャープレシオ", sh_s, sh_c), unsafe_allow_html=True)
    with m4:
        st.markdown(_metric_html("ソルティノレシオ", so_s, so_c), unsafe_allow_html=True)

    # 2段目: リスク指標
    r1, r2, r3, r4 = st.columns(4)
    dd_s, dd_c = _format_pct(max_dd)
    vol_s, _ = _format_pct(volatility, with_sign=False)
    cal_s, cal_c = _format_ratio(calmar)
    var_s, var_c = _format_pct(var_95)
    with r1:
        st.markdown(_metric_html("最大ドローダウン", dd_s, dd_c), unsafe_allow_html=True)
    with r2:
        st.markdown(_metric_html("年率ボラティリティ", vol_s, TEXT_PRIMARY), unsafe_allow_html=True)
    with r3:
        st.markdown(_metric_html("カルマーレシオ", cal_s, cal_c), unsafe_allow_html=True)
    with r4:
        st.markdown(_metric_html("VaR (95%)", var_s, var_c), unsafe_allow_html=True)

    # 3段目: 追加情報
    e1, e2, e3, e4 = st.columns(4)
    wr_s = f"{win_rate:.1f}%"
    bd_s, bd_c = _format_pct(best_day)
    wd_s, wd_c = _format_pct(worst_day)
    days_s = f"{len(port_ret)}"
    with e1:
        st.markdown(_metric_html("勝率", wr_s, ACCENT_SUB), unsafe_allow_html=True)
    with e2:
        st.markdown(_metric_html("ベストデイ", bd_s, bd_c), unsafe_allow_html=True)
    with e3:
        st.markdown(_metric_html("ワーストデイ", wd_s, wd_c), unsafe_allow_html=True)
    with e4:
        st.markdown(_metric_html("取引日数", days_s, TEXT_PRIMARY), unsafe_allow_html=True)

# ─── ベンチマーク比較 ─────────────────────────────────────────────────
if bench_total == bench_total:  # NaN チェック
    st.markdown(f"<h3 style='{_SECTION_STYLE}'>vs 日経225</h3>", unsafe_allow_html=True)
    b1, b2, b3, b4 = st.columns(4)
    bt_s, bt_c = _format_pct(bench_total)
    bc_s, bc_c = _format_pct(bench_cagr)
    bs_s, bs_c = _format_ratio(bench_sharpe)
    # 超過リターン
    excess = total_return - bench_total
    ex_s, ex_c = _format_pct(excess)
    with b1:
        st.markdown(_metric_html("日経225 リターン", bt_s, bt_c), unsafe_allow_html=True)
    with b2:
        st.markdown(_metric_html("日経225 CAGR", bc_s, bc_c), unsafe_allow_html=True)
    with b3:
        st.markdown(_metric_html("日経225 Sharpe", bs_s, bs_c), unsafe_allow_html=True)
    with b4:
        st.markdown(_metric_html("超過リターン", ex_s, ex_c), unsafe_allow_html=True)

# ─── チャートセクション ──────────────────────────────────────────────

# 累積リターン
st.markdown(f"<h3 style='{_SECTION_STYLE}'>累積リターン推移</h3>", unsafe_allow_html=True)
fig_cum = _cumulative_return_chart(port_ret, bench_ret)
st.plotly_chart(fig_cum, use_container_width=True, key="pa_cum")

# ドローダウン & ローリングシャープ（2列）
col_dd, col_rs = st.columns(2)
with col_dd:
    st.markdown(f"<h3 style='{_SECTION_STYLE}'>ドローダウン推移</h3>", unsafe_allow_html=True)
    fig_dd = _drawdown_chart(port_ret)
    st.plotly_chart(fig_dd, use_container_width=True, key="pa_dd")

with col_rs:
    st.markdown(f"<h3 style='{_SECTION_STYLE}'>ローリング・シャープレシオ</h3>", unsafe_allow_html=True)
    fig_rs = _rolling_sharpe_chart(port_ret)
    st.plotly_chart(fig_rs, use_container_width=True, key="pa_rs")

# ローリング・ボラティリティ
st.markdown(f"<h3 style='{_SECTION_STYLE}'>ローリング・ボラティリティ</h3>", unsafe_allow_html=True)
fig_vol = _rolling_volatility_chart(port_ret)
st.plotly_chart(fig_vol, use_container_width=True, key="pa_vol")

# 月次リターン・ヒートマップ
st.markdown(f"<h3 style='{_SECTION_STYLE}'>月次リターン・ヒートマップ</h3>", unsafe_allow_html=True)
fig_hm = _monthly_heatmap(port_ret)
if fig_hm.data:
    st.plotly_chart(fig_hm, use_container_width=True, key="pa_hm")
else:
    st.caption("月次リターンの計算に十分なデータがありません。")

# ─── ドローダウン詳細テーブル ─────────────────────────────────────────
st.markdown(f"<h3 style='{_SECTION_STYLE}'>ドローダウン詳細（上位5件）</h3>", unsafe_allow_html=True)
try:
    dd_series = qs.stats.to_drawdown_series(port_ret)
    dd_details = qs.stats.drawdown_details(dd_series)
    if dd_details is not None and not dd_details.empty:
        # 上位5件を表示
        top5 = dd_details.sort_values("max drawdown").head(5).reset_index(drop=True)
        # カラム名を日本語化
        display_df = pd.DataFrame({
            "開始日": top5["start"].dt.strftime("%Y-%m-%d") if "start" in top5 else "",
            "底値日": top5["valley"].dt.strftime("%Y-%m-%d") if "valley" in top5 else "",
            "回復日": top5["end"].apply(
                lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "未回復"
            ) if "end" in top5 else "",
            "最大DD": top5["max drawdown"].apply(lambda x: f"{x*100:.2f}%"),
            "日数": top5["days"].astype(int) if "days" in top5 else 0,
        })
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("ドローダウン詳細を計算できませんでした。")
except Exception:
    st.caption("ドローダウン詳細を計算できませんでした。")

# ─── 個別銘柄リターン比較 ─────────────────────────────────────────────
if len(weights) > 1:
    st.markdown(f"<h3 style='{_SECTION_STYLE}'>個別銘柄リターン比較</h3>", unsafe_allow_html=True)
    name_map = {h["code"]: h.get("name", h["code"]) for h in holdings_for_chart}

    fig_ind = go.Figure()
    for t in weights:
        r = _fetch_returns(t, period_days)
        if r is not None and len(r) > 10:
            cum = qs.stats.compsum(r) * 100
            label = name_map.get(t, t)
            fig_ind.add_trace(go.Scatter(
                x=cum.index, y=cum.values,
                name=f"{label} ({t})",
                line=dict(width=1.5),
                hovertemplate="%{y:+.2f}%<extra></extra>",
            ))
    layout = _base_layout()
    layout["yaxis"]["title"] = "累積リターン (%)"
    fig_ind.update_layout(**layout)
    st.plotly_chart(fig_ind, use_container_width=True, key="pa_ind")
