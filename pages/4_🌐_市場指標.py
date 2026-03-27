"""
市場指標ダッシュボード

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

apply_theme()



# ─── スパークラインチャート生成 ────────────────────────────────────────

def _make_chart(df, title: str = "", color: str = "#4caf50") -> go.Figure:
    """指標のラインチャートを生成する。"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"],
        mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.08)",
        hovertemplate="%{x|%Y-%m-%d}: %{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color=TEXT_MUTED)),
        margin=dict(l=40, r=10, t=30, b=20),
        height=180,
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=TEXT_MUTED)),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickfont=dict(size=9, color=TEXT_MUTED)),
        plot_bgcolor=BG_BASE,
        paper_bgcolor=BG_PANEL,
        font=dict(family="'IBM Plex Mono', 'Inter', monospace", color=TEXT_MUTED, size=10),
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
        with st.spinner("チャート読込中..."):
            df = fetch_indicator_history(ticker, period)
        if df is not None and not df.empty:
            fig = _make_chart(df, color=color)
            st.plotly_chart(fig, use_container_width=True,
                           key=f"ind_{name}_{ticker}_{period}")
        else:
            st.caption("チャートデータを取得できませんでした")

    if desc:
        st.caption(desc)



# ─── メイン ─────────────────────────────────────────────────────────────

def main() -> None:
    st.title("🌐 市場指標ダッシュボード")
    st.caption("テクニカル・センチメント・マクロ経済まで網羅した全58指標ガイド")

    with st.spinner("市場データを取得中..."):
        snapshot = fetch_market_snapshot()
        derived  = calc_derived_indicators(snapshot)

    if not snapshot:
        st.error("市場データの取得に失敗しました。しばらく経ってから再試行してください。")
        return

    # ─── サマリー行 ──────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    vix = snapshot.get("VIX（恐怖指数）")
    if vix:
        vix_label = derived.get("VIX解釈", {}).get("label", "")
        c1.metric("VIX", f"{vix['value']:.1f}", f"{vix['change_pct']:+.1f}%",
                  delta_color="inverse")
        c1.caption(f"恐怖指数: {vix_label}")

    yc = derived.get("長短金利差（10Y-13W）")
    if yc:
        c2.metric("長短金利差", f"{yc['value']:+.3f}%")
        c2.caption(yc["label"])

    nt = derived.get("NT倍率")
    if nt:
        c3.metric("NT倍率", f"{nt['value']:.2f}")

    usdjpy = snapshot.get("ドル円（USD/JPY）")
    if usdjpy:
        c4.metric("ドル円", f"¥{usdjpy['value']:.1f}", f"{usdjpy['change_pct']:+.1f}%")

    gold = snapshot.get("金（Gold）")
    if gold:
        c5.metric("Gold", f"${gold['value']:,.0f}", f"{gold['change_pct']:+.1f}%")

    oil = snapshot.get("WTI原油")
    if oil:
        c6.metric("WTI", f"${oil['value']:.1f}", f"{oil['change_pct']:+.1f}%")

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
        st.caption(market_status_label())

    # ─── カテゴリタブ ────────────────────────────────────────
    tab_names = [
        "🧠 センチメント",
        "🏭 セクター",
        "💰 債券・金利",
        "🏛️ マクロ経済",
        "🛢️ コモディティ・為替",
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
                    st.plotly_chart(fig, use_container_width=True, key="fred_hy_spread")

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
                                st.plotly_chart(fig, use_container_width=True, key=f"fred_{sid}")
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

    # ── 6. バリュエーション ──────────────────────────────────
    with tabs[5]:
        st.subheader("バリュエーション・市場全体指標")

        _vc1, _vc2, _vc3, _vc4 = st.columns(4)

        # NT倍率
        nt = derived.get("NT倍率")
        if nt:
            _vc1.metric("NT倍率", f"{nt['value']:.2f} 倍")
            _vc1.caption("日経225÷TOPIX")

        # イールドスプレッド
        tnx = snapshot.get("米10年債利回り", {}).get("value")
        sp500 = snapshot.get("S&P 500", {}).get("value")
        if tnx and sp500:
            earnings_yield = 100 / 22
            eq_spread = round(earnings_yield - tnx, 2)
            _vc2.metric("益回りスプレッド", f"{eq_spread:+.2f}%")
            _vc2.caption("株式益回り - 米10年債")

        # CAPEレシオ
        _cape = fetch_cape_ratio()
        if _cape:
            _cape_val = _cape["value"]
            _cape_color = "inverse" if _cape_val > 30 else "normal"
            _vc3.metric("CAPEレシオ", f"{_cape_val:.1f} 倍",
                        "割高警戒" if _cape_val > 30 else "通常範囲",
                        delta_color=_cape_color)
            _vc3.caption(f"シラーPER（{_cape['date']}）")

        # バフェット指標
        _buffett = fetch_buffett_indicator()
        if _buffett:
            _bv = _buffett["value"]
            _vc4.metric("バフェット指標", f"{_bv:.0f}%",
                        "割高圏" if _bv > 150 else ("警戒圏" if _bv > 100 else "割安圏"),
                        delta_color="inverse" if _bv > 100 else "normal")
            _vc4.caption(f"時価総額/GDP（GDP: {_buffett['date']}）")

        # 主要指数チャート
        st.divider()
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
