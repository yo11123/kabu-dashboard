import os
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import pandas as pd

from modules.persistence import save_daily, load_daily, try_restore_from_cookies

from modules.data_loader import (
    fetch_stock_data_max,
    fetch_stock_data_max_realtime,
    fetch_ticker_info,
    load_tickers,
    load_all_tse_stocks,
    clear_tse_cache,
)
from modules.indicators import (
    calc_sma, calc_ema, calc_bollinger_bands, calc_volume_ma,
    calc_rsi, calc_macd, calc_stochastic, calc_cci, calc_ichimoku,
)
from modules.fundamental import fetch_fundamental_yfinance, fetch_fundamental_kabutan
from modules.margin import fetch_margin_data, format_margin_text
from modules.chart import create_candlestick_chart
from modules.events import fetch_earnings_events, fetch_news_events
from modules.market_hours import is_tse_open, get_refresh_interval_ms, market_status_label
from modules.styles import apply_theme
from streamlit_cookies_controller import CookieController
from modules.ai_analysis import (
    get_comprehensive_analysis,
    prepare_analysis_inputs,
    build_chat_system_prompt,
    get_chat_response,
)

from modules.loading import helix_spinner
apply_theme()
try_restore_from_cookies()

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")

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
    from modules.icons import check_glow, warn_glow, trend_up, trend_down

    ev = next((e for e in earnings_events if e["date"] == clicked_date), None)
    if ev is None:
        ev = earnings_events[0] if earnings_events else None
    if ev is None:
        st.error("決算データが見つかりません")
        return

    company_name = ticker_info.get("name", ticker)

    # ── ヘッダー ──
    beat = ev.get("beat")
    eps_act = ev.get("eps_actual")
    eps_est = ev.get("eps_estimate")
    rev = ev.get("revenue")
    op_inc = ev.get("operating_income")

    # 総合判定
    if beat is True:
        verdict_color = "#3fb950"
        verdict_icon = trend_up()
        verdict_text = "好決算 — 株価にポジティブ"
        verdict_bg = "rgba(63,185,80,0.08)"
    elif beat is False:
        verdict_color = "#f47067"
        verdict_icon = trend_down()
        verdict_text = "決算未達 — 株価にネガティブ"
        verdict_bg = "rgba(244,112,103,0.08)"
    else:
        verdict_color = "#d4af37"
        verdict_icon = ""
        verdict_text = "決算発表"
        verdict_bg = "rgba(212,175,55,0.05)"

    st.markdown(
        f"""<div style="background:{verdict_bg};border:1px solid {verdict_color}22;
            border-left:3px solid {verdict_color};border-radius:4px;padding:16px 20px;margin-bottom:12px;">
            <div style="font-family:'Cormorant Garamond',serif;font-size:1.2em;color:#f0ece4;letter-spacing:0.05em;">
                {company_name}
                <span style="color:#6b7280;font-size:0.7em;margin-left:8px;">
                    決算期末: {ev['period_end']}　発表日: {ev['date']}
                </span>
            </div>
            <div style="font-size:1.1em;color:{verdict_color};margin-top:8px;font-weight:600;">
                {verdict_icon} {verdict_text}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── 財務指標カード ──
    col1, col2, col3 = st.columns(3)

    if rev is not None:
        rev_disp = f"¥{rev / 1e12:.2f}兆" if rev >= 1e12 else f"¥{rev / 1e9:.0f}億"
    else:
        rev_disp = "N/A"
    col1.metric("売上高", rev_disp)

    if op_inc is not None:
        op_disp = f"¥{op_inc / 1e9:.0f}億" if op_inc >= 0 else f"▲¥{abs(op_inc) / 1e9:.0f}億"
        if rev and rev > 0 and op_inc is not None:
            margin = op_inc / rev * 100
            col2.metric("営業利益", op_disp, f"利益率 {margin:.1f}%", delta_color="off")
        else:
            col2.metric("営業利益", op_disp)
    else:
        col2.metric("営業利益", "N/A")

    eps_disp = f"{eps_act:.1f}円" if eps_act is not None else "N/A"
    eps_delta = None
    if eps_act is not None and eps_est is not None and eps_est != 0:
        surprise_pct = (eps_act - eps_est) / abs(eps_est) * 100
        eps_delta = f"{surprise_pct:+.1f}% vs 予想{eps_est:.1f}円"
    col3.metric(
        "EPS",
        eps_disp,
        eps_delta,
        delta_color="normal" if beat is True else ("inverse" if beat is False else "off"),
    )

    # ── 好材料/悪材料の分析 ──
    factors_good: list[str] = []
    factors_bad: list[str] = []

    if beat is True and eps_act is not None and eps_est is not None:
        surprise = (eps_act - eps_est) / abs(eps_est) * 100
        if surprise > 20:
            factors_good.append(f"EPSが予想を{surprise:.0f}%大幅超過 — 強い好材料")
        elif surprise > 5:
            factors_good.append(f"EPSが予想を{surprise:.0f}%超過 — 好材料")
        else:
            factors_good.append(f"EPSが予想を小幅超過（{surprise:.1f}%）— 軽い好材料")
    elif beat is False and eps_act is not None and eps_est is not None:
        miss = (eps_est - eps_act) / abs(eps_est) * 100
        if miss > 20:
            factors_bad.append(f"EPSが予想を{miss:.0f}%大幅下回り — 強い悪材料")
        elif miss > 5:
            factors_bad.append(f"EPSが予想を{miss:.0f}%下回り — 悪材料")
        else:
            factors_bad.append(f"EPSが予想を小幅下回り（{miss:.1f}%）— 軽い悪材料")

    if op_inc is not None and rev is not None and rev > 0:
        margin = op_inc / rev * 100
        if margin >= 15:
            factors_good.append(f"営業利益率{margin:.1f}% — 高収益体質")
        elif margin >= 8:
            factors_good.append(f"営業利益率{margin:.1f}% — 安定的")
        elif margin < 3:
            factors_bad.append(f"営業利益率{margin:.1f}% — 低収益")

    if factors_good or factors_bad:
        st.divider()
        gc, bc = st.columns(2)
        with gc:
            if factors_good:
                st.markdown(f"**{trend_up()} 好材料**", unsafe_allow_html=True)
                for i, f in enumerate(factors_good):
                    st.markdown(f"{check_glow(i * 0.3)} {f}", unsafe_allow_html=True)
        with bc:
            if factors_bad:
                st.markdown(f"**{trend_down()} 悪材料**", unsafe_allow_html=True)
                for i, f in enumerate(factors_bad):
                    st.markdown(f"{warn_glow(i * 0.3)} {f}", unsafe_allow_html=True)

    # ── AI 決算インパクト分析 ──
    st.divider()
    _ai_key = f"_earnings_ai_{ticker}_{ev['date']}"
    if _ai_key not in st.session_state:
        st.session_state[_ai_key] = None

    if st.session_state[_ai_key]:
        st.markdown(
            f"**🤖 AI 決算インパクト分析**\n\n{st.session_state[_ai_key]}",
        )
    else:
        if st.button("🤖 AIで決算インパクトを分析", use_container_width=True):
            with helix_spinner("決算インパクトを分析中..."):
                try:
                    api_key = ""
                    try:
                        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
                    except Exception:
                        pass
                    if api_key:
                        from modules.ai_analysis import _call_claude
                        _prompt = f"""以下の決算データを分析し、株価への影響を日本語で簡潔に解説してください。

銘柄: {company_name} ({ticker})
決算期末: {ev['period_end']} / 発表日: {ev['date']}
売上高: {rev_disp}
営業利益: {op_disp if op_inc is not None else 'N/A'}
{f'営業利益率: {op_inc / rev * 100:.1f}%' if op_inc and rev and rev > 0 else ''}
EPS実績: {eps_disp}
{f'EPS予想: {eps_est:.1f}円 / サプライズ: {((eps_act - eps_est) / abs(eps_est) * 100):+.1f}%' if eps_act is not None and eps_est is not None and eps_est != 0 else ''}

以下の3点を各2〜3文で分析してください:
1. **決算評価**: この決算は好決算か悪決算か、市場予想との乖離度
2. **株価への影響**: 翌営業日以降の株価にどう影響するか（過去の類似ケースも参考に）
3. **今後の注目点**: 次の決算に向けて注視すべきポイント

提供データの数値のみを使い、推測で数値を補わないこと。"""
                        _resp = _call_claude(_prompt, api_key)
                        st.session_state[_ai_key] = _resp
                        st.markdown(f"**🤖 AI 決算インパクト分析**\n\n{_resp}")
                    else:
                        st.warning("APIキーが未設定のため分析できません")
                except Exception as e:
                    st.error(f"分析エラー: {e}")

    st.divider()

    # ── IR・開示情報リンク ──
    st.caption("IR・開示情報")
    code_4 = ticker.replace(".T", "").strip()
    tdnet_kabutan_url = f"https://kabutan.jp/stock/news?code={code_4}&nmode=3"
    ir_report_url = f"https://kabutan.jp/stock/ir_report?code={code_4}"
    minkabu_url = f"https://minkabu.jp/stock/{code_4}/settlement"
    website = ticker_info.get("website", "")

    link_cols = st.columns(4 if website else 3)
    link_cols[0].link_button("📋 適時開示", tdnet_kabutan_url, use_container_width=True)
    link_cols[1].link_button("📊 IR レポート", ir_report_url, use_container_width=True)
    link_cols[2].link_button("📈 決算情報", minkabu_url, use_container_width=True)
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
    # ── Cookie（ブラウザ永続化）──
    _cookies = CookieController()

    # ── リアルタイム自動更新（東証開場中のみ）──
    refresh_ms = get_refresh_interval_ms()
    if refresh_ms:
        st_autorefresh(interval=refresh_ms, key="tse_autorefresh")

    st.markdown("<h1 style='font-family:Cormorant Garamond,serif; font-weight:300; letter-spacing:0.12em; font-size:1.6rem;'>日本株アプリ v1.1</h1>", unsafe_allow_html=True)

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
        nav_ticker = st.session_state.pop("selected_ticker", None)

        if nav_ticker:
            target_ticker = nav_ticker
        elif cal_ticker:
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

        period = "6mo"
        fetch_btn = True

        st.divider()
        st.subheader("テクニカル指標")
        show_sma = st.checkbox("SMA（単純移動平均）", value=True)
        sma_periods = st.multiselect("SMA 期間", [5, 10, 25, 50, 75], default=[5, 25, 75]) if show_sma else []

        show_ema = st.checkbox("EMA（指数移動平均）", value=False)
        ema_periods = st.multiselect("EMA 期間", [9, 12, 21, 26, 50], default=[]) if show_ema else []

        show_bb = st.checkbox("ボリンジャーバンド（20日）", value=False)
        show_ichimoku = st.checkbox("一目均衡表", value=False)

        st.caption("── オシレーター（サブプロット）──")
        show_rsi   = st.checkbox("RSI（14日）", value=False)
        show_macd  = st.checkbox("MACD（12/26/9）", value=False)
        show_stoch = st.checkbox("ストキャスティクス（14/3）", value=False)
        show_cci   = st.checkbox("CCI（20日）※AI分析のみ", value=False, help="CCI はチャートに描画せず AI 分析に使用します")

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

            # APIキーの復元（優先順位: セッション → Cookie → 空）
            _widget_key = f"ai_key_{ai_provider}"
            _valid_prefixes = {"claude": "sk-ant-", "openai": "sk-", "gemini": "AIza"}
            _prefix = _valid_prefixes.get(ai_provider, "")
            _cookie_key = f"apikey_{ai_provider}"

            if _widget_key not in st.session_state:
                # まずセッション内辞書から、なければCookieから復元
                _saved = st.session_state.ai_api_keys.get(ai_provider, "")
                if not _saved:
                    _saved = _cookies.get(_cookie_key) or ""
                # 形式不正なキーは無効とみなしクリア
                if not _saved.isascii() or (_saved and _prefix and not _saved.startswith(_prefix)):
                    _saved = ""
                    st.session_state.ai_api_keys[ai_provider] = ""
                st.session_state[_widget_key] = _saved

            ai_api_key = st.text_input(
                "API キー",
                type="password",
                placeholder=_placeholder,
                help="入力したキーはブラウザに1日間保存されます（同じブラウザなら再入力不要）",
                key=_widget_key,
            )

            # 形式が正しいキーのみ保存（セッション辞書 + Cookie）
            if not ai_api_key or (_prefix and ai_api_key.startswith(_prefix)):
                st.session_state.ai_api_keys[ai_provider] = ai_api_key
                if ai_api_key:
                    _cookies.set(_cookie_key, ai_api_key, max_age=86400)  # 1日
                else:
                    try:
                        _cookies.remove(_cookie_key)
                    except Exception:
                        pass

            if ai_api_key:
                st.caption("✅ キー保存済み（ブラウザに1日間保持）")
            else:
                st.caption("⬜ API キーを入力してください")

        st.divider()
        st.markdown(market_status_label(), unsafe_allow_html=True)

    # ─── データ取得（常に上場来全データ）────────────────────────────
    # @st.cache_data の TTL でレート制限を制御するため、毎回関数を呼ぶ。
    # 銘柄変更・ボタン押下時だけスピナーを表示し、autorefresh 時はサイレント更新。
    ticker_changed = st.session_state.get("current_ticker") != ticker

    if fetch_btn or ticker_changed:
        with helix_spinner(f"{ticker} のデータを取得中..."):
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
    _default_start = _calc_view_start_idx(df, period)
    _total_bars = len(df)

    # ─── テクニカル指標計算 ──────────────────────────────────────────
    if sma_periods:
        df = calc_sma(df, sma_periods)
    if ema_periods:
        df = calc_ema(df, ema_periods)
    if show_bb:
        df = calc_bollinger_bands(df)
    if show_ichimoku:
        df = calc_ichimoku(df)
    df = calc_volume_ma(df)
    if show_rsi:
        df = calc_rsi(df)
    if show_macd:
        df = calc_macd(df)
    if show_stoch:
        df = calc_stochastic(df)
    if show_cci:
        df = calc_cci(df)

    # ─── イベントデータ取得 ──────────────────────────────────────────
    chart_start = df.index[0].strftime("%Y-%m-%d")
    chart_end = df.index[-1].strftime("%Y-%m-%d")

    with helix_spinner("イベントデータを取得中..."):
        ticker_info = fetch_ticker_info(ticker)
        earnings_events = fetch_earnings_events(ticker, chart_start, chart_end) if show_earnings else []
        # company_name を渡すことで Google News RSS の日経検索精度を高める
        news_events = fetch_news_events(
            ticker, chart_start, chart_end, ticker_info.get("name", "")
        ) if show_news else []

    # 銘柄名: JPXリスト(filtered)に日本語名があれば優先、なければ yfinance の名前を使用
    company_name = next((t["name"] for t in filtered if t["code"] == ticker), "")
    company_name = company_name or ticker_info.get("name", ticker)

    # ─── ティッカーバナー ───────────────────────────────────────────
    df_view = df.iloc[_default_start:]
    _close_clean = df["Close"].dropna()
    last_close = float(_close_clean.iloc[-1]) if not _close_clean.empty else 0
    prev_close = float(_close_clean.iloc[-2]) if len(_close_clean) >= 2 else last_close
    if last_close != last_close:  # NaN check
        last_close = 0
    if prev_close != prev_close:
        prev_close = last_close
    change_val = last_close - prev_close
    change_pct = (change_val / prev_close * 100) if prev_close else 0
    _chg_color = "#26a69a" if change_pct >= 0 else "#ef5350"
    _chg_arrow = "▲" if change_pct >= 0 else "▼"
    _period_high = float(df_view["High"].max())
    _period_low = float(df_view["Low"].min())

    st.markdown(
        f"""<div style="
            background: rgba(10,15,26,0.5);
            border: 1px solid rgba(212,175,55,0.06); border-left: 2px solid {_chg_color};
            border-radius: 2px; padding: 24px 32px; margin-bottom: 16px;
        ">
            <div style="display:flex; align-items:baseline; gap:20px; flex-wrap:wrap;">
                <span style="font-family:'Cormorant Garamond','Noto Sans JP',serif; font-size:1.5em; font-weight:400; color:#f0ece4; letter-spacing:0.05em;">
                    {company_name}
                </span>
                <span style="font-family:'Inter',sans-serif; font-size:0.7em; color:#6b7280; letter-spacing:0.15em; text-transform:uppercase;">
                    {ticker}
                </span>
                <span style="font-family:'IBM Plex Mono',monospace; font-size:1.5em; font-weight:400; color:#f0ece4; margin-left:auto; letter-spacing:0.02em;">
                    ¥{last_close:,.0f}
                </span>
                <span style="font-family:'IBM Plex Mono',monospace; font-size:0.95em; font-weight:500; color:{_chg_color};">
                    {_chg_arrow} {abs(change_val):,.0f}（{change_pct:+.2f}%）
                </span>
            </div>
            <div style="display:flex; gap:32px; margin-top:14px; font-family:'Inter',sans-serif; font-size:0.65em; color:#6b7280; letter-spacing:0.08em; text-transform:uppercase;">
                <span>{PERIOD_LABELS[period]}高値 <b style="color:#f0ece4; font-weight:500;">¥{_period_high:,.0f}</b></span>
                <span>{PERIOD_LABELS[period]}安値 <b style="color:#f0ece4; font-weight:500;">¥{_period_low:,.0f}</b></span>
                <span>決算 <b style="color:#d4af37; font-weight:500;">{len(earnings_events)}</b></span>
                <span>ニュース <b style="color:#8fb8a0; font-weight:500;">{len(news_events)}</b></span>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ─── 期間切替ボタン（チャート直上）─────────────────────────────
    _period_options = {
        "1M": ("1ヶ月", 21),
        "3M": ("3ヶ月", 63),
        "6M": ("6ヶ月", 132),
        "1Y": ("1年", 260),
        "2Y": ("2年", 520),
        "5Y": ("5年", 1300),
        "ALL": ("全期間", _total_bars),
    }

    # セッション内で期間を保持
    if "chart_period" not in st.session_state:
        st.session_state.chart_period = period  # サイドバーの初期値を使用

    _btn_cols = st.columns(len(_period_options))
    for i, (key, (label, _)) in enumerate(_period_options.items()):
        _is_active = st.session_state.chart_period == key
        if _btn_cols[i].button(
            label,
            key=f"period_btn_{key}",
            use_container_width=True,
            type="primary" if _is_active else "secondary",
        ):
            st.session_state.chart_period = key

    _selected_period = st.session_state.chart_period
    _bars = _period_options.get(_selected_period, ("", 132))[1]
    view_start_idx = max(0, _total_bars - _bars)
    view_end_idx = _total_bars - 1
    chart_height = 580

    # ─── チャート描画 ────────────────────────────────────────────────
    fig, earnings_trace_idx, news_trace_idx = create_candlestick_chart(
        df=df,
        earnings_events=earnings_events,
        news_events=news_events,
        title=f"{ticker}  {company_name}",
        show_sma=sma_periods,
        show_ema=ema_periods,
        show_bb=show_bb,
        show_ichimoku=show_ichimoku,
        show_rsi=show_rsi,
        show_macd=show_macd,
        show_stoch=show_stoch,
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

    # ─── データ事前取得（タブ共用）──────────────────────────────────
    with helix_spinner("データを取得中..."):
        _margin = fetch_margin_data(ticker)
        _fund_yf = fetch_fundamental_yfinance(ticker)
        _fund_kb = fetch_fundamental_kabutan(ticker)

    _ai_end = df.index[-1].strftime("%Y-%m-%d")
    _ai_start = (df.index[-1] - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    _news_30d = fetch_news_events(ticker, _ai_start, _ai_end, company_name)
    tech_json, fund_text, news_titles, _margin_text, _market_text = prepare_analysis_inputs(
        ticker, company_name, df, _news_30d
    )

    _provider_label = {
        "claude": "Claude (Anthropic)",
        "openai": "ChatGPT (OpenAI)",
        "gemini": "Gemini (Google)",
    }.get(ai_provider, ai_provider)

    # ─── タブレイアウト ───────────────────────────────────────────
    tab_fund, tab_ai, tab_chat = st.tabs([
        "📊 ファンダメンタルズ",
        f"🤖 AI分析（{_provider_label}）",
        "💬 AIチャット",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB 1: ファンダメンタルズ + 信用残
    # ════════════════════════════════════════════════════════════════
    with tab_fund:
        # ── ファンダメンタルズ ──────────────────────────────────────
        _per = _fund_kb.get("per") or _fund_yf.get("per")
        _pbr = _fund_kb.get("pbr") or _fund_yf.get("pbr")
        _roe = _fund_yf.get("roe")
        _roa = _fund_yf.get("roa")
        _eps = _fund_yf.get("eps_trailing")
        _div_kb = _fund_kb.get("dividend_yield")
        _div_yf = _fund_yf.get("dividend_yield")
        _mktcap = _fund_kb.get("market_cap") or _fund_yf.get("market_cap")
        _fcf = _fund_yf.get("free_cashflow")

        # バリュエーション行
        _fc1, _fc2, _fc3, _fc4 = st.columns(4)
        _fc1.metric("PER", f"{_per:.1f} 倍" if _per else "—")
        _fc2.metric("PBR", f"{_pbr:.2f} 倍" if _pbr else "—")
        _fc3.metric("ROE", f"{_roe * 100:.1f}%" if _roe else "—")
        _fc4.metric("ROA", f"{_roa * 100:.1f}%" if _roa else "—")

        # 財務行
        _fc5, _fc6, _fc7, _fc8 = st.columns(4)
        _fc5.metric("EPS（実績）", f"¥{_eps:,.1f}" if _eps else "—")
        if _div_kb is not None:
            _fc6.metric("配当利回り", f"{_div_kb:.2f}%")
        elif _div_yf is not None:
            _fc6.metric("配当利回り", f"{_div_yf * 100:.2f}%")
        else:
            _fc6.metric("配当利回り", "—")
        if _mktcap:
            _fc7.metric("時価総額", f"¥{_mktcap / 1e12:.2f}兆" if _mktcap >= 1e12 else f"¥{_mktcap / 1e8:,.0f}億")
        else:
            _fc7.metric("時価総額", "—")
        if _fcf:
            if abs(_fcf) >= 1e12:
                _fc8.metric("FCF", f"¥{_fcf / 1e12:.2f}兆")
            elif abs(_fcf) >= 1e8:
                _fc8.metric("FCF", f"¥{_fcf / 1e8:,.0f}億")
            else:
                _fc8.metric("FCF", f"¥{_fcf:,.0f}")
        else:
            _fc8.metric("FCF", "—")

        # 補足情報
        _sector = _fund_yf.get("sector", "")
        _industry = _fund_yf.get("industry", "")
        _beta = _fund_yf.get("beta")
        _rev_growth = _fund_yf.get("revenue_growth")
        _op_margin = _fund_yf.get("operating_margins")
        _extra_parts = []
        if _sector:
            _extra_parts.append(f"セクター: {_sector}" + (f" / {_industry}" if _industry else ""))
        if _beta is not None:
            _extra_parts.append(f"β: {_beta:.2f}")
        if _rev_growth is not None:
            _extra_parts.append(f"売上成長率: {_rev_growth * 100:+.1f}%")
        if _op_margin is not None:
            _extra_parts.append(f"営業利益率: {_op_margin * 100:.1f}%")
        if _extra_parts:
            st.caption("　".join(_extra_parts))

        # ── 信用取引情報 ──────────────────────────────────────────
        st.divider()
        if _margin:
            st.markdown("**信用取引情報**")
            _mcols = st.columns(4)
            if _margin.get("buy_margin") is not None:
                _mcols[0].metric("信用買い残", f"{_margin['buy_margin']:,.0f} 株")
            if _margin.get("sell_margin") is not None:
                _mcols[1].metric("信用売り残", f"{_margin['sell_margin']:,.0f} 株")
            if _margin.get("lending_ratio") is not None:
                lr = _margin["lending_ratio"]
                lr_delta = "過熱" if lr >= 10 else ("買い多" if lr >= 3 else ("売り多" if lr <= 0.5 else "中立"))
                _mcols[2].metric("貸借倍率", f"{lr:.2f} 倍", lr_delta)
            if _margin.get("date"):
                _mcols[3].metric("基準日", _margin["date"])
        else:
            st.caption("信用残データなし（海外銘柄・上場廃止等）")

    # ════════════════════════════════════════════════════════════════
    # TAB 2: AI 総合分析
    # ════════════════════════════════════════════════════════════════
    with tab_ai:
        # ── 分析結果のキャッシュ管理 ──
        _cache_key = "dashboard_ai_cache"
        if _cache_key not in st.session_state:
            st.session_state[_cache_key] = load_daily(_cache_key, default={})

        _analyzed_key = f"{ticker}::{ai_provider}"
        _cached_result = st.session_state[_cache_key].get(_analyzed_key)

        btn_col, clear_col = st.columns([3, 1])

        if _cached_result:
            st.caption("✅ 本日の分析結果を表示中（キャッシュ済み・API消費なし）")
            if btn_col.button("再分析を実行（API消費あり）", key="main_ai_btn", use_container_width=True):
                _cached_result = None
                if _analyzed_key in st.session_state[_cache_key]:
                    del st.session_state[_cache_key][_analyzed_key]
                get_comprehensive_analysis.clear()
        else:
            if btn_col.button("AI総合分析を実行", type="primary", key="main_ai_btn", use_container_width=True):
                _cached_result = "__run__"

        if clear_col.button("🗑️ キャッシュクリア", key="main_ai_clear_btn", use_container_width=True,
                            help="前回の分析結果を削除して再実行します"):
            get_comprehensive_analysis.clear()
            if _analyzed_key in st.session_state[_cache_key]:
                del st.session_state[_cache_key][_analyzed_key]
                save_daily(_cache_key, st.session_state[_cache_key])
            st.rerun()

        if _cached_result and _cached_result != "__run__":
            _render_ai_results(_cached_result)
        elif _cached_result == "__run__":
            _ai_placeholder = st.empty()
            from modules.loading import show_loading
            _ai_placeholder.markdown("")
            show_loading("AI 分析を実行中...")
            _ai_result = get_comprehensive_analysis(
                ticker=ticker,
                company_name=company_name,
                tech_json=tech_json,
                fund_text=fund_text,
                news_titles=news_titles,
                margin_text=_margin_text,
                market_text=_market_text,
                provider=ai_provider,
                api_key=ai_api_key,
            )
            st.session_state[_cache_key][_analyzed_key] = _ai_result
            save_daily(_cache_key, st.session_state[_cache_key])
            st.rerun()
        else:
            st.caption(
                f"「AI総合分析を実行」ボタンを押すと、テクニカル・ファンダメンタル・ニュース・マーケット環境を"
                f"統合した分析レポートを {_provider_label} が生成します。"
            )

    # ════════════════════════════════════════════════════════════════
    # TAB 3: AI チャット
    # ════════════════════════════════════════════════════════════════
    with tab_chat:
        import markdown as _md
        from modules.icons import robot_avatar, render_user_bubble, render_ai_bubble, robot_chat_avatar

        _chat_key = f"chat_{ticker}_{ai_provider}"
        if _chat_key not in st.session_state:
            st.session_state[_chat_key] = []

        _chat_hdr, _chat_clr = st.columns([5, 1])
        _chat_hdr.caption(
            f"**{company_name}** について {_provider_label} に自由に質問できます。"
            "テクニカル・ファンダメンタル・信用残・マーケット環境データを渡しています。"
        )
        if _chat_clr.button("🗑️ 履歴クリア", key="chat_clear_btn", use_container_width=True):
            st.session_state[_chat_key] = []
            st.rerun()

        _chat_window = st.container(height=500, border=True)
        with _chat_window:
            if not st.session_state[_chat_key]:
                st.markdown(
                    f"""<div style='text-align:center;color:#6b7280;padding:2em 1em;
                        font-family:Inter,Noto Sans JP,sans-serif;font-size:0.82em;letter-spacing:0.04em;'>
                        {robot_avatar("lg")}
                        <br><br>
                        <b style="color:#b8b0a2;">{company_name} AIアナリスト</b><br><br>
                        テクニカル・ファンダメンタル・ニュース・マーケット環境を踏まえて回答します。<br>
                        <span style='font-size:0.9em;color:#505868;font-style:italic;'>
                        例:「今買い時ですか？」「RSIの数値をどう見ますか？」<br>
                        「決算はいつ？」「配当利回りは？」「リスクは？」
                        </span></div>""",
                    unsafe_allow_html=True,
                )
            # カスタムバブルで描画
            for _msg in st.session_state[_chat_key]:
                if _msg["role"] == "user":
                    st.markdown(render_user_bubble(_msg["content"]), unsafe_allow_html=True)
                else:
                    _ai_html = _md.markdown(_msg["content"], extensions=["tables", "fenced_code"])
                    st.markdown(render_ai_bubble(_ai_html, talking=False), unsafe_allow_html=True)

        if _user_input := st.chat_input(
            f"{company_name} について質問...", key="stock_chat_input"
        ):
            st.session_state[_chat_key].append({"role": "user", "content": _user_input})
            with _chat_window:
                st.markdown(render_user_bubble(_user_input), unsafe_allow_html=True)
                # 口パクロボット + スピナー
                _thinking_html = render_ai_bubble(
                    '<span style="color:#6b7280;font-style:italic;">回答を生成中...</span>',
                    talking=True,
                )
                _spinner_placeholder = st.empty()
                _spinner_placeholder.markdown(_thinking_html, unsafe_allow_html=True)
                _sys_prompt = build_chat_system_prompt(
                    ticker, company_name, tech_json, fund_text, _margin_text,
                    news_titles=news_titles,
                )
                _response = get_chat_response(
                    messages=st.session_state[_chat_key],
                    system_prompt=_sys_prompt,
                    provider=ai_provider,
                    api_key=ai_api_key,
                )
                # 口パク停止 → 通常表示に置換
                _resp_html = _md.markdown(_response, extensions=["tables", "fenced_code"])
                _spinner_placeholder.markdown(render_ai_bubble(_resp_html, talking=False), unsafe_allow_html=True)
            st.session_state[_chat_key].append({"role": "assistant", "content": _response})


if __name__ == "__main__":
    main()
