import os

import pandas as pd
import streamlit as st

from modules.ai_analysis import get_comprehensive_analysis, prepare_analysis_inputs
from modules.data_loader import (
    fetch_stock_data_max,
    fetch_ticker_info,
    load_all_tse_stocks,
    load_tickers,
)
from modules.events import fetch_news_events
from modules.styles import apply_theme

st.set_page_config(
    page_title="AI銘柄総合分析",
    page_icon="🤖",
    layout="wide",
)
apply_theme()

_TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")


# ─── UI ヘルパー ─────────────────────────────────────────────────────────


def _score_card(col, label: str, score: int) -> None:
    """スコアカードを描画する。"""
    if score >= 65:
        color = "🟢"
    elif score <= 40:
        color = "🔴"
    else:
        color = "🟡"

    with col:
        with st.container(border=True):
            st.markdown(f"**{label}**")
            st.markdown(f"### {color} {score} <span style='font-size:0.6em;color:gray;'>/ 100</span>", unsafe_allow_html=True)
            st.progress(score / 100)


def _judgment_banner(judgment: str, detail: str) -> None:
    """総合判断バナーを描画する。"""
    config = {
        "強気買い": ("success", "🚀 強気買い"),
        "買い":     ("success", "📈 買い"),
        "中立":     ("info",    "➡️ 中立"),
        "売り":     ("warning", "📉 売り"),
        "強気売り": ("error",   "🚨 強気売り"),
    }
    style, label = config.get(judgment, ("info", f"➡️ {judgment}"))
    msg = f"**総合判断: {label}**\n\n{detail}"

    if style == "success":
        st.success(msg)
    elif style == "warning":
        st.warning(msg)
    elif style == "error":
        st.error(msg)
    else:
        st.info(msg)


def _render_results(result: dict) -> None:
    """分析結果を全て表示する。"""

    # ── スコアカード 4列 ────────────────────────────────────────
    cols = st.columns(4)
    _score_card(cols[0], "📈 テクニカル",       result["technical_score"])
    _score_card(cols[1], "📊 ファンダメンタル", result["fundamental_score"])
    _score_card(cols[2], "📰 ニュース",          result["news_score"])
    _score_card(cols[3], "🎯 総合スコア",        result["overall_score"])

    st.divider()

    # ── 総合判断バナー ──────────────────────────────────────────
    _judgment_banner(result.get("judgment", "中立"), result.get("overall_detail", ""))

    st.divider()

    # ── チャンス・リスク ────────────────────────────────────────
    col_opp, col_risk = st.columns(2)
    with col_opp:
        st.subheader("💚 チャンス・強み")
        opportunities = result.get("opportunities", [])
        if opportunities:
            for item in opportunities:
                st.markdown(f"- {item}")
        else:
            st.caption("データなし")

    with col_risk:
        st.subheader("🔴 リスク・注意点")
        risks = result.get("risks", [])
        if risks:
            for item in risks:
                st.markdown(f"- {item}")
        else:
            st.caption("データなし")

    st.divider()

    # ── 詳細説明 expander ───────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.expander("📈 テクニカル詳細"):
            st.write(result.get("technical_detail") or "データなし")
    with col2:
        with st.expander("📊 ファンダメンタル詳細"):
            st.write(result.get("fundamental_detail") or "データなし")
    with col3:
        with st.expander("📰 ニュース詳細"):
            st.write(result.get("news_detail") or "データなし")


# ─── メイン ─────────────────────────────────────────────────────────────


def main() -> None:
    st.title("🤖 AI銘柄総合分析")
    st.caption("テクニカル・ファンダメンタル・ニュースを総合した AI 分析レポート")

    # ── 銘柄リスト読み込み ────────────────────────────────────
    nikkei225 = load_tickers(_TICKERS_PATH)
    all_tse, _ = load_all_tse_stocks()
    search_pool = all_tse if all_tse else nikkei225

    # ── サイドバー ────────────────────────────────────────────
    with st.sidebar:
        st.header("銘柄設定")

        search_query = st.text_input(
            "銘柄検索",
            placeholder="例: トヨタ・7203・ソニー",
            key="analysis_search",
        )
        q = search_query.strip().lower()

        if q:
            matched = [
                t for t in search_pool
                if q in t["code"].lower() or q in t["name"].lower()
            ]
            filtered = matched[:100] or nikkei225
            if matched:
                st.caption(f"{len(matched)} 件ヒット")
            else:
                st.caption("該当なし — 日経225を表示")
        else:
            filtered = nikkei225

        def _label(t: dict) -> str:
            market = t.get("market", "")
            if market and market != "nan":
                return f"{t['code']}  {t['name']}  [{market}]"
            return f"{t['code']}  {t['name']}"

        ticker_labels = [_label(t) for t in filtered]
        default_idx = next(
            (i for i, t in enumerate(filtered) if t["code"] == "7203.T"), 0
        )

        selected_label = st.selectbox(
            "銘柄を選択",
            ticker_labels,
            index=min(default_idx, len(ticker_labels) - 1),
            label_visibility="collapsed",
        )
        ticker = selected_label.split()[0]

        st.divider()
        st.caption("⚙️ API 設定状況")

        has_anthropic = bool(st.secrets.get("ANTHROPIC_API_KEY", ""))
        has_jquants = bool(st.secrets.get("JQUANTS_REFRESH_TOKEN", ""))
        st.caption("Claude API: " + ("✅ 設定済み" if has_anthropic else "❌ 未設定"))
        st.caption("J-Quants: " + ("✅ 設定済み" if has_jquants else "⬜ 未設定（yfinanceで代替）"))

    # ── 株価データ取得 ────────────────────────────────────────
    with st.spinner(f"{ticker} のデータを取得中..."):
        df = fetch_stock_data_max(ticker)
        ticker_info = fetch_ticker_info(ticker)

    if df is None or df.empty:
        st.error(f"'{ticker}' のデータを取得できませんでした。銘柄コードを確認してください。")
        return

    company_name = ticker_info.get("name", ticker)
    last_close = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else last_close
    change_pct = (last_close - prev_close) / prev_close * 100

    # ── 会社ヘッダー ──────────────────────────────────────────
    h_col1, h_col2, h_col3, h_col4 = st.columns([3, 1, 1, 1])
    h_col1.subheader(f"🏢 {company_name}  ({ticker})")
    h_col2.metric(
        "現在値",
        f"¥{last_close:,.0f}",
        f"{change_pct:+.2f}%",
        delta_color="normal" if change_pct >= 0 else "inverse",
    )
    sector = ticker_info.get("sector", "")
    if sector:
        h_col3.metric("セクター", sector)
    mktcap = ticker_info.get("market_cap")
    if mktcap:
        cap_str = f"¥{mktcap/1e12:.1f}兆" if mktcap >= 1e12 else f"¥{mktcap/1e9:.0f}億"
        h_col4.metric("時価総額", cap_str)

    st.divider()

    # ── 分析実行ボタン ────────────────────────────────────────
    if "analyzed_tickers" not in st.session_state:
        st.session_state.analyzed_tickers = set()

    already_analyzed = ticker in st.session_state.analyzed_tickers

    btn_col, note_col = st.columns([2, 5])
    if btn_col.button("🤖 AI総合分析を実行", type="primary", use_container_width=True):
        st.session_state.analyzed_tickers.add(ticker)
        already_analyzed = True

    if already_analyzed:
        note_col.caption("✅ 分析済み（結果は24時間キャッシュされます）")
    else:
        note_col.caption(
            "テクニカル・ファンダメンタル・ニュースを総合した AI 分析レポートを生成します。"
            "（Claude API の利用料が発生します）"
        )

    # ── 分析実行・結果表示 ────────────────────────────────────
    if not already_analyzed:
        return

    with st.spinner("AI 分析を実行中..."):
        # 直近30日のニュースを取得
        chart_end = df.index[-1].strftime("%Y-%m-%d")
        chart_start_30d = (df.index[-1] - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        news_events = fetch_news_events(ticker, chart_start_30d, chart_end, company_name)

        # 各入力データを準備
        tech_json, fund_text, news_titles = prepare_analysis_inputs(
            ticker, company_name, df, news_events
        )

        # AI 分析実行（24h キャッシュ）
        result = get_comprehensive_analysis(
            ticker=ticker,
            company_name=company_name,
            tech_json=tech_json,
            fund_text=fund_text,
            news_titles=news_titles,
        )

    _render_results(result)


if __name__ == "__main__":
    main()
