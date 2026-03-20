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

import xml.etree.ElementTree as _ET

import requests as _requests

from modules.ai_analysis import get_comprehensive_analysis, prepare_analysis_inputs
from modules.data_loader import fetch_stock_data_max, load_all_tse_stocks, load_tickers
from modules.events import fetch_news_events
from modules.market_context import fetch_market_context_text, fetch_market_snapshot, calc_derived_indicators
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
    ルールベース買いスコア（0〜200）と根拠テキストを返す。
    テクニカル6指標 + トレンド転換 + 出来高の質 = 最大200点。
    Phase 1 では純テクニカルのみ（ファンダ・信用残は Phase 1.5 で加減点）。
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

    # ── 52週安値比 ───────────────────────────────────────────────────
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

    # ══════════════════════════════════════════════════════════════════
    # 新規追加: トレンド転換の確認
    # ══════════════════════════════════════════════════════════════════
    if len(close) >= 30:
        sma25_series = close.rolling(25).mean()
        # SMA25の傾き（5日間の変化率）
        sma25_now  = float(sma25_series.iloc[-1])
        sma25_5ago = float(sma25_series.iloc[-6]) if len(sma25_series) >= 6 else sma25_now
        if sma25_5ago > 0:
            sma25_slope = (sma25_now - sma25_5ago) / sma25_5ago * 100
            if sma25_slope > 0.5:
                score += 15; breakdown["トレンド転換"] = f"SMA25上昇転換（傾き+{sma25_slope:.1f}%, +15）"
            elif sma25_slope > 0:
                score += 8;  breakdown["トレンド転換"] = f"SMA25横ばい→上昇（+{sma25_slope:.2f}%, +8）"
            elif sma25_slope < -1.0:
                score -= 10; breakdown["下降トレンド"] = f"SMA25下降中（{sma25_slope:.1f}%, -10）⚠️"

    # SMA75上昇でさらにボーナス（中期トレンド確認）
    if len(close) >= 80:
        sma75_series = close.rolling(75).mean()
        sma75_now  = float(sma75_series.iloc[-1])
        sma75_5ago = float(sma75_series.iloc[-6])
        if sma75_5ago > 0 and (sma75_now - sma75_5ago) / sma75_5ago * 100 > 0.3:
            score += 8; breakdown["中期トレンド"] = "SMA75も上昇中（+8）"

    # ══════════════════════════════════════════════════════════════════
    # 新規追加: 出来高の質（上昇日の出来高増のみ加点）
    # ══════════════════════════════════════════════════════════════════
    if len(volume) >= 30 and len(close) >= 30:
        v30 = float(volume.tail(30).mean())
        if v30 > 0:
            # 直近5日の上昇日出来高 vs 下落日出来高
            recent = df.tail(10)
            up_days   = recent[recent["Close"] >= recent["Open"]]
            down_days = recent[recent["Close"] < recent["Open"]]
            up_vol   = float(up_days["Volume"].mean()) if len(up_days) > 0 else 0
            down_vol = float(down_days["Volume"].mean()) if len(down_days) > 0 else 0

            if up_vol > 0 and down_vol > 0:
                vol_quality = up_vol / down_vol
                if vol_quality > 1.5 and up_vol / v30 > 1.2:
                    score += 12; breakdown["出来高の質"] = f"上昇日出来高÷下落日出来高={vol_quality:.1f}倍（+12）"
                elif vol_quality > 1.2:
                    score += 6;  breakdown["出来高の質"] = f"上昇日出来高÷下落日出来高={vol_quality:.1f}倍（+6）"

            # 従来の出来高急増も残す
            vr = float(volume.tail(5).mean()) / v30
            if vr > 2.0:
                score += 8; breakdown["出来高急増"] = f"{vr:.1f}倍（+8）"
            elif vr > 1.5:
                score += 4; breakdown["出来高増加"] = f"{vr:.1f}倍（+4）"

    return max(score, 0.0), breakdown


# ─── Phase 1.5: ファンダメンタル＋信用残で加減点 ──────────────────────

def _adjust_score_fundamental(item: dict, ticker: str) -> dict:
    """ファンダメンタル・信用残データでスコアを加減点する。"""
    from modules.fundamental import fetch_fundamental_yfinance, fetch_fundamental_kabutan
    from modules.margin import fetch_margin_data

    score = item["score"]
    breakdown = item["breakdown"].copy()

    # ── ファンダメンタル ─────────────────────────────────────────
    try:
        fund_yf = fetch_fundamental_yfinance(ticker)
        fund_kb = fetch_fundamental_kabutan(ticker)
    except Exception:
        fund_yf, fund_kb = {}, {}

    per = fund_kb.get("per") or fund_yf.get("per")
    pbr = fund_kb.get("pbr") or fund_yf.get("pbr")
    div_kb = fund_kb.get("dividend_yield")
    div_yf = fund_yf.get("dividend_yield")
    div_yield = div_kb if div_kb is not None else ((div_yf * 100) if div_yf else None)
    roe = fund_yf.get("roe")

    if per is not None:
        if 0 < per <= 10:
            score += 15; breakdown["PER割安"] = f"PER {per:.1f}倍（+15）"
        elif 0 < per <= 15:
            score += 8;  breakdown["PER割安"] = f"PER {per:.1f}倍（+8）"
        elif per > 50:
            score -= 8;  breakdown["PER割高"] = f"PER {per:.1f}倍（-8）⚠️"
        elif per < 0:
            score -= 15; breakdown["赤字"] = f"PER {per:.1f}倍（赤字, -15）⚠️"

    if pbr is not None:
        if 0 < pbr < 0.8:
            score += 10; breakdown["PBR割安"] = f"PBR {pbr:.2f}倍（+10）"
        elif 0 < pbr < 1.0:
            score += 5;  breakdown["PBR割安"] = f"PBR {pbr:.2f}倍（+5）"

    if div_yield is not None and div_yield > 0:
        if div_yield >= 4.0:
            score += 12; breakdown["高配当"] = f"配当 {div_yield:.1f}%（+12）"
        elif div_yield >= 3.0:
            score += 6;  breakdown["好配当"] = f"配当 {div_yield:.1f}%（+6）"

    if roe is not None:
        if roe >= 0.15:
            score += 8; breakdown["高ROE"] = f"ROE {roe*100:.1f}%（+8）"
        elif roe >= 0.08:
            score += 4; breakdown["ROE合格"] = f"ROE {roe*100:.1f}%（+4）"
        elif roe < 0:
            score -= 5; breakdown["ROEマイナス"] = f"ROE {roe*100:.1f}%（-5）⚠️"

    item["per"] = per
    item["pbr"] = pbr
    item["div_yield"] = div_yield

    # ── 信用残フィルター ─────────────────────────────────────────
    try:
        margin = fetch_margin_data(ticker)
    except Exception:
        margin = {}

    if margin:
        lr = margin.get("lending_ratio")
        buy_margin = margin.get("buy_margin")
        sell_margin = margin.get("sell_margin")

        if lr is not None:
            if lr < 1.0 and sell_margin and sell_margin > 0:
                # 売り残 > 買い残 → ショートカバー期待
                score += 10; breakdown["信用売り超"] = f"貸借倍率 {lr:.2f}倍（売り超, +10）"
            elif lr > 5.0:
                # 買い残過多 → 将来の売り圧力
                score -= 8; breakdown["買い残過多"] = f"貸借倍率 {lr:.1f}倍（-8）⚠️"

    item["score"] = max(score, 0.0)
    item["breakdown"] = breakdown
    return item


# ─── セクター強弱の計算 ───────────────────────────────────────────

@st.cache_data(ttl=3600 * 4, show_spinner=False)
def _calc_sector_strength(
    ticker_codes: tuple, ticker_names: tuple, ticker_markets: tuple,
) -> dict[str, float]:
    """
    セクター別の直近5日間平均騰落率を計算する。
    強いセクターに属する銘柄にボーナス、弱いセクターに減点。
    """
    from modules.data_loader import load_all_tse_stocks
    all_tse, _ = load_all_tse_stocks()
    if not all_tse:
        return {}

    # セクター別に代表5銘柄の5日リターンを平均
    sector_tickers: dict[str, list[str]] = {}
    for t in all_tse:
        sec = t.get("sector", "")
        if sec:
            sector_tickers.setdefault(sec, []).append(t["code"])

    sector_scores: dict[str, float] = {}
    for sec, codes in sector_tickers.items():
        sample = codes[:5]  # 先頭5銘柄をサンプル
        try:
            raw = yf.download(sample, period="10d", interval="1d",
                              progress=False, auto_adjust=True, threads=True)
            if raw is None or raw.empty:
                continue
            returns = []
            single = len(sample) == 1
            for code in sample:
                try:
                    df = raw.copy() if single else raw[code].copy()
                    if df is None or df.empty:
                        continue
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [str(c[0]).capitalize() for c in df.columns]
                    else:
                        df.columns = [str(c).capitalize() for c in df.columns]
                    if "Close" not in df.columns:
                        continue
                    df.dropna(subset=["Close"], inplace=True)
                    if len(df) >= 2:
                        ret = (float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-6])) / float(df["Close"].iloc[-6]) * 100
                        returns.append(ret)
                except Exception:
                    continue
            if returns:
                sector_scores[sec] = round(sum(returns) / len(returns), 2)
        except Exception:
            continue

    return sector_scores


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


# ─── 市場ニュース取得（Google News RSS）──────────────────────────────

@st.cache_data(ttl=3600)  # 1時間キャッシュ
def _fetch_market_news() -> list[str]:
    """Google News RSSから市場・地政学・経済ニュースの見出しを取得する。"""
    queries = [
        "株式市場 日経平均",
        "地政学リスク 株 影響",
        "米国株 市場 経済",
        "原油 金利 為替 市場",
        "戦争 紛争 制裁 経済",
    ]
    titles: list[str] = []
    seen: set[str] = set()

    for q in queries:
        try:
            url = f"https://news.google.com/rss/search?q={q}&hl=ja&gl=JP&ceid=JP:ja"
            r = _requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                continue
            root = _ET.fromstring(r.content)
            for item in root.findall(".//item")[:8]:
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    t = title_el.text.strip()
                    if t not in seen:
                        seen.add(t)
                        titles.append(t)
        except Exception:
            continue

    return titles[:30]


# ─── 日本株全体の相場観 AI 分析 ──────────────────────────────────────

def _build_market_outlook_prompt(market_text: str, snapshot: dict, derived: dict, news: list[str]) -> str:
    """日本株市場全体の売買判断プロンプトを生成する。"""
    # 主要指数の変動をまとめる
    indices = []
    for name in ["日経平均", "TOPIX（ETF）", "S&P 500", "ナスダック総合"]:
        d = snapshot.get(name)
        if d:
            indices.append(f"- {name}: {d['value']:,.0f}（前日比{d['change_pct']:+.1f}%）")
    indices_text = "\n".join(indices) if indices else "データなし"

    # ニュース
    news_text = "\n".join(f"- {t}" for t in news[:25]) if news else "ニュース取得なし"

    return f"""あなたは日本株市場の上級ストラテジストです。
以下の市場データと**最新ニュース**を分析し、**今、日本株全体として買い時か・売り時か・現状維持か** を判断してください。

## 主要指数
{indices_text}

{market_text}

## 最新の市場・地政学ニュース（直近）
{news_text}

## 分析の視点
1. VIXとSKEWから市場のリスク選好度を判断
2. イールドカーブ（長短金利差）から景気サイクルの位置を判断
3. ドル円の動向が日本株に与える影響
4. SOX・ラッセル2000からグローバルなリスクオン/オフを判断
5. コモディティ（金・原油・銅）からインフレ/景気の方向性を判断
6. マクロ経済指標（CPI・雇用・GDP等）があればそれも考慮
7. **地政学リスク（戦争・紛争・制裁）が原油・サプライチェーン・市場心理に与える影響を重視**
8. **ニュースから読み取れるカタリスト（政策変更・貿易摩擦・軍事行動等）を具体的に分析**

## 出力形式（このJSONのみ出力）
```json
{{
  "market_judgment": "積極買い" | "買い優勢" | "中立・様子見" | "売り優勢" | "リスク回避",
  "score": 0〜100の整数（50=中立、高い=強気、低い=弱気）,
  "summary": "4〜5文の相場観サマリー。指標の数値とニュースの具体的事実を引用して根拠を示す",
  "bull_factors": ["強気要因1（数値やニュース根拠付き）", "強気要因2", "強気要因3"],
  "bear_factors": ["弱気要因1（数値やニュース根拠付き）", "弱気要因2", "弱気要因3"],
  "geopolitical": "地政学リスクの現状分析（2〜3文。戦争・紛争・制裁がエネルギー価格やサプライチェーン、市場心理に与える影響を具体的に）",
  "strategy": "今週〜今月の投資戦略を3〜4文で具体的に提案。セクター配分やリスクヘッジも含む"
}}
```"""


@st.cache_data(ttl=3600 * 4)  # 4時間キャッシュ
def _get_market_outlook(market_text: str, news_tuple: tuple, provider: str, api_key: str) -> dict:
    """日本株全体の相場観をAIで分析する。"""
    import json
    import re

    snapshot = fetch_market_snapshot()
    derived = calc_derived_indicators(snapshot)
    prompt = _build_market_outlook_prompt(market_text, snapshot, derived, list(news_tuple))

    try:
        if provider == "claude":
            import anthropic
            key = api_key.strip()
            if not key:
                try:
                    key = st.secrets.get("ANTHROPIC_API_KEY", "")
                except Exception:
                    key = ""
            if not key:
                return {"error": "APIキーが設定されていません"}
            client = anthropic.Anthropic(api_key=key)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key.strip())
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.choices[0].message.content
        elif provider == "gemini":
            import requests as _req
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
            resp = _req.post(
                url,
                params={"key": api_key.strip()},
                headers={"Content-Type": "application/json; charset=utf-8"},
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return {"error": f"不明なプロバイダー: {provider}"}

        # JSONパース
        text = text.strip()
        if "```" in text:
            for part in text.split("```"):
                part = part.strip().lstrip("json").strip()
                try:
                    return json.loads(part)
                except json.JSONDecodeError:
                    continue
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    except Exception as e:
        return {"error": str(e)[:300]}


_MARKET_JUDGMENT_CONFIG = {
    "積極買い":   ("#00c853", "🔥"),
    "買い優勢":   ("#4caf50", "📈"),
    "中立・様子見": ("#9e9e9e", "➡️"),
    "売り優勢":   ("#ff9800", "📉"),
    "リスク回避": ("#f44336", "🛡️"),
}


def _render_market_outlook(result: dict) -> None:
    """日本株全体の相場観を描画する。"""
    if result.get("error"):
        st.error(f"相場分析エラー: {result['error']}")
        return

    judgment = result.get("market_judgment", "中立・様子見")
    score = result.get("score", 50)
    summary = result.get("summary", "")
    strategy = result.get("strategy", "")
    geopolitical = result.get("geopolitical", "")
    bulls = result.get("bull_factors", [])
    bears = result.get("bear_factors", [])
    color, emoji = _MARKET_JUDGMENT_CONFIG.get(judgment, ("#9e9e9e", "➡️"))

    # ヘッダーバナー
    st.markdown(
        f"""<div style="
            background: linear-gradient(135deg, #101c30 0%, #0d1929 100%);
            border: 1px solid #1e2d40; border-left: 4px solid {color};
            border-radius: 8px; padding: 18px 24px; margin-bottom: 12px;
        ">
            <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
                <span style="font-size:2em;">{emoji}</span>
                <div>
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:1.2em; font-weight:700; color:{color};">
                        日本株全体: {judgment}
                    </div>
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.8em; color:#4a7a8a; margin-top:4px;">
                        市場スコア: {score} / 100
                    </div>
                </div>
                <div style="margin-left:auto; max-width:55%; font-family:'IBM Plex Sans JP',sans-serif; font-size:0.88em; color:#c9d6e3; line-height:1.6;">
                    {summary}
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # 強気・弱気要因
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📈 強気要因**")
        for b in bulls:
            st.markdown(f"<span style='color:#4caf50'>✅</span> {b}", unsafe_allow_html=True)
    with c2:
        st.markdown("**📉 弱気要因**")
        for b in bears:
            st.markdown(f"<span style='color:#f44336'>⚠️</span> {b}", unsafe_allow_html=True)

    # 地政学リスク + 投資戦略
    c3, c4 = st.columns(2)
    with c3:
        if geopolitical:
            st.markdown("**🌍 地政学リスク分析**")
            st.markdown(f"<div style='font-size:0.88em;line-height:1.6;'>{geopolitical}</div>", unsafe_allow_html=True)
    with c4:
        st.markdown("**🎯 投資戦略**")
        st.markdown(f"<div style='font-size:0.88em;line-height:1.6;'>{strategy}</div>", unsafe_allow_html=True)


# ─── メイン ─────────────────────────────────────────────────────────────

def main() -> None:
    st.title("🎯 買い時・仕込み時銘柄スクリーナー")
    st.caption(
        "テクニカル（RSI・MACD・BB・トレンド転換・出来高の質）+"
        "ファンダメンタル（PER・PBR・配当・ROE）+"
        "信用残・セクター強弱で全銘柄をスコアリングし、上位候補をAIが総合分析。"
    )

    _cookies = CookieController()

    # ─── 日本株全体の相場観（ページ最上部）──────────────────────
    _market_text = fetch_market_context_text()
    if _market_text:
        # APIキー取得（secrets優先）
        try:
            _outlook_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            _outlook_key = ""
        _outlook_provider = "claude" if _outlook_key else ""

        if _outlook_provider:
            _market_news = tuple(_fetch_market_news())
            with st.spinner("市場ニュース＋指標データからAIが相場観を分析中..."):
                _outlook = _get_market_outlook(_market_text, _market_news, _outlook_provider, _outlook_key)
            _render_market_outlook(_outlook)
            st.divider()

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
            st.write(f"✅ {len(candidates)} 候補銘柄を発見（テクニカルスコア上位）")

            # Phase 1.5: ファンダメンタル + 信用残 + セクター強弱で加減点
            st.write(f"📊 Phase 1.5: ファンダメンタル・信用残・セクター強弱で加減点中...")
            _sector_scores = _calc_sector_strength(ticker_codes, ticker_names, ticker_markets)
            _p15_prog = st.progress(0, text="ファンダ取得中...")
            for i, item in enumerate(candidates):
                item = _adjust_score_fundamental(item, item["ticker"])
                # セクター強弱ボーナス
                _sec = item.get("market", "")
                # scan_items からセクター情報を取得
                _item_sector = next(
                    (t.get("sector", "") for t in scan_items if t["code"] == item["ticker"]),
                    "",
                )
                if _item_sector and _item_sector in _sector_scores:
                    _sec_score = _sector_scores[_item_sector]
                    if _sec_score > 2.0:
                        item["score"] += 10
                        item["breakdown"]["強セクター"] = f"{_item_sector}（セクター騰落率+{_sec_score:.1f}%, +10）"
                    elif _sec_score > 0.5:
                        item["score"] += 5
                        item["breakdown"]["好セクター"] = f"{_item_sector}（+{_sec_score:.1f}%, +5）"
                    elif _sec_score < -2.0:
                        item["score"] -= 5
                        item["breakdown"]["弱セクター"] = f"{_item_sector}（{_sec_score:.1f}%, -5）⚠️"
                candidates[i] = item
                _p15_prog.progress((i + 1) / max(len(candidates), 1), text=f"({i+1}/{len(candidates)}) {item['name']}")

            # ファンダ加味後に再ソート
            candidates.sort(key=lambda x: x["score"], reverse=True)
            st.write(f"✅ ファンダメンタル・信用残・セクター加味完了")

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
## 3段階スクリーニング

### Phase 1: テクニカルスコアリング（全銘柄対象）

| 指標 | 条件 | 点数 |
|------|------|------|
| RSI(14) | < 30（売られ過ぎ） | +20 |
| RSI(14) | 30〜40（回復途上） | +15 |
| MACD | ゴールデンクロス直後 | +25 |
| MACD | 0線以下でヒスト+（転換初期） | +15 |
| BB σ | < −2σ（下限突破） | +20 |
| BB σ | −2〜−1σ（下限付近） | +12 |
| 52週安値比 | +10%以内 | +15 |
| SMA25 | 本日上抜け | +10 |
| **トレンド転換** | **SMA25 上昇転換** | **+15** |
| **中期トレンド** | **SMA75 も上昇中** | **+8** |
| **下降トレンド** | **SMA25 下降中** | **-10** |
| **出来高の質** | **上昇日÷下落日 > 1.5倍** | **+12** |

### Phase 1.5: ファンダ・信用残・セクター加減点（上位候補）

| 指標 | 条件 | 点数 |
|------|------|------|
| **PER** | **0〜10倍（割安）** | **+15** |
| **PER** | **赤字** | **-15** |
| **PBR** | **0.8倍未満** | **+10** |
| **配当利回り** | **4%超** | **+12** |
| **ROE** | **15%超** | **+8** |
| **信用売り超** | **貸借倍率 < 1.0** | **+10** |
| **買い残過多** | **貸借倍率 > 5.0** | **-8** |
| **強セクター** | **セクター5日騰落 > +2%** | **+10** |
| **弱セクター** | **セクター5日騰落 < -2%** | **-5** |

### Phase 2: AI 総合分析（最終候補）

テクニカル・ファンダメンタル・ニュース・マーケット環境を統合してAIが最終判定。
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
