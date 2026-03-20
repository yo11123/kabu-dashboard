"""
市場指標ダッシュボード

テクニカル・ファンダメンタルズ・センチメント・マクロ経済まで網羅した
全58指標をカテゴリ別に表示。チャートデータが取得可能な指標はリアルタイム表示。
"""
import plotly.graph_objects as go
import streamlit as st

from modules.market_context import (
    INDICATORS,
    calc_derived_indicators,
    fetch_indicator_history,
    fetch_market_snapshot,
)
from modules.market_hours import market_status_label
from modules.styles import BG_BASE, BG_PANEL, GRID_COLOR, TEXT_MUTED, apply_theme

st.set_page_config(
    page_title="市場指標 | 日本株ダッシュボード",
    page_icon="🌐",
    layout="wide",
)
apply_theme()


# ─── 外部データが必要な指標の説明 ──────────────────────────────────────

_EXTERNAL_INDICATORS: dict[str, list[dict]] = {
    "sentiment": [
        {"name": "日経VI", "desc": "日経225オプションから算出される日本版VIX。日本市場の恐怖度を測る。", "source": "日本取引所グループ"},
        {"name": "Put/Call Ratio", "desc": "プット/コール出来高比率。1.0超で弱気偏り、極端な値は逆張りシグナル。", "source": "CBOE / 大阪取引所"},
        {"name": "AAII投資家センチメント", "desc": "米個人投資家の強気/弱気/中立割合。極端な偏りは逆張り指標。", "source": "aaii.com"},
        {"name": "CNN Fear & Greed Index", "desc": "7つの市場指標を総合して0（恐怖）〜100（強欲）で表示。", "source": "CNN Business"},
        {"name": "騰落レシオ（25日）", "desc": "値上がり/値下がり銘柄数比率。120超で過熱、70未満で底値圏。", "source": "東証データ"},
        {"name": "新高値・新安値銘柄数", "desc": "年初来高値/安値更新銘柄の集計。市場の内部健全性を示す。", "source": "東証データ"},
    ],
    "bond": [
        {"name": "ハイイールドスプレッド", "desc": "ジャンク債と国債の利回り差。拡大＝リスクオフ、縮小＝リスクオン。", "source": "FRED (BAMLH0A0HYM2)"},
        {"name": "TEDスプレッド", "desc": "銀行間金利とT-Billの差。金融危機時に急拡大する。", "source": "FRED"},
    ],
    "flow": [
        {"name": "投資主体別売買動向", "desc": "海外投資家・個人・信託銀行等の売買状況。海外投資家の動向が最重要。", "source": "東証（毎週木曜公表）"},
        {"name": "CFTC先物ポジション（COT）", "desc": "米先物市場の参加者別ポジション。大口投機筋の偏りは反転リスク。", "source": "CFTC（毎週金曜公表）"},
        {"name": "ETF資金フロー", "desc": "SPY・QQQ等への資金流入出。リスクオン/オフの温度計。", "source": "etf.com / Bloomberg"},
        {"name": "裁定買い残", "desc": "先物と現物の裁定取引残高。減少後は売り圧力後退→反発しやすい。", "source": "東証"},
    ],
    "volatility": [
        {"name": "MOVE Index", "desc": "債券版VIX。金融不安・金利急変動で急上昇し株式市場にも波及。", "source": "ICE BofA"},
        {"name": "ヒンデンブルグ・オーメン", "desc": "新高値と新安値が同時に多数出現する市場内部の矛盾を検出。暴落の前兆（ダマシも多い）。", "source": "計算必要"},
    ],
    "macro": [
        {"name": "PMI（購買担当者景気指数）", "desc": "50超＝拡大、50未満＝縮小。ISM製造業PMIは毎月第1営業日発表。", "source": "ISM / S&P Global"},
        {"name": "雇用統計（NFP）", "desc": "毎月第1金曜発表。FRB政策に直結する最重要経済指標の一つ。", "source": "BLS"},
        {"name": "CPI（消費者物価指数）", "desc": "インフレ率の代表指標。コアCPIが予想超でFRB利上げ懸念→株安。", "source": "BLS"},
        {"name": "GDP成長率", "desc": "2四半期連続マイナスでテクニカル・リセッション。ただし市場は先読み。", "source": "BEA"},
        {"name": "LEI（景気先行指数）", "desc": "10の先行指標の合成。3ヶ月連続低下で景気後退警告。", "source": "Conference Board"},
        {"name": "消費者信頼感指数", "desc": "米GDPの7割は個人消費。消費者マインドは経済全体の行方を左右。", "source": "Conference Board"},
        {"name": "ミシガン大消費者信頼感", "desc": "1年先・5年先のインフレ期待も含む。FRBが政策判断の参考にする。", "source": "University of Michigan"},
    ],
    "valuation": [
        {"name": "バフェット指標", "desc": "株式時価総額/名目GDP。100%超で割高、150%超で歴史的警戒ゾーン。", "source": "計算必要（FRED + Wilshire 5000）"},
        {"name": "CAPEレシオ（シラーPER）", "desc": "過去10年インフレ調整後平均利益でPER計算。30超で長期リターン低下傾向。", "source": "multpl.com / shillerdata.com"},
        {"name": "空売り比率", "desc": "全売買代金に占める空売り割合。40%超で売り圧力大、逆張りの目安にも。", "source": "東証（毎日公表）"},
    ],
}


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
        font=dict(family="'IBM Plex Mono', monospace", color=TEXT_MUTED, size=10),
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
        df = fetch_indicator_history(ticker, period)
        if df is not None and not df.empty:
            fig = _make_chart(df, color=color)
            st.plotly_chart(fig, use_container_width=True, key=f"chart_{ticker}_{period}")

    if desc:
        st.caption(desc)


def _render_info_indicator(item: dict) -> None:
    """外部データ必要な指標の説明カードを描画する。"""
    with st.container(border=True):
        st.markdown(f"**{item['name']}**")
        st.caption(item["desc"])
        src = item.get("source") or item.get("status", "")
        if src:
            st.caption(f"📎 データソース: {src}")


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
        "💹 資金フロー",
        "⚡ ボラティリティ",
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
        # 外部データ
        st.divider()
        st.caption("以下の指標は外部データソースが必要です")
        cols = st.columns(2)
        for i, item in enumerate(_EXTERNAL_INDICATORS.get("sentiment", [])):
            with cols[i % 2]:
                _render_info_indicator(item)

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
        # 外部データ
        st.divider()
        st.caption("以下の指標は外部データソースが必要です")
        cols = st.columns(2)
        for i, item in enumerate(_EXTERNAL_INDICATORS.get("bond", [])):
            with cols[i % 2]:
                _render_info_indicator(item)

    # ── 4. 資金フロー ─────────────────────────────────────────
    with tabs[3]:
        st.subheader("資金フロー・ポジション指標")
        st.info("**信用買い残・売り残・貸借倍率** はメインチャートページの AI 分析に組み込まれています。")
        cols = st.columns(2)
        for i, item in enumerate(_EXTERNAL_INDICATORS.get("flow", [])):
            with cols[i % 2]:
                _render_info_indicator(item)

    # ── 5. ボラティリティ ─────────────────────────────────────
    with tabs[4]:
        st.subheader("ボラティリティ・リスク指標")
        # 実現ボラティリティ
        hv = derived.get("日経HV20")
        if hv:
            st.metric("日経225 HV20（実現ボラティリティ）", f"{hv['value']:.1f}%")
            st.caption("過去20日間の実際の価格変動率（年率換算）。VIX（予想変動率）と比較して使う。")
        st.divider()
        cols = st.columns(2)
        for i, item in enumerate(_EXTERNAL_INDICATORS.get("volatility", [])):
            with cols[i % 2]:
                _render_info_indicator(item)

    # ── 6. マクロ経済 ─────────────────────────────────────────
    with tabs[5]:
        st.subheader("マクロ経済・先行指標")
        st.caption("マクロ経済指標は定期発表データのため、リアルタイム取得はできません。以下は参照先のガイドです。")
        cols = st.columns(2)
        for i, item in enumerate(_EXTERNAL_INDICATORS.get("macro", [])):
            with cols[i % 2]:
                _render_info_indicator(item)

    # ── 7. コモディティ・為替 ─────────────────────────────────
    with tabs[6]:
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

    # ── 8. バリュエーション ──────────────────────────────────
    with tabs[7]:
        st.subheader("バリュエーション・市場全体指標")
        # NT倍率（ライブ）
        nt = derived.get("NT倍率")
        if nt:
            st.metric("NT倍率", f"{nt['value']:.2f} 倍")
            st.caption("日経225÷TOPIX。拡大は値がさ株集中、市場の広がりに欠ける状態。")
        # イールドスプレッド概算
        tnx = snapshot.get("米10年債利回り", {}).get("value")
        sp500 = snapshot.get("S&P 500", {}).get("value")
        if tnx and sp500:
            # S&P500のPER概算（≒22倍とする）で益回りを計算
            earnings_yield = 100 / 22  # 概算
            eq_spread = round(earnings_yield - tnx, 2)
            st.metric("株式益回りスプレッド（概算）", f"{eq_spread:+.2f}%")
            st.caption("株式益回り（1/PER）- 米10年債利回り。マイナスなら債券が相対的に魅力的。")
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
        # 外部データ
        st.divider()
        st.caption("以下の指標は外部データソースが必要です")
        cols = st.columns(2)
        for i, item in enumerate(_EXTERNAL_INDICATORS.get("valuation", [])):
            with cols[i % 2]:
                _render_info_indicator(item)


if __name__ == "__main__":
    main()
