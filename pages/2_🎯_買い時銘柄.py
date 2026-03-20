"""
買い時・仕込み時銘柄スクリーナー

2段階方式:
  Phase 1: 全銘柄をルールベーススコアで絞り込み（4hキャッシュ）
  Phase 2: 上位候補のみAI詳細分析（24hキャッシュ）
"""
import os

import pandas as pd
import streamlit as st
import yfinance as yf
from streamlit_cookies_controller import CookieController

from modules.ai_analysis import get_comprehensive_analysis, prepare_analysis_inputs
from modules.data_loader import fetch_stock_data_max, load_all_tse_stocks, load_tickers
from modules.events import fetch_news_events
from modules.market_hours import market_status_label
from modules.styles import apply_theme

st.set_page_config(
    page_title="買い時銘柄 | 日本株ダッシュボード",
    page_icon="🎯",
    layout="wide",
)
apply_theme()

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")

_JUDGMENT_COLOR = {
    "強気買い": "#00c853",
    "買い":     "#4caf50",
    "中立":     "#9e9e9e",
    "売り":     "#ff9800",
    "強気売り": "#f44336",
}
_JUDGMENT_EMOJI = {
    "強気買い": "🔥",
    "買い":     "✅",
    "中立":     "➖",
    "売り":     "⚠️",
    "強気売り": "🔴",
}


# ─── スコアリング ────────────────────────────────────────────────────────

def _score_stock(df: pd.DataFrame) -> tuple[float, dict]:
    """
    ルールベース買いスコア（0〜100）と根拠テキストを返す。
    RSI・MACD・BB・52週安値比・SMA25上抜け・出来高急増 の6指標。
    """
    close  = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(dtype=float)
    score  = 0.0
    breakdown: dict[str, str] = {}

    # ── RSI(14) ──────────────────────────────────────────────────────
    if len(close) >= 15:
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean().replace(0, float("nan"))
        rsi_s = 100 - 100 / (1 + gain / loss)
        rsi   = float(rsi_s.iloc[-1]) if not pd.isna(rsi_s.iloc[-1]) else None
        if rsi is not None:
            if rsi < 30:
                score += 20; breakdown["RSI"] = f"{rsi:.1f}（売られ過ぎ, +20）"
            elif rsi < 40:
                score += 15; breakdown["RSI"] = f"{rsi:.1f}（回復途上, +15）"
            elif rsi < 50:
                score += 5;  breakdown["RSI"] = f"{rsi:.1f}（中立やや弱, +5）"

    # ── MACD(12/26/9) ────────────────────────────────────────────────
    if len(close) >= 35:
        macd_line = (close.ewm(span=12, adjust=False).mean()
                     - close.ewm(span=26, adjust=False).mean())
        signal    = macd_line.ewm(span=9, adjust=False).mean()
        hist      = macd_line - signal
        h_cur  = float(hist.iloc[-1])
        h_prev = float(hist.iloc[-2]) if len(hist) >= 2 else 0.0
        m_cur  = float(macd_line.iloc[-1])
        if h_cur > 0 and h_prev <= 0:
            score += 25; breakdown["MACD"] = "ゴールデンクロス直後（+25）"
        elif h_cur > 0 and m_cur < 0:
            score += 15; breakdown["MACD"] = "0線以下でヒスト+（上昇転換初期, +15）"
        elif h_cur > 0:
            score += 5;  breakdown["MACD"] = "ヒスト+（弱い強気, +5）"

    # ── ボリンジャーバンド σ位置 ──────────────────────────────────────
    if len(close) >= 20:
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        std_v  = float(bb_std.iloc[-1])
        if std_v > 0:
            sigma = (float(close.iloc[-1]) - float(bb_mid.iloc[-1])) / std_v
            if sigma < -2:
                score += 20; breakdown["BB"] = f"{sigma:.1f}σ（下限突破, +20）"
            elif sigma < -1:
                score += 12; breakdown["BB"] = f"{sigma:.1f}σ（下限付近, +12）"

    # ── 52週安値比（データが1年未満の場合は全期間の安値を代替使用）──────
    last  = float(close.iloc[-1])
    low52 = float(close.tail(min(len(close), 252)).min())
    pct_from_low = (last - low52) / low52 * 100 if low52 > 0 else 999.0
    if pct_from_low < 10:
        score += 15; breakdown["安値圏"] = f"52週安値+{pct_from_low:.1f}%（+15）"
    elif pct_from_low < 20:
        score += 8;  breakdown["安値圏"] = f"52週安値+{pct_from_low:.1f}%（+8）"

    # ── SMA25 上抜け（今日）────────────────────────────────────────
    if len(close) >= 26:
        sma25 = close.rolling(25).mean()
        if (float(close.iloc[-1]) > float(sma25.iloc[-1])
                and float(close.iloc[-2]) <= float(sma25.iloc[-2])):
            score += 10; breakdown["SMA25"] = "本日上抜け（+10）"

    # ── 出来高急増（5日/30日平均）───────────────────────────────────
    if len(volume) >= 30:
        v30 = float(volume.tail(30).mean())
        if v30 > 0:
            vr = float(volume.tail(5).mean()) / v30
            if vr > 2.0:
                score += 10; breakdown["出来高"] = f"{vr:.1f}倍（急増, +10）"
            elif vr > 1.5:
                score += 5;  breakdown["出来高"] = f"{vr:.1f}倍（増加, +5）"

    return min(score, 100.0), breakdown


def _get_rsi(close: pd.Series) -> float | None:
    """表示用RSI(14)値を返す。"""
    if len(close) < 15:
        return None
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean().replace(0, float("nan"))
    v     = float((100 - 100 / (1 + gain / loss)).iloc[-1])
    return round(v, 1) if not pd.isna(v) else None


# ─── Phase 1: ルールベーススキャン（4時間キャッシュ）────────────────────

@st.cache_data(ttl=3600 * 4, show_spinner=False)
def _run_screen(
    ticker_codes: tuple,
    ticker_names: tuple,
    ticker_markets: tuple,
    top_n: int = 30,
) -> list[dict]:
    """全銘柄をルールベーススコアリングし、上位 top_n を返す（辞書リスト）。"""
    name_map   = dict(zip(ticker_codes, ticker_names))
    market_map = dict(zip(ticker_codes, ticker_markets))
    single     = len(ticker_codes) == 1

    try:
        raw = yf.download(
            tickers=list(ticker_codes),
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        raise RuntimeError(f"yfinance ダウンロード失敗: {e}") from e

    results: list[dict] = []

    for code in ticker_codes:
        try:
            df = raw.copy() if single else raw[code].copy()
            if df is None or df.empty:
                continue
            df.columns = [str(c).capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df.dropna(subset=["Close"], inplace=True)
            if len(df) < 30:
                continue

            score, breakdown = _score_stock(df)
            if score < 20:   # 最低ライン未満はスキップ
                continue

            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2]) if len(df) >= 2 else last
            chg  = (last - prev) / prev * 100

            results.append({
                "ticker":     code,
                "name":       name_map.get(code, code),
                "market":     market_map.get(code, ""),
                "score":      score,
                "breakdown":  breakdown,
                "last_price": int(round(last)),
                "change_pct": round(chg, 2),
                "rsi":        _get_rsi(df["Close"]),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


# ─── Phase 2: 1銘柄AI分析 ────────────────────────────────────────────

def _run_ai_for_candidate(item: dict, provider: str, api_key: str) -> dict:
    """1銘柄のAI分析を実行し item にマージして返す。"""
    ticker = item["ticker"]
    name   = item["name"]
    try:
        df = fetch_stock_data_max(ticker)
        if df is None or df.empty or len(df) < 30:
            item["ai_result"] = None
            return item

        end   = df.index[-1].strftime("%Y-%m-%d")
        start = (df.index[-1] - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        news  = fetch_news_events(ticker, start, end, name)

        tech_json, fund_text, news_titles, margin_text, market_text = prepare_analysis_inputs(
            ticker, name, df, news
        )
        ai_result = get_comprehensive_analysis(
            ticker, name, tech_json, fund_text, news_titles,
            margin_text=margin_text,
            market_text=market_text,
            provider=provider,
            api_key=api_key,
        )
        item["ai_result"] = ai_result
        item["fund_text"] = fund_text
    except Exception as e:
        item["ai_result"] = {
            "error": True,
            "judgment": "中立",
            "overall_score": 0,
            "technical_score": 0,
            "fundamental_score": 0,
            "news_score": 0,
            "overall_detail": str(e),
            "opportunities": [],
            "risks": [],
        }
    return item


# ─── カード描画 ────────────────────────────────────────────────────────

def _render_card(rank: int, item: dict) -> None:
    """1銘柄の分析カードを描画する。"""
    ai       = item.get("ai_result") or {}
    judgment = ai.get("judgment", "中立")
    color    = _JUDGMENT_COLOR.get(judgment, "#9e9e9e")
    emoji    = _JUDGMENT_EMOJI.get(judgment, "❓")
    o_score  = ai.get("overall_score", 0)
    t_score  = ai.get("technical_score", 0)
    f_score  = ai.get("fundamental_score", 0)
    n_score  = ai.get("news_score", 0)
    chg      = item["change_pct"]
    chg_sign = "▲" if chg >= 0 else "▼"
    chg_color = "#00c853" if chg >= 0 else "#f44336"

    with st.container(border=True):
        # ── ヘッダー行 ────────────────────────────────────────────
        h1, h2, h3 = st.columns([5, 3, 2])
        with h1:
            st.markdown(
                f"<b style='font-size:1.1em'>{rank}位　{item['name']}</b>"
                f"　<span style='color:#aaa'>{item['ticker']}</span>"
                f"　<span style='font-size:.8em;color:#888'>{item['market']}</span>",
                unsafe_allow_html=True,
            )
        with h2:
            st.markdown(
                f"<span style='color:{color};font-size:1.3em;font-weight:bold'>"
                f"{emoji}&nbsp;{judgment}"
                f"</span>",
                unsafe_allow_html=True,
            )
        with h3:
            st.markdown(
                f"<b>¥{item['last_price']:,}</b>"
                f"　<span style='color:{chg_color}'>{chg_sign}{abs(chg):.2f}%</span>",
                unsafe_allow_html=True,
            )

        # ── スコアバー ────────────────────────────────────────────
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("総合スコア",   f"{o_score} / 100")
        sc2.metric("テクニカル",   f"{t_score} / 100")
        sc3.metric("ファンダ",     f"{f_score} / 100")
        sc4.metric("ニュース",     f"{n_score} / 100")

        # ── 買いシグナル根拠タグ ──────────────────────────────────
        if item.get("breakdown"):
            parts = []
            for k, v in item["breakdown"].items():
                short = v.split("（")[0]
                parts.append(f"**{k}** {short}")
            st.caption("📌 " + "　".join(parts))

        # ── AI分析テキスト（常時表示）────────────────────────────
        overall = ai.get("overall_detail", "")
        if overall and not ai.get("error"):
            st.markdown(
                f"<div style='background:#1a1a2e;padding:10px 14px;border-radius:6px;"
                f"border-left:3px solid {color};margin:6px 0'>"
                f"<b>総合判断</b>　{overall}"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ── 詳細展開（チャンス・リスク・各指標解説）────────────────
        with st.expander("📋 詳細分析を見る"):
            # テクニカル・ファンダ・ニュース解説
            d1, d2, d3 = st.columns(3)
            if ai.get("technical_detail"):
                d1.markdown(f"**テクニカル**\n\n{ai['technical_detail']}")
            if ai.get("fundamental_detail"):
                d2.markdown(f"**ファンダメンタル**\n\n{ai['fundamental_detail']}")
            if ai.get("news_detail"):
                d3.markdown(f"**ニュース**\n\n{ai['news_detail']}")

            # チャンス・リスク
            opp_list  = ai.get("opportunities", [])
            risk_list = ai.get("risks", [])
            if opp_list or risk_list:
                st.divider()
                col_opp, col_risk = st.columns(2)
                with col_opp:
                    st.markdown("**チャンス・強み**")
                    for o in opp_list:
                        st.markdown(f"✅ {o}")
                with col_risk:
                    st.markdown("**リスク・注意点**")
                    for r in risk_list:
                        st.markdown(f"⚠️ {r}")

            # ルールスコア内訳
            if item.get("breakdown"):
                st.divider()
                st.markdown("**スクリーニングスコア内訳**")
                for k, v in item["breakdown"].items():
                    st.markdown(f"- {k}: {v}")
            st.caption(f"ルールスコア: {item['score']:.0f} / 100　RSI: {item.get('rsi') or 'N/A'}")

        # ── チャートボタン ────────────────────────────────────────
        if st.button(
            "📈 チャートで詳細確認",
            key=f"chart_{item['ticker']}_{rank}",
            type="primary",
        ):
            st.session_state["calendar_selected_ticker"] = item["ticker"]
            st.switch_page("app.py")

    st.write("")  # カード間の余白


# ─── メイン ─────────────────────────────────────────────────────────────

def main() -> None:
    st.title("🎯 買い時・仕込み時銘柄スクリーナー")
    st.caption(
        "テクニカル指標（RSI・MACD・BB・出来高）で全銘柄をスクリーニングし、"
        "上位候補をAIが総合分析。今最も仕込みどきの銘柄を理由とともに提示します。"
    )

    _cookies = CookieController()

    nikkei225    = load_tickers(TICKERS_PATH)
    all_tse, _   = load_all_tse_stocks()
    prime_stocks = [t for t in all_tse if "プライム" in t.get("market", "")] if all_tse else []

    # ─── サイドバー ─────────────────────────────────────────────
    with st.sidebar:
        st.header("スキャン設定")

        # ── ユニバース選択 ──────────────────────────────────────
        universe_opts = ["日経225"]
        if prime_stocks:
            universe_opts.append(f"東証プライム（{len(prime_stocks):,}銘柄）")
        universe_choice = st.selectbox("スキャン対象", universe_opts)

        if "プライム" in universe_choice:
            scan_items = prime_stocks
        else:
            scan_items = nikkei225

        if len(scan_items) > 300:
            st.warning(
                f"⚠️ {len(scan_items):,} 銘柄のスキャンは初回 3〜5 分かかります。"
                "（結果は4時間キャッシュされます）"
            )

        top_n = st.slider("AI分析する上位銘柄数", 5, 30, 20, step=5)

        # ── セクターフィルター ──────────────────────────────────
        if all_tse and len(scan_items) > 50:
            sectors = sorted({t.get("sector", "") for t in scan_items if t.get("sector")})
            if sectors:
                selected_sectors = st.multiselect("セクターフィルター（空=全て）", sectors)
                if selected_sectors:
                    scan_items = [t for t in scan_items if t.get("sector") in selected_sectors]

        st.divider()
        st.subheader("🤖 AI 設定")

        ai_provider = st.selectbox(
            "プロバイダー",
            options=["claude", "openai", "gemini"],
            format_func=lambda x: {
                "claude": "Claude (Anthropic)",
                "openai": "ChatGPT (OpenAI)",
                "gemini": "Gemini (Google)",
            }[x],
            key="buy_ai_provider",
        )

        if "ai_api_keys" not in st.session_state:
            st.session_state.ai_api_keys = {}

        _has_owner_claude_key = bool(st.secrets.get("ANTHROPIC_API_KEY", ""))
        if ai_provider == "claude" and _has_owner_claude_key:
            st.caption("✅ Anthropic キー設定済み（共用）")
            ai_api_key = ""
        else:
            _placeholder  = {"claude": "sk-ant-...", "openai": "sk-...", "gemini": "AIza..."}[ai_provider]
            _widget_key   = f"buy_ai_key_{ai_provider}"
            _valid_pfx    = {"claude": "sk-ant-", "openai": "sk-", "gemini": "AIza"}
            _prefix       = _valid_pfx.get(ai_provider, "")
            _cookie_key   = f"apikey_{ai_provider}"

            if _widget_key not in st.session_state:
                _saved = st.session_state.ai_api_keys.get(ai_provider, "")
                if not _saved:
                    _saved = _cookies.get(_cookie_key) or ""
                if not _saved.isascii() or (_saved and _prefix and not _saved.startswith(_prefix)):
                    _saved = ""
                st.session_state[_widget_key] = _saved

            ai_api_key = st.text_input(
                "API キー",
                type="password",
                placeholder=_placeholder,
                help="入力したキーはブラウザに1日間保存されます",
                key=_widget_key,
            )

            if not ai_api_key or (_prefix and ai_api_key.startswith(_prefix)):
                st.session_state.ai_api_keys[ai_provider] = ai_api_key
                if ai_api_key:
                    _cookies.set(_cookie_key, ai_api_key, max_age=86400)

            if ai_api_key:
                st.caption("✅ キー保存済み")

        st.divider()
        st.caption(market_status_label())
        scan_btn = st.button("🔍 スキャン開始", type="primary", use_container_width=True)

    # ─── スキャン実行 ────────────────────────────────────────────
    if scan_btn:
        ticker_codes   = tuple(t["code"]           for t in scan_items)
        ticker_names   = tuple(t.get("name", "")    for t in scan_items)
        ticker_markets = tuple(t.get("market", "")  for t in scan_items)

        with st.status("スキャン実行中...", expanded=True) as status:
            # Phase 1: ルールベーススクリーニング
            st.write(f"📊 Phase 1: {len(scan_items):,} 銘柄をスクリーニング中...")
            try:
                candidates = _run_screen(ticker_codes, ticker_names, ticker_markets, top_n=top_n)
            except Exception as e:
                st.error(f"スキャン失敗: {e}")
                return
            st.write(f"✅ {len(candidates)} 候補銘柄を発見（スコア上位）")

            # Phase 2: AI詳細分析
            st.write(f"🤖 Phase 2: 上位 {len(candidates)} 銘柄をAI分析中...")
            final_results: list[dict] = []
            prog = st.progress(0, text="分析中...")
            for i, item in enumerate(candidates):
                result = _run_ai_for_candidate(item, ai_provider, ai_api_key)
                final_results.append(result)
                prog.progress(
                    (i + 1) / max(len(candidates), 1),
                    text=f"({i + 1}/{len(candidates)}) {item['name']} 完了",
                )

            status.update(label="✅ 分析完了！", state="complete", expanded=False)

        # AIスコア降順でソート
        final_results.sort(
            key=lambda x: (x.get("ai_result") or {}).get("overall_score", 0),
            reverse=True,
        )

        buy_cnt = sum(
            1 for r in final_results
            if (r.get("ai_result") or {}).get("judgment") in ("強気買い", "買い")
        )
        st.session_state["buy_scan_results"] = final_results
        st.session_state["buy_scan_meta"] = {
            "universe":   universe_choice.split("（")[0],
            "total":      len(scan_items),
            "candidates": len(candidates),
            "buy_cnt":    buy_cnt,
        }

    # ─── 結果表示 ────────────────────────────────────────────────
    results: list[dict] | None = st.session_state.get("buy_scan_results")
    meta: dict                  = st.session_state.get("buy_scan_meta", {})

    if results is None:
        st.info("サイドバーの **「スキャン開始」** を押してください。")
        with st.expander("スクリーニング条件の説明", expanded=True):
            st.markdown("""
## 2段階スクリーニング

### Phase 1: ルールベーススコアリング（全銘柄対象）

| 指標 | 条件 | 点数 |
|------|------|------|
| RSI(14) | < 30（売られ過ぎ） | +20 |
| RSI(14) | 30〜40（回復途上） | +15 |
| MACD | ゴールデンクロス直後 | +25 |
| MACD | 0線以下でヒスト+（転換初期） | +15 |
| BB σ | < −2σ（下限突破） | +20 |
| BB σ | −2〜−1σ（下限付近） | +12 |
| 52週安値比 | +10%以内 | +15 |
| 52週安値比 | +10〜20% | +8 |
| SMA25 | 本日上抜け | +10 |
| 出来高比 | 5日/30日 > 2.0× | +10 |

20点以上の銘柄を上位N件に絞り込み。

### Phase 2: AI 総合分析（上位候補のみ）

テクニカル・ファンダメンタル・ニュースを統合してAIが最終判定。
「強気買い」「買い」と判断した銘柄を理由とともに上位表示します。
            """)
        return

    # ── サマリーメトリクス ────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("スキャン対象",   f"{meta.get('total', 0):,} 銘柄",  meta.get("universe", ""))
    c2.metric("候補銘柄",       f"{meta.get('candidates', 0)} 件",  "ルールスコア上位")
    c3.metric("買いシグナル",   f"{meta.get('buy_cnt', 0)} 件",     "強気買い + 買い")
    c4.metric("AI分析済み",     f"{len(results)} 件")

    st.divider()

    if not results:
        st.warning("条件に合致する銘柄が見つかりませんでした。スキャン対象を変更してみてください。")
        return

    # ── ランキングカード ─────────────────────────────────────────
    for rank, item in enumerate(results, 1):
        _render_card(rank, item)


if __name__ == "__main__":
    main()
