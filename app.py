import os
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import pandas as pd

from modules.data_loader import (
    fetch_stock_data_max,
    fetch_stock_data_max_realtime,
    fetch_ticker_info,
    load_tickers,
)
from modules.indicators import calc_sma, calc_ema, calc_bollinger_bands, calc_volume_ma
from modules.chart import create_candlestick_chart
from modules.events import fetch_earnings_events, fetch_news_events
from modules.ai_summary import get_earnings_analysis, get_news_analysis
from modules.market_hours import is_tse_open, get_refresh_interval_ms, market_status_label

st.set_page_config(
    page_title="日本株ダッシュボード",
    page_icon="📊",
    layout="wide",
)

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "data", "nikkei225_tickers.txt")

PERIOD_LABELS = {
    "1mo": "1ヶ月",
    "3mo": "3ヶ月",
    "6mo": "6ヶ月",
    "1y": "1年",
    "2y": "2年",
}

# 期間コード → 表示期間の目安（営業日数）
_PERIOD_DAYS = {
    "1mo": 23,
    "3mo": 66,
    "6mo": 132,
    "1y": 260,
    "2y": 520,
}


def _calc_view_start_idx(df: pd.DataFrame, period: str) -> int:
    """
    全データ df の中から、選択期間の開始インデックスを返す。
    チャートの初期表示範囲（右端から period 分）を決めるために使用する。
    """
    bars = _PERIOD_DAYS.get(period, 132)
    idx = max(0, len(df) - bars)
    return idx


# ─── 決算詳細ダイアログ ─────────────────────────────────────────────

@st.dialog("📊 決算詳細", width="large")
def show_earnings_dialog(
    clicked_date: str,
    earnings_events: list[dict],
    ticker: str,
    ticker_info: dict,
) -> None:
    """決算マーカー（★）クリック時に表示するダイアログ。"""
    # クリック日に対応するイベントを検索（スナップされた日付に対応できるよう柔軟に）
    ev = next((e for e in earnings_events if e["date"] == clicked_date), None)
    if ev is None:
        # customdata には元の日付が入っているので再度照合
        ev = earnings_events[0] if earnings_events else None
    if ev is None:
        st.error("決算データが見つかりません")
        return

    company_name = ticker_info.get("name", ticker)

    # ── AI 分析（24h キャッシュ）──
    with st.spinner("AI が決算を分析中..."):
        ai = get_earnings_analysis(
            ticker=ticker,
            company_name=company_name,
            period_end=ev["period_end"],
            revenue=ev["revenue"],
            operating_income=ev["operating_income"],
            eps_actual=ev["eps_actual"],
            eps_estimate=ev["eps_estimate"],
            beat=ev["beat"],
        )

    # ── 判定（大きく表示）──
    assessment = ai.get("assessment", "中立")
    color_map = {"良い": "#4CAF50", "悪い": "#ef5350", "中立": "#FF9800"}
    color = color_map.get(assessment, "#FF9800")
    emoji_map = {"良い": "✅", "悪い": "❌", "中立": "➡️"}
    emoji = emoji_map.get(assessment, "➡️")

    st.markdown(
        f"<div style='text-align:center; padding:12px 0;'>"
        f"<span style='font-size:80px; color:{color};'>{emoji}</span>"
        f"<h1 style='color:{color}; margin:0; font-size:64px;'>{assessment}</h1>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # 株価予測
    impact = ai.get("stock_impact", "中立")
    impact_color = {"上昇": "#4CAF50", "下落": "#ef5350", "中立": "#FF9800"}
    impact_arrow = {"上昇": "↑", "下落": "↓", "中立": "→"}
    st.markdown(
        f"<p style='text-align:center; color:{impact_color.get(impact, '#FF9800')};"
        f" font-size:28px; font-weight:bold; margin:4px 0;'>"
        f"株価予測: {impact_arrow.get(impact, '→')} {impact}</p>",
        unsafe_allow_html=True,
    )

    st.markdown(f"> {ai.get('assessment_detail', '')}")
    if ai.get("reasoning"):
        st.caption(f"根拠: {ai['reasoning']}")

    st.divider()

    # ── 財務指標 ──
    st.subheader(f"決算期: {ev['period_end']}  |  発表日: {ev['date']}")

    col1, col2, col3 = st.columns(3)

    rev = ev.get("revenue")
    if rev is not None:
        rev_disp = f"¥{rev / 1e12:.2f}兆" if rev >= 1e12 else f"¥{rev / 1e9:.0f}億"
    else:
        rev_disp = "N/A"
    col1.metric("売上高", rev_disp)

    op_inc = ev.get("operating_income")
    if op_inc is not None:
        op_disp = f"¥{op_inc / 1e9:.0f}億" if op_inc >= 0 else f"▲¥{abs(op_inc) / 1e9:.0f}億"
    else:
        op_disp = "N/A"
    col2.metric("営業利益", op_disp)

    eps_act = ev.get("eps_actual")
    eps_est = ev.get("eps_estimate")
    eps_disp = f"{eps_act:.1f}円" if eps_act is not None else "N/A"
    eps_delta = None
    if eps_act is not None and eps_est is not None:
        eps_delta = f"{eps_act - eps_est:+.1f}円 vs 予想{eps_est:.1f}円"
    col3.metric(
        "EPS",
        eps_disp,
        eps_delta,
        delta_color="normal" if ev.get("beat") is True else ("inverse" if ev.get("beat") is False else "off"),
    )

    # ── 注目ポイント ──
    key_pts = ai.get("key_points", [])
    if key_pts:
        st.subheader("注目ポイント")
        for pt in key_pts:
            st.markdown(f"- {pt}")

    st.divider()

    # ── IR・開示情報リンク ──
    st.subheader("IR・開示情報")
    code_4 = ticker.replace(".T", "").strip()
    # Kabutan: 会社開示情報（TDNET 適時開示をまとめて閲覧できる）
    tdnet_kabutan_url = f"https://kabutan.jp/stock/news?code={code_4}&nmode=3"
    # Kabutan: IR レポート（アナリストレポート）
    ir_report_url = f"https://kabutan.jp/stock/ir_report?code={code_4}"
    # Minkabu: 決算・業績情報
    minkabu_url = f"https://minkabu.jp/stock/{code_4}/settlement"
    website = ticker_info.get("website", "")

    link_cols = st.columns(4 if website else 3)
    link_cols[0].link_button("📋 適時開示（Kabutan）", tdnet_kabutan_url, use_container_width=True)
    link_cols[1].link_button("📊 IR レポート（Kabutan）", ir_report_url, use_container_width=True)
    link_cols[2].link_button("📈 決算情報（Minkabu）", minkabu_url, use_container_width=True)
    if website:
        link_cols[3].link_button("🌐 IR サイト", website, use_container_width=True)


# ─── ニュース詳細ダイアログ ────────────────────────────────────────

@st.dialog("📰 ニュース詳細", width="large")
def show_news_dialog(
    clicked_date: str,
    news_events: list[dict],
    ticker: str,
    ticker_info: dict,
) -> None:
    """ニュースマーカー（●）クリック時に表示するダイアログ。"""
    ev = next((e for e in news_events if e["date"] == clicked_date), None)
    if ev is None:
        ev = news_events[0] if news_events else None
    if ev is None:
        st.error("ニュースデータが見つかりません")
        return

    company_name = ticker_info.get("name", ticker)
    all_items = ev.get("all_items", [{"title": ev["title"], "publisher": ev["publisher"],
                                      "link": ev["link"], "uuid": ev["uuid"]}])
    all_titles = tuple(item["title"] for item in all_items)

    # ── AI 分析（24h キャッシュ）──
    with st.spinner("AI がニュースを分析中..."):
        ai = get_news_analysis(
            ticker=ticker,
            company_name=company_name,
            news_titles=all_titles,
            news_date=ev["date"],
        )

    # ── 株価影響予測（大きく表示）──
    impact = ai.get("stock_impact", "中立")
    confidence = ai.get("confidence", "低")
    impact_color = {"上昇": "#4CAF50", "下落": "#ef5350", "中立": "#FF9800"}
    impact_arrow = {"上昇": "↑ 上昇", "下落": "↓ 下落", "中立": "→ 中立"}

    st.markdown(
        f"<div style='text-align:center; padding:12px 0;'>"
        f"<h1 style='color:{impact_color.get(impact, '#FF9800')}; font-size:60px; margin:0;'>"
        f"{impact_arrow.get(impact, impact)}</h1>"
        f"<p style='color:#aaa; font-size:18px; margin:4px 0;'>予測信頼度: <b>{confidence}</b></p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"**AI 要約:** {ai.get('summary', '')}")
    if ai.get("reasoning"):
        st.caption(f"根拠: {ai['reasoning']}")

    risk = ai.get("key_risk", "")
    if risk:
        st.warning(f"⚠️ リスク: {risk}")

    st.divider()

    # ── ニュース一覧 ──
    st.subheader(f"{ev['date']} のニュース（{len(all_items)} 件）")
    for item in all_items:
        with st.container(border=True):
            st.markdown(f"**{item['title']}**")
            st.caption(f"出典: {item['publisher']}")
            if item.get("link"):
                st.link_button("🔗 記事を読む", item["link"])


# ─── メイン ────────────────────────────────────────────────────────

def main() -> None:
    # ── リアルタイム自動更新（東証開場中のみ）──
    refresh_ms = get_refresh_interval_ms()
    if refresh_ms:
        st_autorefresh(interval=refresh_ms, key="tse_autorefresh")

    st.title("📊 日本株ダッシュボード")

    tickers = load_tickers(TICKERS_PATH)

    # ─── サイドバー ─────────────────────────────────────────────────
    with st.sidebar:
        st.header("銘柄設定")

        ticker_labels = [f"{t['code']}  {t['name']}" for t in tickers]

        # カレンダーページから遷移してきた場合はその銘柄をデフォルト選択
        cal_ticker = st.session_state.pop("calendar_selected_ticker", None)
        if cal_ticker:
            default_idx = next(
                (i for i, t in enumerate(tickers) if t["code"] == cal_ticker), 0
            )
        else:
            default_idx = next(
                (i for i, t in enumerate(tickers) if t["code"] == "7203.T"), 0
            )

        selected_label = st.selectbox("銘柄を選択", ticker_labels, index=default_idx)
        selected_ticker = selected_label.split()[0]
        manual = st.text_input("直接入力（例: 6758.T）", value="")
        ticker = manual.strip() if manual.strip() else selected_ticker

        period = st.select_slider(
            "表示期間",
            options=list(PERIOD_LABELS.keys()),
            value="6mo",
            format_func=lambda x: PERIOD_LABELS[x],
        )

        fetch_btn = st.button("チャートを表示", type="primary", use_container_width=True)

        st.divider()
        st.subheader("テクニカル指標")
        show_sma = st.checkbox("SMA（単純移動平均）", value=True)
        sma_periods = st.multiselect("SMA 期間", [5, 10, 25, 50, 75], default=[5, 25, 75]) if show_sma else []

        show_ema = st.checkbox("EMA（指数移動平均）", value=False)
        ema_periods = st.multiselect("EMA 期間", [9, 12, 21, 26, 50], default=[]) if show_ema else []

        show_bb = st.checkbox("ボリンジャーバンド（20日）", value=False)

        st.divider()
        st.subheader("イベント表示")
        show_earnings = st.checkbox("★ 決算マーカー", value=True)
        show_news = st.checkbox("● ニュースマーカー", value=True)

        st.divider()
        st.caption(market_status_label())

    # ─── データ取得（常に上場来全データ）────────────────────────────
    ticker_changed = st.session_state.get("current_ticker") != ticker

    if fetch_btn or ticker_changed or "df_raw" not in st.session_state:
        with st.spinner(f"{ticker} の全期間データを取得中..."):
            if is_tse_open():
                df_raw = fetch_stock_data_max_realtime(ticker)
            else:
                df_raw = fetch_stock_data_max(ticker)

        if df_raw is None or df_raw.empty:
            st.error(f"'{ticker}' のデータを取得できませんでした。銘柄コードと期間を確認してください。")
            return

        st.session_state["df_raw"] = df_raw
        st.session_state["current_ticker"] = ticker

    df = st.session_state["df_raw"].copy()

    # 初期表示範囲（選択期間に対応するインデックス）
    view_start_idx = _calc_view_start_idx(df, period)
    view_end_idx = len(df) - 1

    # ─── テクニカル指標計算 ──────────────────────────────────────────
    if sma_periods:
        df = calc_sma(df, sma_periods)
    if ema_periods:
        df = calc_ema(df, ema_periods)
    if show_bb:
        df = calc_bollinger_bands(df)
    df = calc_volume_ma(df)

    # ─── イベントデータ取得 ──────────────────────────────────────────
    chart_start = df.index[0].strftime("%Y-%m-%d")
    chart_end = df.index[-1].strftime("%Y-%m-%d")

    with st.spinner("イベントデータを取得中..."):
        earnings_events = fetch_earnings_events(ticker, chart_start, chart_end) if show_earnings else []
        news_events = fetch_news_events(ticker, chart_start, chart_end) if show_news else []
        ticker_info = fetch_ticker_info(ticker)

    # ─── 指標サマリ行（表示範囲の値を使用）─────────────────────────
    df_view = df.iloc[view_start_idx:]
    last_close = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else last_close
    change_pct = (last_close - prev_close) / prev_close * 100

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(
        "現在値",
        f"¥{last_close:,.0f}",
        f"{change_pct:+.2f}%",
        delta_color="normal" if change_pct >= 0 else "inverse",
    )
    c2.metric(f"期間高値（{PERIOD_LABELS[period]}）", f"¥{df_view['High'].max():,.0f}")
    c3.metric(f"期間安値（{PERIOD_LABELS[period]}）", f"¥{df_view['Low'].min():,.0f}")
    c4.metric("決算マーカー", f"{len(earnings_events)} 件")
    c5.metric("ニュースマーカー", f"{len(news_events)} 件")

    # ─── チャート描画 ────────────────────────────────────────────────
    fig, earnings_trace_idx, news_trace_idx = create_candlestick_chart(
        df=df,
        earnings_events=earnings_events,
        news_events=news_events,
        title=f"{ticker}  {ticker_info.get('name', '')}",
        show_sma=sma_periods,
        show_ema=ema_periods,
        show_bb=show_bb,
        view_start_idx=view_start_idx,
        view_end_idx=view_end_idx,
    )

    event_data = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="main_chart",
    )

    # チャートの操作説明
    st.caption(
        "💡 **★（黄色）** = 決算日　**●（水色）** = ニュース日　"
        "マーカーをクリックすると詳細が表示されます。"
        "チャートはドラッグでパン、スクロールでズームできます。"
    )

    # ─── クリックイベント処理 ────────────────────────────────────────
    # Streamlit の plotly_chart on_select イベントではトレース番号のキーは
    # "curve_number"（Plotly.js の curveNumber に対応）
    if event_data and event_data.get("selection", {}).get("points"):
        pt = event_data["selection"]["points"][0]
        tidx = pt.get("curve_number", -1)
        clicked_date = pt.get("x", "")

        if tidx == earnings_trace_idx and earnings_events and clicked_date:
            raw_cd = pt.get("customdata", clicked_date)
            original_date = raw_cd[0] if isinstance(raw_cd, list) else raw_cd
            show_earnings_dialog(str(original_date), earnings_events, ticker, ticker_info)

        elif tidx == news_trace_idx and news_events and clicked_date:
            raw_cd = pt.get("customdata")
            original_date = raw_cd[0] if isinstance(raw_cd, list) else (raw_cd or clicked_date)
            show_news_dialog(str(original_date), news_events, ticker, ticker_info)


if __name__ == "__main__":
    main()
