import os
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import pandas as pd

from modules.data_loader import (
    fetch_stock_data_max,
    fetch_stock_data_max_realtime,
    fetch_ticker_info,
    load_tickers,
    load_all_tse_stocks,
    clear_tse_cache,
)
from modules.indicators import calc_sma, calc_ema, calc_bollinger_bands, calc_volume_ma
from modules.chart import create_candlestick_chart
from modules.events import fetch_earnings_events, fetch_news_events
from modules.market_hours import is_tse_open, get_refresh_interval_ms, market_status_label
from modules.styles import apply_theme
from modules.ai_analysis import get_comprehensive_analysis, prepare_analysis_inputs

st.set_page_config(
    page_title="日本株ダッシュボード",
    page_icon="📊",
    layout="wide",
)
apply_theme()

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
        ev = earnings_events[0] if earnings_events else None
    if ev is None:
        st.error("決算データが見つかりません")
        return

    company_name = ticker_info.get("name", ticker)
    st.subheader(f"{company_name}　決算期: {ev['period_end']}  |  発表日: {ev['date']}")

    # ── EPS 予想比較バッジ ──
    beat = ev.get("beat")
    if beat is True:
        st.success("✅ EPS 予想超過")
    elif beat is False:
        st.error("❌ EPS 予想未達")

    # ── 財務指標 ──
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
        delta_color="normal" if beat is True else ("inverse" if beat is False else "off"),
    )

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

    # ── 日経電子版の銘柄ニュースページへの直リンク ──
    code_4 = ticker.replace(".T", "").strip()
    nikkei_url = f"https://www.nikkei.com/nkd/company/news/?scode={code_4}&ba=1"
    st.link_button("🗞️ 日経電子版で関連ニュースを探す", nikkei_url, use_container_width=True)

    # ── ニュース一覧（日経記事が先頭に並ぶ）──
    st.subheader(f"{company_name}　{ev['date']} のニュース（{len(all_items)} 件）")
    for item in all_items:
        with st.container(border=True):
            pub = item.get("publisher", "").lower()
            if any(k in pub for k in ("日本経済新聞", "日経", "nikkei")):
                st.caption("🗞️ 日本経済新聞")
            st.markdown(f"**{item['title']}**")
            st.caption(f"出典: {item['publisher']}")
            if item.get("link"):
                st.link_button("🔗 記事を読む", item["link"])


# ─── AI 分析 描画ヘルパー ──────────────────────────────────────────

def _ai_score_card(col, label: str, score: int) -> None:
    color = "🟢" if score >= 65 else ("🔴" if score <= 40 else "🟡")
    with col:
        with st.container(border=True):
            st.markdown(f"**{label}**")
            st.markdown(
                f"### {color} {score}"
                f"<span style='font-size:0.6em;color:gray;'> / 100</span>",
                unsafe_allow_html=True,
            )
            st.progress(score / 100)


def _ai_judgment_banner(judgment: str, detail: str) -> None:
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


def _render_ai_results(result: dict) -> None:
    # エラー時は専用バナーのみ表示
    if result.get("error"):
        detail = result.get("overall_detail", "不明なエラー")
        if "クレジット" in detail:
            st.warning(detail)
        else:
            st.error(detail)
        return

    # スコアカード 4列
    cols = st.columns(4)
    _ai_score_card(cols[0], "📈 テクニカル",       result["technical_score"])
    _ai_score_card(cols[1], "📊 ファンダメンタル", result["fundamental_score"])
    _ai_score_card(cols[2], "📰 ニュース",          result["news_score"])
    _ai_score_card(cols[3], "🎯 総合スコア",        result["overall_score"])

    st.divider()
    _ai_judgment_banner(result.get("judgment", "中立"), result.get("overall_detail", ""))
    st.divider()

    col_opp, col_risk = st.columns(2)
    with col_opp:
        st.subheader("💚 チャンス・強み")
        for item in result.get("opportunities", []):
            st.markdown(f"- {item}")
    with col_risk:
        st.subheader("🔴 リスク・注意点")
        for item in result.get("risks", []):
            st.markdown(f"- {item}")

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.expander("📈 テクニカル詳細"):
            st.write(result.get("technical_detail") or "データなし")
    with c2:
        with st.expander("📊 ファンダメンタル詳細"):
            st.write(result.get("fundamental_detail") or "データなし")
    with c3:
        with st.expander("📰 ニュース詳細"):
            st.write(result.get("news_detail") or "データなし")


# ─── メイン ────────────────────────────────────────────────────────

def main() -> None:
    # ── リアルタイム自動更新（東証開場中のみ）──
    refresh_ms = get_refresh_interval_ms()
    if refresh_ms:
        st_autorefresh(interval=refresh_ms, key="tse_autorefresh")

    st.title("📊 日本株ダッシュボード")

    nikkei225 = load_tickers(TICKERS_PATH)

    # 東証全上場銘柄（JPX データ 24h キャッシュ）。取得失敗時は日経225にフォールバック
    all_tse, tse_error = load_all_tse_stocks()
    search_pool = all_tse if all_tse else nikkei225

    # ─── サイドバー ─────────────────────────────────────────────────
    with st.sidebar:
        st.header("銘柄設定")

        # ── 全銘柄DBステータス ──────────────────────────────
        db_cols = st.columns([3, 1])
        if tse_error:
            db_cols[0].caption(f"⚠️ JPX取得失敗（日経225で代替中）")
            # エラー詳細はexpanderで確認できる
            with st.expander("エラー詳細"):
                st.code(tse_error, language=None)
        else:
            db_cols[0].caption(f"東証全銘柄 {len(all_tse):,} 件")
        if db_cols[1].button("↺", help="銘柄DBを再取得", use_container_width=True):
            clear_tse_cache()
            st.rerun()

        # ── 銘柄検索（コード / 名称どちらでも可）──
        search_query = st.text_input(
            "銘柄検索",
            placeholder="例: トヨタ・7203・ソニー・電機",
            key="ticker_search",
        )

        q = search_query.strip().lower()
        MAX_DISPLAY = 100  # 一覧に表示する最大件数

        if q:
            matched = [
                t for t in search_pool
                if q in t["code"].lower() or q in t["name"].lower()
            ]
            total_hits = len(matched)
            filtered = matched[:MAX_DISPLAY]

            if not filtered:
                st.caption("該当なし — 日経225を表示")
                filtered = nikkei225
            elif total_hits > MAX_DISPLAY:
                st.caption(f"上位 {MAX_DISPLAY} 件を表示（計 {total_hits} 件ヒット）")
            else:
                st.caption(f"{total_hits} 件ヒット")
        else:
            filtered = nikkei225  # デフォルト表示は日経225

        # 市場区分があれば表示に加える（複数候補の区別に有用）
        def _label(t: dict) -> str:
            market = t.get("market", "")
            if market and market != "nan":
                return f"{t['code']}  {t['name']}  [{market}]"
            return f"{t['code']}  {t['name']}"

        # ── デフォルト選択銘柄の決定 ──────────────────────────────────
        # 優先順位:
        #   1. スキャナー等から遷移した cal_ticker
        #   2. 検索中でない場合は current_ticker（サイドバー操作でリセットされない）
        #   3. 検索中は先頭候補
        #   4. デフォルト: トヨタ
        cal_ticker = st.session_state.pop("calendar_selected_ticker", None)

        if cal_ticker:
            target_ticker = cal_ticker
        elif not q:
            # 検索なし: 現在表示中の銘柄を維持（チェックボックス操作などで戻らないように）
            target_ticker = st.session_state.get("current_ticker")
        else:
            target_ticker = None

        # target_ticker が filtered に含まれない場合は search_pool から探して先頭に挿入
        if target_ticker and not any(t["code"] == target_ticker for t in filtered):
            _found = next((t for t in search_pool if t["code"] == target_ticker), None)
            if _found:
                filtered = [_found] + filtered[:MAX_DISPLAY - 1]

        ticker_labels = [_label(t) for t in filtered]

        if target_ticker:
            default_idx = next(
                (i for i, t in enumerate(filtered) if t["code"] == target_ticker), 0
            )
        elif q:
            default_idx = 0  # 検索時は先頭候補
        else:
            default_idx = next(
                (i for i, t in enumerate(filtered) if t["code"] == "7203.T"), 0
            )

        selected_label = st.selectbox(
            "銘柄を選択",
            ticker_labels,
            index=min(default_idx, len(ticker_labels) - 1),
            label_visibility="collapsed",
        )
        selected_ticker = selected_label.split()[0]

        # 海外ETF・ADRなど東証外のコードを直接入力する場合（省略可）
        manual = st.text_input("海外ETF等の直接入力（例: VTI）", value="")
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
        st.subheader("🤖 AI 分析設定")

        ai_provider = st.selectbox(
            "プロバイダー",
            options=["claude", "openai", "gemini"],
            format_func=lambda x: {
                "claude": "Claude (Anthropic)",
                "openai": "ChatGPT (OpenAI)",
                "gemini": "Gemini (Google)",
            }[x],
            key="ai_provider_select",
        )

        # ページをまたいで API キーを保持するための永続化辞書
        if "ai_api_keys" not in st.session_state:
            st.session_state.ai_api_keys = {}

        _has_owner_claude_key = bool(st.secrets.get("ANTHROPIC_API_KEY", ""))
        if ai_provider == "claude" and _has_owner_claude_key:
            st.caption("✅ Anthropic キー設定済み（共用）")
            ai_api_key = ""
        else:
            _placeholder = {
                "claude": "sk-ant-...",
                "openai": "sk-...",
                "gemini": "AIza...",
            }[ai_provider]

            # ページ遷移後にウィジェット状態がリセットされていたら永続化辞書から復元する
            _widget_key = f"ai_key_{ai_provider}"
            if _widget_key not in st.session_state:
                _saved = st.session_state.ai_api_keys.get(ai_provider, "")
                # 非ASCII文字（日本語エラーメッセージ等）が混入していたら無効とみなしクリア
                if not _saved.isascii():
                    _saved = ""
                    st.session_state.ai_api_keys[ai_provider] = ""
                st.session_state[_widget_key] = _saved

            ai_api_key = st.text_input(
                "API キー",
                type="password",
                placeholder=_placeholder,
                help="入力したキーはこのブラウザセッション中のみ保持されます",
                key=_widget_key,
            )

            # 永続化辞書に保存（次回ページ遷移後の復元用）
            st.session_state.ai_api_keys[ai_provider] = ai_api_key

            if ai_api_key:
                st.caption("✅ キー入力済み（セッション中のみ保持）")
            else:
                st.caption("⬜ API キーを入力してください")

        st.divider()
        st.caption(market_status_label())

    # ─── データ取得（常に上場来全データ）────────────────────────────
    # @st.cache_data の TTL でレート制限を制御するため、毎回関数を呼ぶ。
    # 銘柄変更・ボタン押下時だけスピナーを表示し、autorefresh 時はサイレント更新。
    ticker_changed = st.session_state.get("current_ticker") != ticker

    if fetch_btn or ticker_changed:
        with st.spinner(f"{ticker} のデータを取得中..."):
            df_raw = fetch_stock_data_max_realtime(ticker) if is_tse_open() \
                else fetch_stock_data_max(ticker)
    else:
        # autorefresh または UI 操作時 — キャッシュが切れていれば自動で再取得
        df_raw = fetch_stock_data_max_realtime(ticker) if is_tse_open() \
            else fetch_stock_data_max(ticker)

    if df_raw is None or df_raw.empty:
        st.error(f"'{ticker}' のデータを取得できませんでした。銘柄コードを確認してください。")
        return

    st.session_state["current_ticker"] = ticker
    df = df_raw.copy()

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
        ticker_info = fetch_ticker_info(ticker)
        earnings_events = fetch_earnings_events(ticker, chart_start, chart_end) if show_earnings else []
        # company_name を渡すことで Google News RSS の日経検索精度を高める
        news_events = fetch_news_events(
            ticker, chart_start, chart_end, ticker_info.get("name", "")
        ) if show_news else []

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

    # ─── チャートの高さ調整（チャート直上に配置）────────────────────
    chart_height = st.slider(
        "チャートの高さ", min_value=400, max_value=800, value=580, step=20,
        label_visibility="collapsed",
        help="チャートの高さを調整（400〜800px）",
    )

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
        chart_height=chart_height,
    )

    event_data = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="main_chart",
        config={"scrollZoom": True, "displayModeBar": True},
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

    # ─── AI 総合分析 ────────────────────────────────────────────────
    st.divider()
    _provider_label = {
        "claude": "Claude (Anthropic)",
        "openai": "ChatGPT (OpenAI)",
        "gemini": "Gemini (Google)",
    }.get(ai_provider, ai_provider)
    st.subheader(f"🤖 AI 総合分析　({_provider_label})")

    if "analyzed_tickers" not in st.session_state:
        st.session_state.analyzed_tickers = set()

    # プロバイダーが変わったら別の分析扱いにする
    _analyzed_key = f"{ticker}::{ai_provider}"
    already_analyzed = _analyzed_key in st.session_state.analyzed_tickers

    btn_col, clear_col, note_col = st.columns([2, 1, 4])
    if btn_col.button("🤖 AI総合分析を実行", type="primary", key="main_ai_btn", use_container_width=True):
        st.session_state.analyzed_tickers.add(_analyzed_key)
        already_analyzed = True

    if clear_col.button("🗑️ キャッシュ", key="main_ai_clear_btn", use_container_width=True,
                        help="前回の分析結果キャッシュを削除して再実行します"):
        get_comprehensive_analysis.clear()
        st.session_state.analyzed_tickers.discard(_analyzed_key)
        already_analyzed = False
        st.rerun()

    if already_analyzed:
        note_col.caption("✅ 分析済み（結果は24時間キャッシュされます）")
    else:
        note_col.caption(
            f"テクニカル・ファンダメンタル・ニュースを総合した AI 分析レポートを生成します。"
            f"（{_provider_label} API の利用料が発生します）"
        )

    if already_analyzed:
        with st.spinner("AI 分析を実行中..."):
            _ai_end = df.index[-1].strftime("%Y-%m-%d")
            _ai_start = (df.index[-1] - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
            _news_30d = fetch_news_events(ticker, _ai_start, _ai_end, ticker_info.get("name", ""))
            tech_json, fund_text, news_titles = prepare_analysis_inputs(
                ticker, ticker_info.get("name", ticker), df, _news_30d
            )
            _ai_result = get_comprehensive_analysis(
                ticker=ticker,
                company_name=ticker_info.get("name", ticker),
                tech_json=tech_json,
                fund_text=fund_text,
                news_titles=news_titles,
                provider=ai_provider,
                api_key=ai_api_key,
            )
        _render_ai_results(_ai_result)


if __name__ == "__main__":
    main()
