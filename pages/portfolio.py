"""
ポートフォリオ分析ページ
保有銘柄と株数を入力し、最新ニュースとAIで個別＋全体の分析を行う。
"""
import json
import os
import sys

import pandas as pd
import streamlit as st
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.styles import apply_theme

apply_theme()

from modules.persistence import load_into_session, save_from_session
from modules.data_loader import load_all_tse_stocks, load_tickers
from modules.events import fetch_latest_news
from modules.ai_analysis import (
    calc_technical_summary,
    prepare_analysis_inputs,
    _call_claude,
    _call_openai,
    _call_gemini,
    _parse_json,
    _classify_error,
)
from modules.fundamental import (
    fetch_fundamental_yfinance,
    fetch_fundamental_kabutan,
    fetch_financial_statements_jquants,
    format_fundamental_text,
)
from modules.margin import fetch_margin_data, format_margin_text
from modules.market_context import fetch_market_context_text

TICKERS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt"
)


# ─── ヘルパー ─────────────────────────────────────────────────────────────


def _get_api_key() -> str:
    """API キーを取得する。"""
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        key = ""
    if not key:
        key = st.session_state.get("portfolio_api_key", "")
    return key


@st.cache_data(ttl=300)
def _fetch_current_price(ticker: str) -> dict:
    """現在の株価情報を取得する。"""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist is None or hist.empty:
            return {}
        last_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else last_close
        change = last_close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        try:
            info = t.info or {}
        except Exception:
            info = {}
        return {
            "price": last_close,
            "change": change,
            "change_pct": change_pct,
            "name": info.get("longName") or info.get("shortName", ""),
            "currency": info.get("currency", "JPY"),
        }
    except Exception:
        return {}


@st.cache_data(ttl=3600)
def _portfolio_ai_analysis(
    ticker: str,
    company_name: str,
    shares: int,
    avg_cost: float,
    current_price: float,
    tech_json: str,
    fund_text: str,
    news_titles: tuple[str, ...],
    margin_text: str,
    market_text: str,
    provider: str,
    api_key: str,
) -> dict:
    """個別銘柄のポートフォリオ向けAI分析を行う。"""
    pnl = (current_price - avg_cost) * shares if avg_cost > 0 else 0
    pnl_pct = ((current_price / avg_cost - 1) * 100) if avg_cost > 0 else 0
    position_value = current_price * shares

    cost_section = ""
    if avg_cost > 0:
        cost_section = f"""
## ポジション情報
- 保有株数: {shares:,}株
- 取得単価: ¥{avg_cost:,.0f}
- 現在値: ¥{current_price:,.0f}
- 評価額: ¥{position_value:,.0f}
- 含み損益: ¥{pnl:,.0f}（{pnl_pct:+.1f}%）
"""
    else:
        cost_section = f"""
## ポジション情報
- 保有株数: {shares:,}株
- 現在値: ¥{current_price:,.0f}
- 評価額: ¥{position_value:,.0f}
"""

    try:
        tech = json.loads(tech_json)
    except Exception:
        tech = {}

    rsi = tech.get("rsi", "N/A")
    macd = tech.get("macd", {})
    news_text = "\n".join(f"- {t}" for t in news_titles[:15]) if news_titles else "最新ニュースなし"

    prompt = f"""あなたは CFA 資格を持つ日本株ポートフォリオアドバイザーです。
以下の保有銘柄について、個人投資家向けに具体的なアクションアドバイスを提供してください。

## 銘柄
{company_name} ({ticker})
{cost_section}
## テクニカル指標（直近）
- RSI(14): {rsi}
- MACD: {json.dumps(macd, ensure_ascii=False) if macd else 'N/A'}
- 52週高値比: {tech.get('pct_from_52w_high', 'N/A')}%
- 52週安値比: +{tech.get('pct_from_52w_low', 'N/A')}%
- ボリンジャー位置: {tech.get('bb_sigma', 'N/A')}σ

## ファンダメンタル
{fund_text}

{f"## 信用取引情報{chr(10)}{margin_text}" if margin_text else ""}

## 最新ニュース（直近30日）
{news_text}

{f"## マーケット環境{chr(10)}{market_text}" if market_text else ""}

## 分析と回答の指針
1. **現状評価**: この銘柄の現在のポジションを総合的に評価
2. **リスク警戒**: 今すぐ警戒すべきリスク要因を具体的に列挙
3. **アクション提案**: 以下の5段階から推奨アクションを選択
   - 「買い増し推奨」「保有継続」「一部利確推奨」「全売却推奨」「様子見」
4. **具体的な戦略**: 利確ライン・損切りラインの目安を提示
5. **注目イベント**: 今後1ヶ月で注視すべきイベントやタイミング

## 出力形式
以下の JSON **のみ** を出力してください。

```json
{{
  "action": "買い増し推奨" | "保有継続" | "一部利確推奨" | "全売却推奨" | "様子見",
  "action_reason": "推奨アクションの理由（3〜4文、具体的な数値根拠付き）",
  "risk_alerts": ["警戒すべきリスク1（具体的に）", "警戒すべきリスク2", "警戒すべきリスク3"],
  "opportunities": ["チャンス要因1", "チャンス要因2"],
  "target_price": "目標株価（円、レンジで）",
  "stop_loss": "損切りライン目安（円）",
  "key_events": ["注目イベント1（日付付き）", "注目イベント2"],
  "overall_assessment": "総合評価（5〜6文。ニュースの内容を踏まえた具体的な分析）",
  "news_impact": "最新ニュースの影響分析（3〜4文。具体的なニュースを引用して株価への影響を解説）",
  "score": 0〜100の整数（50=中立、0=即売り、100=強力買い増し）
}}
```"""

    try:
        if provider == "openai":
            text = _call_openai(prompt, api_key)
        elif provider == "gemini":
            text = _call_gemini(prompt, api_key)
        else:
            text = _call_claude(prompt, api_key)
        return {**_parse_json(text), "error": False}
    except Exception as e:
        return {
            "action": "分析エラー",
            "action_reason": _classify_error(str(e), provider),
            "risk_alerts": [],
            "opportunities": [],
            "target_price": "",
            "stop_loss": "",
            "key_events": [],
            "overall_assessment": "",
            "news_impact": "",
            "score": 50,
            "error": True,
        }


# ─── ポートフォリオ全体分析 ───────────────────────────────────────────────


def _portfolio_overall_analysis(
    holdings_summary: str,
    market_text: str,
    provider: str,
    api_key: str,
) -> dict:
    """ポートフォリオ全体のAI分析。"""
    prompt = f"""あなたは CFA 資格を持つポートフォリオマネージャーです。
以下のポートフォリオ全体を分析し、総合アドバイスを提供してください。

## 保有ポートフォリオ
{holdings_summary}

{f"## マーケット環境{chr(10)}{market_text}" if market_text else ""}

## 分析と回答の指針
1. **ポートフォリオ全体のバランス評価**: セクター分散、リスク集中度
2. **相関リスク**: 保有銘柄間の相関性と連鎖リスク
3. **マーケット環境との適合性**: 現在の市場環境でのポートフォリオ適切度
4. **リバランス提案**: 具体的な調整案
5. **全体的な警戒点**: ポートフォリオ全体で見た場合のリスク

## 出力形式
以下の JSON **のみ** を出力してください。

```json
{{
  "portfolio_score": 0〜100の整数（50=中立、ポートフォリオの健全性を表す）,
  "balance_assessment": "分散度・バランスの評価（3〜4文）",
  "correlation_risk": "銘柄間の相関リスク分析（3〜4文）",
  "market_fit": "現在の市場環境との適合性（3〜4文）",
  "rebalance_suggestions": ["具体的なリバランス提案1", "提案2", "提案3"],
  "top_risks": ["ポートフォリオ全体のリスク1", "リスク2", "リスク3"],
  "strategic_advice": "今後の戦略アドバイス（5〜6文）"
}}
```"""

    try:
        if provider == "openai":
            text = _call_openai(prompt, api_key)
        elif provider == "gemini":
            text = _call_gemini(prompt, api_key)
        else:
            text = _call_claude(prompt, api_key)
        return {**_parse_json(text), "error": False}
    except Exception as e:
        return {
            "portfolio_score": 50,
            "balance_assessment": _classify_error(str(e), provider),
            "correlation_risk": "",
            "market_fit": "",
            "rebalance_suggestions": [],
            "top_risks": [],
            "strategic_advice": "",
            "error": True,
        }


# ─── 表示ヘルパー ─────────────────────────────────────────────────────────


def _render_holding_card(
    ticker: str,
    name: str,
    shares: int,
    avg_cost: float,
    price_info: dict,
    analysis: dict | None,
) -> None:
    """保有銘柄カードを描画する。"""
    price = price_info.get("price", 0)
    change_pct = price_info.get("change_pct", 0)
    position_value = price * shares
    pnl = (price - avg_cost) * shares if avg_cost > 0 else 0
    pnl_pct = ((price / avg_cost - 1) * 100) if avg_cost > 0 else 0
    pnl_color = "#5ca08b" if pnl >= 0 else "#c45c5c"
    chg_color = "#5ca08b" if change_pct >= 0 else "#c45c5c"

    # カードヘッダー
    st.markdown(
        f"""<div style="
            background: rgba(10,15,26,0.5);
            border: 1px solid rgba(212,175,55,0.06); border-left: 2px solid {pnl_color};
            border-radius: 2px; padding: 20px 28px; margin-bottom: 8px;
        ">
            <div style="display:flex; align-items:baseline; gap:16px; flex-wrap:wrap;">
                <span style="font-family:'Cormorant Garamond',serif; font-size:1.2em; font-weight:400; color:#f0ece4; letter-spacing:0.04em;">
                    {name}
                </span>
                <span style="font-family:'Inter',sans-serif; font-size:0.65em; color:#6b7280; letter-spacing:0.15em; text-transform:uppercase;">
                    {ticker}
                </span>
                <span style="font-family:'IBM Plex Mono',monospace; font-size:1.2em; font-weight:400; color:#f0ece4; margin-left:auto;">
                    ¥{price:,.0f}
                </span>
                <span style="font-family:'IBM Plex Mono',monospace; font-size:0.85em; color:{chg_color};">
                    {change_pct:+.2f}%
                </span>
            </div>
            <div style="display:flex; gap:28px; margin-top:10px; font-family:'Inter',sans-serif; font-size:0.65em; color:#6b7280; letter-spacing:0.06em;">
                <span>{shares:,}株</span>
                <span>評価額 <b style="color:#f0ece4;">¥{position_value:,.0f}</b></span>
                {f"<span>取得単価 <b style='color:#b8b0a2;'>¥{avg_cost:,.0f}</b></span>" if avg_cost > 0 else ""}
                {f"<span>含み損益 <b style='color:{pnl_color};'>¥{pnl:,.0f} ({pnl_pct:+.1f}%)</b></span>" if avg_cost > 0 else ""}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    if analysis and not analysis.get("error"):
        # アクションバッジ
        action = analysis.get("action", "")
        score = int(analysis.get("score", 50))
        action_colors = {
            "買い増し推奨": "#5ca08b",
            "保有継続": "#d4af37",
            "一部利確推奨": "#e6913e",
            "全売却推奨": "#c45c5c",
            "様子見": "#6b7280",
        }
        ac = action_colors.get(action, "#6b7280")

        st.markdown(
            f"""<div style="display:flex; align-items:center; gap:16px; margin:8px 0 12px 0;">
                <span style="font-family:'Inter',sans-serif; font-size:0.7em; font-weight:600;
                     color:{ac}; background:rgba({_hex_to_rgb(ac)},0.1);
                     padding:6px 16px; border:1px solid rgba({_hex_to_rgb(ac)},0.2); border-radius:2px;
                     text-transform:uppercase; letter-spacing:0.12em;">
                    {action}
                </span>
                <span style="font-family:'IBM Plex Mono',monospace; font-size:0.75em; color:#6b7280;">
                    Score: {score}/100
                </span>
                {"<span style='font-family:Inter,sans-serif; font-size:0.65em; color:#6b7280;'>目標: " + analysis.get('target_price', '') + " ｜ 損切: " + analysis.get('stop_loss', '') + "</span>" if analysis.get('target_price') else ""}
            </div>""",
            unsafe_allow_html=True,
        )

        # 詳細展開
        with st.expander("分析詳細", expanded=False):
            if analysis.get("action_reason"):
                st.markdown(f"**推奨理由**\n\n{analysis['action_reason']}")

            if analysis.get("news_impact"):
                st.markdown(f"**ニュースの影響**\n\n{analysis['news_impact']}")

            if analysis.get("overall_assessment"):
                st.markdown(f"**総合評価**\n\n{analysis['overall_assessment']}")

            c1, c2 = st.columns(2)
            with c1:
                if analysis.get("risk_alerts"):
                    st.markdown("**警戒すべきリスク**")
                    for r in analysis["risk_alerts"]:
                        st.markdown(f"- {r}")
            with c2:
                if analysis.get("opportunities"):
                    st.markdown("**チャンス要因**")
                    for o in analysis["opportunities"]:
                        st.markdown(f"- {o}")

            if analysis.get("key_events"):
                st.markdown("**注目イベント**")
                for ev in analysis["key_events"]:
                    st.markdown(f"- {ev}")

    elif analysis and analysis.get("error"):
        st.error(analysis.get("action_reason", "分析エラー"))


def _hex_to_rgb(hex_color: str) -> str:
    """#RRGGBB → 'R,G,B' に変換。"""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


# ─── メイン ───────────────────────────────────────────────────────────────


def main() -> None:
    st.title("💼 ポートフォリオ分析")
    st.caption(
        "保有銘柄と株数を入力し、最新ニュース・テクニカル・ファンダメンタルを"
        "総合したAI分析で、個別銘柄ごとの行動アドバイスとポートフォリオ全体の"
        "リスク診断を受けられます。"
    )

    # ─── 銘柄候補のロード ─────────────────────────────────────────
    nikkei225 = load_tickers(TICKERS_PATH)
    all_tse, _ = load_all_tse_stocks()
    all_stocks = all_tse if all_tse else nikkei225
    stock_map = {s["code"]: s["name"] for s in all_stocks}

    # ─── セッションステート初期化（Cookieから復元）─────────────────
    load_into_session("portfolio_holdings", "portfolio_holdings", default=[])
    if "portfolio_results" not in st.session_state:
        st.session_state.portfolio_results = {}

    # ─── サイドバー: 銘柄追加 ─────────────────────────────────────
    with st.sidebar:
        st.header("保有銘柄の追加")

        # 検索
        search = st.text_input(
            "銘柄検索（コードまたは名前）",
            placeholder="例: 7203 or トヨタ",
            key="pf_search",
        )
        if search:
            matches = [
                s for s in all_stocks
                if search.lower() in s["code"].lower()
                or search.lower() in s["name"].lower()
            ][:20]
        else:
            matches = []

        if matches:
            options = [f"{s['code']} {s['name']}" for s in matches]
            selected = st.selectbox("候補", options, key="pf_select")
            selected_code = selected.split(" ")[0] if selected else ""
        else:
            selected_code = st.text_input(
                "銘柄コード",
                placeholder="例: 7203.T",
                key="pf_code_direct",
            )
            if selected_code and not selected_code.endswith(".T"):
                selected_code = f"{selected_code.strip()}.T"

        col_shares, col_cost = st.columns(2)
        with col_shares:
            shares = st.number_input("株数", min_value=1, value=100, step=100, key="pf_shares")
        with col_cost:
            avg_cost = st.number_input(
                "取得単価（任意）", min_value=0.0, value=0.0, step=100.0,
                key="pf_cost",
                help="0の場合は含み損益を計算しません",
            )

        if st.button("追加", use_container_width=True, type="primary"):
            if selected_code:
                code = selected_code.strip()
                if not code.endswith(".T"):
                    code = f"{code}.T"
                name = stock_map.get(code, "")
                # 重複チェック
                existing = [h for h in st.session_state.portfolio_holdings if h["code"] == code]
                if existing:
                    st.warning(f"{code} は既に追加されています")
                else:
                    st.session_state.portfolio_holdings.append({
                        "code": code,
                        "name": name,
                        "shares": int(shares),
                        "avg_cost": float(avg_cost),
                    })
                    save_from_session("portfolio_holdings", "portfolio_holdings")
                    st.rerun()

        st.divider()

        # API 設定
        st.header("AI 設定")
        provider = st.selectbox(
            "AIプロバイダー",
            ["claude", "openai", "gemini"],
            format_func=lambda x: {"claude": "Claude (Anthropic)", "openai": "ChatGPT (OpenAI)", "gemini": "Gemini (Google)"}.get(x, x),
            key="pf_provider",
        )
        custom_key = st.text_input(
            "APIキー（任意）",
            type="password",
            key="portfolio_api_key",
            help="未入力の場合は secrets.toml の ANTHROPIC_API_KEY を使用",
        )

    # ─── メインエリア ─────────────────────────────────────────────
    holdings = st.session_state.portfolio_holdings

    if not holdings:
        st.info("サイドバーから保有銘柄を追加してください。銘柄コードと株数を入力すると、AI分析を開始できます。")
        st.stop()

    # ─── 保有一覧テーブル ─────────────────────────────────────────
    st.subheader("保有銘柄一覧")

    # 銘柄リスト（編集・削除）
    to_remove = None
    changed = False
    for i, h in enumerate(holdings):
        name_display = h["name"] or h["code"]

        # 現在価格
        price_info = _fetch_current_price(h["code"])
        price = price_info.get("price", 0) if price_info else 0
        chg = price_info.get("change_pct", 0) if price_info else 0
        chg_color = "#5ca08b" if chg >= 0 else "#c45c5c"
        price_str = f"¥{price:,.0f} ({chg:+.2f}%)" if price else "取得中..."
        shares_str = f"{h['shares']:,}株"
        cost_str = f"取得単価 ¥{h['avg_cost']:,.0f}" if h["avg_cost"] > 0 else "取得単価: 未設定"
        pnl_str = ""
        if h["avg_cost"] > 0 and price > 0:
            pnl_val = (price - h["avg_cost"]) * h["shares"]
            pnl_pct = (price / h["avg_cost"] - 1) * 100
            pnl_label = "含み益" if pnl_val >= 0 else "含み損"
            pnl_str = f"　{pnl_label} ¥{abs(pnl_val):,.0f} ({pnl_pct:+.1f}%)"

        with st.expander(f"**{name_display}**　`{h['code']}`　　{shares_str}　{cost_str}　　{price_str}{pnl_str}", expanded=False):
            c1, c2, c3 = st.columns([2, 2, 1])
            new_shares = c1.number_input(
                "株数", min_value=1, value=h["shares"], step=100,
                key=f"edit_shares_{i}",
            )
            new_cost = c2.number_input(
                "取得単価 (¥)", min_value=0.0, value=float(h["avg_cost"]), step=100.0,
                key=f"edit_cost_{i}",
            )
            if c3.button("削除", key=f"rm_{i}", use_container_width=True):
                to_remove = i

            if new_shares != h["shares"] or new_cost != h["avg_cost"]:
                st.session_state.portfolio_holdings[i]["shares"] = int(new_shares)
                st.session_state.portfolio_holdings[i]["avg_cost"] = float(new_cost)
                changed = True

            # 損益表示
            if h["avg_cost"] > 0 and price > 0:
                pnl = (price - h["avg_cost"]) * h["shares"]
                pnl_pct = (price / h["avg_cost"] - 1) * 100
                pnl_color = "#5ca08b" if pnl >= 0 else "#c45c5c"
                st.markdown(
                    f"評価額 **¥{price * h['shares']:,.0f}** ｜ "
                    f"含み損益 <span style='color:{pnl_color};'>**¥{pnl:,.0f}** ({pnl_pct:+.1f}%)</span>",
                    unsafe_allow_html=True,
                )

    if changed:
        save_from_session("portfolio_holdings", "portfolio_holdings")

    if to_remove is not None:
        st.session_state.portfolio_holdings.pop(to_remove)
        st.session_state.portfolio_results = {}
        save_from_session("portfolio_holdings", "portfolio_holdings")
        st.rerun()

    st.divider()

    # ─── 分析実行 ─────────────────────────────────────────────────
    if st.button("AI分析を実行", use_container_width=True, type="primary"):
        api_key = _get_api_key()
        if not api_key and provider == "claude":
            st.error("APIキーが設定されていません。サイドバーでAPIキーを入力してください。")
            st.stop()

        provider = st.session_state.get("pf_provider", "claude")
        results = {}
        market_text = fetch_market_context_text()

        progress = st.progress(0)
        total = len(holdings)

        for idx, h in enumerate(holdings):
            ticker = h["code"]
            name = h["name"] or ticker
            status_text = f"分析中: {name} ({idx + 1}/{total})"
            progress.progress((idx) / total, text=status_text)

            try:
                # 株価データ取得
                t = yf.Ticker(ticker)
                df = t.history(period="1y", interval="1d")
                if df.empty:
                    results[ticker] = {
                        "error": True,
                        "action": "データ取得エラー",
                        "action_reason": f"{ticker} の株価データを取得できませんでした",
                    }
                    continue

                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)

                # 現在価格
                price_info = _fetch_current_price(ticker)
                current_price = price_info.get("price", float(df["Close"].iloc[-1]))

                # テクニカル
                tech_summary = calc_technical_summary(df)
                tech_json = json.dumps(tech_summary, ensure_ascii=False)

                # ファンダメンタル
                fund_data = fetch_fundamental_yfinance(ticker)
                jquants_data = fetch_financial_statements_jquants(ticker)
                kabutan_data = fetch_fundamental_kabutan(ticker)
                fund_text = format_fundamental_text(fund_data, jquants_data, kabutan=kabutan_data)

                # 最新ニュース（新しい統合関数を使用）
                latest_news = fetch_latest_news(ticker, name)
                news_titles = tuple(n["title"] for n in latest_news[:15])

                # 信用残
                margin_data = fetch_margin_data(ticker)
                margin_text_str = format_margin_text(margin_data)

                # AI分析
                analysis = _portfolio_ai_analysis(
                    ticker=ticker,
                    company_name=name,
                    shares=h["shares"],
                    avg_cost=h["avg_cost"],
                    current_price=current_price,
                    tech_json=tech_json,
                    fund_text=fund_text,
                    news_titles=news_titles,
                    margin_text=margin_text_str,
                    market_text=market_text,
                    provider=provider,
                    api_key=api_key,
                )
                analysis["price_info"] = price_info
                analysis["news_count"] = len(latest_news)
                analysis["news_sources"] = list({n["publisher"] for n in latest_news[:15]})
                results[ticker] = analysis

            except Exception as e:
                results[ticker] = {
                    "error": True,
                    "action": "分析エラー",
                    "action_reason": str(e)[:300],
                }

            progress.progress((idx + 1) / total, text=f"完了: {name}")

        # ポートフォリオ全体分析
        progress.progress(0.95, text="ポートフォリオ全体を分析中...")

        # 全体分析用のサマリー構築
        summary_lines = []
        total_value = 0
        for h in holdings:
            pi = _fetch_current_price(h["code"])
            price = pi.get("price", 0)
            val = price * h["shares"]
            total_value += val
            pnl_str = ""
            if h["avg_cost"] > 0:
                pnl = (price - h["avg_cost"]) * h["shares"]
                pnl_pct = (price / h["avg_cost"] - 1) * 100
                pnl_str = f" / 含み損益: ¥{pnl:,.0f}（{pnl_pct:+.1f}%）"

            r = results.get(h["code"], {})
            action = r.get("action", "N/A")
            score = r.get("score", "N/A")
            news_src = ", ".join(r.get("news_sources", []))
            summary_lines.append(
                f"- {h['name'] or h['code']} ({h['code']}): "
                f"{h['shares']:,}株 / 現在値¥{price:,.0f} / 評価額¥{val:,.0f}"
                f"{pnl_str} / AI判断: {action}(Score:{score})"
                f" / ニュースソース: {news_src}"
            )
        summary_lines.insert(0, f"ポートフォリオ合計評価額: ¥{total_value:,.0f}\n")

        overall = _portfolio_overall_analysis(
            holdings_summary="\n".join(summary_lines),
            market_text=market_text,
            provider=provider,
            api_key=api_key,
        )
        results["__portfolio_overall__"] = overall
        progress.progress(1.0, text="分析完了")

        st.session_state.portfolio_results = results
        st.rerun()

    # ─── 分析結果表示 ─────────────────────────────────────────────
    results = st.session_state.portfolio_results

    if not results:
        st.info("「AI分析を実行」ボタンを押すと、全銘柄を最新ニュースで分析します。")
        st.stop()

    # ポートフォリオ全体
    overall = results.get("__portfolio_overall__")
    if overall and not overall.get("error"):
        st.subheader("ポートフォリオ全体診断")
        pf_score = int(overall.get("portfolio_score", 50))

        st.markdown(
            f"""<div style="
                background: rgba(10,15,26,0.5);
                border: 1px solid rgba(212,175,55,0.08); border-left: 2px solid #d4af37;
                border-radius: 2px; padding: 24px 32px; margin-bottom: 16px;
            ">
                <div style="display:flex; align-items:center; gap:20px;">
                    <span style="font-family:'Cormorant Garamond',serif; font-size:1.3em; font-weight:400; color:#f0ece4; letter-spacing:0.06em;">
                        Portfolio Health
                    </span>
                    <span style="font-family:'IBM Plex Mono',monospace; font-size:1.4em; color:#d4af37;">
                        {pf_score}/100
                    </span>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3 = st.tabs(["バランス評価", "リスク分析", "戦略アドバイス"])

        with tab1:
            if overall.get("balance_assessment"):
                st.markdown(overall["balance_assessment"])
            if overall.get("market_fit"):
                st.markdown(f"**市場環境との適合性**\n\n{overall['market_fit']}")

        with tab2:
            if overall.get("correlation_risk"):
                st.markdown(f"**相関リスク**\n\n{overall['correlation_risk']}")
            if overall.get("top_risks"):
                st.markdown("**主要リスク**")
                for r in overall["top_risks"]:
                    st.markdown(f"- {r}")

        with tab3:
            if overall.get("strategic_advice"):
                st.markdown(overall["strategic_advice"])
            if overall.get("rebalance_suggestions"):
                st.markdown("**リバランス提案**")
                for s in overall["rebalance_suggestions"]:
                    st.markdown(f"- {s}")

        st.divider()

    # 個別銘柄結果
    st.subheader("個別銘柄分析")
    for h in holdings:
        ticker = h["code"]
        analysis = results.get(ticker)
        price_info = analysis.get("price_info", {}) if analysis else {}
        if not price_info:
            price_info = _fetch_current_price(ticker)

        # ニュースソース情報
        if analysis and analysis.get("news_sources"):
            news_info = f"ニュースソース: {', '.join(analysis['news_sources'])}（{analysis.get('news_count', 0)}件）"
        else:
            news_info = ""

        _render_holding_card(
            ticker=ticker,
            name=h["name"] or ticker,
            shares=h["shares"],
            avg_cost=h["avg_cost"],
            price_info=price_info,
            analysis=analysis,
        )

        if news_info:
            st.caption(news_info)


main()
