"""
市場指標

テクニカル・ファンダメンタルズ・センチメント・マクロ経済まで網羅した
全58指標をカテゴリ別に表示。チャートデータが取得可能な指標はリアルタイム表示。
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.market_context import (
    INDICATORS,
    calc_derived_indicators,
    fetch_buffett_indicator,
    fetch_cape_ratio,
    fetch_indicator_history,
    fetch_fred_indicators,
    fetch_fred_series_history,
    fetch_market_snapshot,
)
from modules.market_hours import market_status_label
from modules.styles import BG_BASE, BG_PANEL, GRID_COLOR, TEXT_MUTED, apply_theme

from modules.loading import helix_spinner
apply_theme()

# ─── Plotly 共通設定 ──────────────────────────────────────────────────
_PLOTLY_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "staticPlot": True,
}

# ─── スパークラインチャート生成 ────────────────────────────────────────

def _make_chart(df, title: str = "", color: str = "#4caf50") -> go.Figure:
    """指標のローソク足チャートを生成する。OHLCがなければラインで表示。"""
    fig = go.Figure()
    has_ohlc = all(c in df.columns for c in ["Open", "High", "Low", "Close"])

    if has_ohlc:
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"],
            increasing_line_color="#5ca08b",
            decreasing_line_color="#c45c5c",
            increasing_fillcolor="#5ca08b",
            decreasing_fillcolor="#c45c5c",
            showlegend=False,
        ))
        # SMA25
        if len(df) >= 25:
            sma = df["Close"].rolling(25).mean()
            fig.add_trace(go.Scatter(
                x=df.index, y=sma,
                mode="lines",
                line=dict(color="#d4af37", width=1),
                name="SMA25",
                showlegend=False,
            ))
    else:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            mode="lines",
            line=dict(color=color, width=1.5),
            fill="tozeroy",
            fillcolor=f"rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.08)",
            hovertemplate="%{x|%Y-%m-%d}: %{y:,.2f}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color=TEXT_MUTED)),
        margin=dict(l=40, r=10, t=30, b=20),
        height=220,
        xaxis=dict(showgrid=False, rangeslider_visible=False,
                   tickfont=dict(size=9, color=TEXT_MUTED),
                   tickformat="%Y/%m/%d" if len(df) <= 90 else "%Y/%m"),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickfont=dict(size=9, color=TEXT_MUTED)),
        plot_bgcolor=BG_BASE,
        paper_bgcolor=BG_PANEL,
        font=dict(family="'IBM Plex Mono', 'Inter', monospace", color=TEXT_MUTED, size=10),
    )
    return fig


def _make_sparkline(df, color: str = "#5ca08b") -> go.Figure:
    """サマリー行用の極小スパークラインチャート。"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        mode="lines",
        line=dict(color=color, width=1),
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.06)",
        hoverinfo="skip",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=60,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _render_live_indicator(name: str, data: dict, period: str) -> None:
    """ライブデータ付き指標カードを描画する。"""
    value      = data["value"]
    change_pct = data["change_pct"]
    unit       = data.get("unit", "")
    desc       = data.get("description", "")
    ticker     = data.get("ticker", "")
    color      = "#4caf50" if change_pct >= 0 else "#f44336"

    # 値のフォーマット
    if unit == "%":
        val_str = f"{value:.2f}%"
    elif value >= 10000:
        val_str = f"{value:,.0f}"
    elif value >= 100:
        val_str = f"{value:,.1f}"
    else:
        val_str = f"{value:,.2f}"

    if unit and unit != "%":
        val_str = f"{val_str} {unit}"

    st.metric(name, val_str, f"{change_pct:+.2f}%")

    if ticker:
        with helix_spinner("チャート読込中..."):
            df = fetch_indicator_history(ticker, period)
        if df is not None and not df.empty:
            fig = _make_chart(df, color=color)
            st.plotly_chart(fig, use_container_width=True,
                           config=_PLOTLY_CONFIG,
                           key=f"ind_{name}_{ticker}_{period}")
        else:
            st.caption("チャートデータを取得できませんでした")

    if desc:
        st.caption(desc)



# ─── メイン ─────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown("<h1 style='font-family:Cormorant Garamond,serif; font-weight:300; letter-spacing:0.12em; font-size:1.6rem;'>市場指標</h1>", unsafe_allow_html=True)
    st.caption("テクニカル・センチメント・マクロ経済まで網羅した全58指標ガイド")

    with helix_spinner("市場データを取得中..."):
        snapshot = fetch_market_snapshot()
        derived  = calc_derived_indicators(snapshot)

    if not snapshot:
        st.error("市場データの取得に失敗しました。しばらく経ってから再試行してください。")
        return

    # ─── サマリー行（メトリクス + ミニチャート）────────────────
    summary_items = [
        ("VIX", "VIX（恐怖指数）", lambda v: f"{v:.1f}", "inverse"),
        ("ドル円", "ドル円（USD/JPY）", lambda v: f"¥{v:.1f}", "normal"),
        ("Gold", "金（Gold）", lambda v: f"${v:,.0f}", "normal"),
        ("WTI", "WTI原油", lambda v: f"${v:.1f}", "normal"),
        ("S&P500", "S&P 500", lambda v: f"{v:,.0f}", "normal"),
        ("日経平均", "日経平均", lambda v: f"¥{v:,.0f}", "normal"),
    ]
    cols = st.columns(len(summary_items))
    for col, (label, key, fmt, delta_color) in zip(cols, summary_items):
        data = snapshot.get(key)
        if data:
            col.metric(label, fmt(data["value"]), f"{data['change_pct']:+.1f}%",
                       delta_color=delta_color)
            ticker = data.get("ticker", "")
            if ticker:
                df = fetch_indicator_history(ticker, "3mo")
                if df is not None and not df.empty:
                    color = "#5ca08b" if data["change_pct"] >= 0 else "#c45c5c"
                    fig = _make_sparkline(df, color)
                    col.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG, key=f"sum_{key}")

    # ─── ウィークエンドCFD（サンデーダウ・日経）────────────────
    from modules.market_context import fetch_weekend_cfd
    _weekend = fetch_weekend_cfd()
    if _weekend:
        st.divider()
        _wcols = st.columns(len(_weekend))
        for _wcol, (_wname, _wdata) in zip(_wcols, _weekend.items()):
            _ref_data = snapshot.get(_wdata.get("ref_name", ""))
            _gap_text = ""
            if _ref_data:
                _gap_pct = (_wdata["value"] - _ref_data["value"]) / _ref_data["value"] * 100
                _gap_text = f"金曜比{_gap_pct:+.2f}%"
            _wcol.metric(
                _wname,
                f"{_wdata['value']:,.0f}",
                f"{_wdata['change_pct']:+.2f}%　{_gap_text}",
                delta_color="normal",
            )
            _wcol.caption(_wdata.get("description", ""))

    st.divider()

    # ─── チャート期間選択 ────────────────────────────────────
    with st.sidebar:
        st.header("表示設定")
        period = st.select_slider(
            "チャート期間",
            options=["1mo", "3mo", "6mo", "1y", "2y"],
            value="6mo",
            format_func=lambda x: {"1mo": "1ヶ月", "3mo": "3ヶ月", "6mo": "6ヶ月", "1y": "1年", "2y": "2年"}[x],
        )
        st.divider()
        st.markdown(market_status_label(), unsafe_allow_html=True)

    # ─── カテゴリタブ ────────────────────────────────────────
    tab_names = [
        "🧠 センチメント",
        "🏭 セクター",
        "💰 債券・金利",
        "🏛️ マクロ経済",
        "🛢️ コモディティ・為替",
        "₿ 仮想通貨",
        "📐 バリュエーション",
    ]
    tabs = st.tabs(tab_names)

    # ── 1. センチメント ───────────────────────────────────────
    with tabs[0]:
        st.subheader("センチメント指標")
        # ライブデータ
        cols = st.columns(2)
        for name in ["VIX（恐怖指数）", "SKEW指数"]:
            data = snapshot.get(name)
            if data:
                with cols[0] if "VIX" in name else cols[1]:
                    with st.container(border=True):
                        _render_live_indicator(name, data, period)
        # VIX解釈
        vi = derived.get("VIX解釈")
        if vi:
            signal = vi.get("signal", "")
            color_map = {"extreme_fear": "🔴", "fear": "🟠", "neutral": "⚪", "greed": "🟢"}
            st.markdown(f"**VIX 判定:** {color_map.get(signal, '')} {vi['label']}（{vi['value']:.1f}）")
        # 実現ボラティリティ
        hv = derived.get("日経HV20")
        if hv:
            st.metric("日経HV20（実現ボラティリティ）", f"{hv['value']:.1f}%")

    # ── 2. セクター ───────────────────────────────────────────
    with tabs[1]:
        st.subheader("セクター・テーマ指標")
        sector_names = ["SOX（半導体指数）", "ダウ輸送株平均", "ラッセル2000"]
        cols = st.columns(2)
        col_idx = 0
        for name in sector_names:
            data = snapshot.get(name)
            if data:
                with cols[col_idx % 2]:
                    with st.container(border=True):
                        _render_live_indicator(name, data, period)
                col_idx += 1

    # ── 3. 債券・金利 ─────────────────────────────────────────
    with tabs[2]:
        st.subheader("債券・金利指標")
        # 長短金利差（派生指標）
        yc = derived.get("長短金利差（10Y-13W）")
        if yc:
            yc_color = "#f44336" if yc["value"] < 0 else "#4caf50"
            st.markdown(
                f"**イールドカーブ:** <span style='color:{yc_color};font-size:1.2em'>"
                f"{yc['value']:+.3f}% （{yc['label']}）</span>",
                unsafe_allow_html=True,
            )
            if yc["value"] < 0:
                st.warning("⚠️ 逆イールド発生中 — 歴史的に12〜18ヶ月後の景気後退確率が上昇します。")

        bond_names = ["米10年債利回り", "米5年債利回り", "米30年債利回り", "米13週T-Bill"]
        cols = st.columns(2)
        col_idx = 0
        for name in bond_names:
            data = snapshot.get(name)
            if data:
                with cols[col_idx % 2]:
                    with st.container(border=True):
                        _render_live_indicator(name, data, period)
                col_idx += 1
        # FRED: ハイイールドスプレッド
        _fred = fetch_fred_indicators()
        _hy = _fred.get("ハイイールドスプレッド")
        if _hy:
            st.divider()
            with st.container(border=True):
                st.metric("ハイイールドスプレッド（FRED）", f"{_hy['value']}%", help=_hy["description"])
                st.caption(f"データ日: {_hy['date']}　※{_hy['description']}")
                _hy_hist = fetch_fred_series_history("BAMLH0A0HYM2", 252)
                if _hy_hist is not None:
                    fig = _make_chart(pd.DataFrame({"Close": _hy_hist}), color="#ff9800")
                    st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG, key="fred_hy_spread")

    # ── 4. マクロ経済 ─────────────────────────────────────────
    with tabs[3]:
        st.subheader("マクロ経済・先行指標")

        _fred = fetch_fred_indicators()
        if _fred:
            # FREDデータをカードで表示
            _fred_items = list(_fred.items())
            # ハイイールドスプレッドは債券タブに表示済みなので除外
            _fred_items = [(n, d) for n, d in _fred_items if n != "ハイイールドスプレッド"]

            cols = st.columns(2)
            for i, (name, info) in enumerate(_fred_items):
                with cols[i % 2]:
                    with st.container(border=True):
                        val = info["value"]
                        unit = info.get("unit", "")
                        st.metric(name, f"{val}{unit}")
                        st.caption(f"{info['description']}　（{info['date']}）")
                        # チャート表示
                        sid = info.get("series_id")
                        if sid:
                            hist = fetch_fred_series_history(sid, 60)
                            if hist is not None:
                                fig = _make_chart(pd.DataFrame({"Close": hist}), color="#4caf50")
                                st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG, key=f"fred_{sid}")
        else:
            st.warning(
                "FRED APIキーが設定されていません。マクロ経済指標を表示するには:\n\n"
                "1. https://fred.stlouisfed.org でアカウント作成\n"
                "2. https://fredaccount.stlouisfed.org/apikeys でAPIキー取得\n"
                "3. secrets.toml に `FRED_API_KEY = \"あなたのキー\"` を追加"
            )

    # ── 5. コモディティ・為替 ─────────────────────────────────
    with tabs[4]:
        st.subheader("コモディティ・為替指標")
        commodity_fx = ["金（Gold）", "WTI原油", "銅（Copper）", "ドルインデックス", "ドル円（USD/JPY）", "ユーロドル"]
        cols = st.columns(2)
        col_idx = 0
        for name in commodity_fx:
            data = snapshot.get(name)
            if data:
                with cols[col_idx % 2]:
                    with st.container(border=True):
                        _render_live_indicator(name, data, period)
                col_idx += 1

    # ── 6. 仮想通貨 ─────────────────────────────────────────
    with tabs[5]:
        st.subheader("仮想通貨")
        _crypto_list = ["ビットコイン（BTC）", "イーサリアム（ETH）", "リップル（XRP）", "ソラナ（SOL）"]
        _crypto_cols = st.columns(2)
        for _ci, _cname in enumerate(_crypto_list):
            _cd = snapshot.get(_cname)
            if _cd:
                with _crypto_cols[_ci % 2]:
                    with st.container(border=True):
                        _chg_color = "normal" if _cd["change_pct"] >= 0 else "inverse"
                        st.metric(_cname, f"${_cd['value']:,.1f}", f"{_cd['change_pct']:+.1f}%",
                                  delta_color=_chg_color)
                        st.caption(_cd.get("description", ""))
                        _cticker = _cd.get("ticker", "")
                        if _cticker:
                            _cdf = fetch_indicator_history(_cticker, period)
                            if _cdf is not None and not _cdf.empty:
                                _ccolor = "#5ca08b" if _cd["change_pct"] >= 0 else "#c45c5c"
                                _cfig = _make_chart(_cdf, color=_ccolor)
                                st.plotly_chart(_cfig, use_container_width=True,
                                               config=_PLOTLY_CONFIG,
                                               key=f"crypto_{_cname}")

    # ── 7. バリュエーション ──────────────────────────────────
    with tabs[6]:
        st.subheader("バリュエーション・市場全体指標")

        vc1, vc2 = st.columns(2)

        # NT倍率
        nt = derived.get("NT倍率")
        if nt:
            with vc1:
                with st.container(border=True):
                    st.metric("NT倍率", f"{nt['value']:.2f} 倍")
                    st.caption("日経225÷TOPIX。14倍超で日経優位、13倍以下でTOPIX優位")
                    # 日経とTOPIXのチャートを重ねて表示
                    nk = snapshot.get("日経平均")
                    if nk and nk.get("ticker"):
                        df_nk = fetch_indicator_history(nk["ticker"], period)
                        if df_nk is not None and not df_nk.empty:
                            fig = _make_chart(df_nk, title="日経平均", color="#d4af37")
                            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG, key="val_nk225")

        # イールドスプレッド
        tnx_data = snapshot.get("米10年債利回り", {})
        sp500_data = snapshot.get("S&P 500", {})
        if tnx_data.get("value") and sp500_data.get("value"):
            earnings_yield = 100 / 22
            eq_spread = round(earnings_yield - tnx_data["value"], 2)
            with vc2:
                with st.container(border=True):
                    st.metric("益回りスプレッド", f"{eq_spread:+.2f}%")
                    st.caption("株式益回り - 米10年債。プラスで株式有利、マイナスで債券有利")
                    if tnx_data.get("ticker"):
                        df_tnx = fetch_indicator_history(tnx_data["ticker"], period)
                        if df_tnx is not None and not df_tnx.empty:
                            fig = _make_chart(df_tnx, title="米10年債利回り", color="#ff9800")
                            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG, key="val_tnx")

        vc3, vc4 = st.columns(2)

        # CAPEレシオ
        _cape = fetch_cape_ratio()
        if _cape:
            _cape_val = _cape["value"]
            with vc3:
                with st.container(border=True):
                    _cape_color = "inverse" if _cape_val > 30 else "normal"
                    st.metric("CAPEレシオ", f"{_cape_val:.1f} 倍",
                              "割高警戒" if _cape_val > 30 else "通常範囲",
                              delta_color=_cape_color)
                    st.caption(f"シラーPER（{_cape['date']}）。25倍以上で割高圏")

        # バフェット指標
        _buffett = fetch_buffett_indicator()
        if _buffett:
            _bv = _buffett["value"]
            with vc4:
                with st.container(border=True):
                    st.metric("バフェット指標", f"{_bv:.0f}%",
                              "割高圏" if _bv > 150 else ("警戒圏" if _bv > 100 else "割安圏"),
                              delta_color="inverse" if _bv > 100 else "normal")
                    st.caption(f"時価総額/GDP（{_buffett['date']}）。100%超で割高")

        # 主要指数チャート
        st.divider()
        st.markdown("**主要指数**")
        index_names = ["日経平均", "S&P 500", "ナスダック総合", "ダウ平均"]
        cols = st.columns(2)
        col_idx = 0
        for name in index_names:
            data = snapshot.get(name)
            if data:
                with cols[col_idx % 2]:
                    with st.container(border=True):
                        _render_live_indicator(name, data, period)
                col_idx += 1


if __name__ == "__main__":
    main()
