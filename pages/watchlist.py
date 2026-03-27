"""
ウォッチリスト — 気になる銘柄を監視し、条件到達時にハイライト表示。
"""
import json
import os
import sys

import pandas as pd
import streamlit as st
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.styles import apply_theme
from modules.data_loader import load_tickers, load_all_tse_stocks
from modules.persistence import load_into_session, save_from_session

apply_theme()

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")

# ─── ヘルパー ─────────────────────────────────────────────────────────────

def _normalize_div_yield(raw) -> float | None:
    """yfinance の dividendYield を正規化（%値で返す）。"""
    if raw is None:
        return None
    val = float(raw)
    pct = val * 100 if val < 1 else val
    return pct if pct <= 30 else None


# ─── データ取得 ───────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def _fetch_quote(ticker: str) -> dict:
    """銘柄のリアルタイム情報を取得。"""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="5d")
        if hist.empty:
            return {}
        close = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else close
        chg = close - prev
        chg_pct = (chg / prev * 100) if prev else 0

        # RSI 簡易計算
        hist_long = t.history(period="1mo")
        rsi = None
        if len(hist_long) >= 15:
            delta = hist_long["Close"].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            loss = loss.replace(0, float("nan"))
            rs = gain / loss
            rsi_s = 100 - 100 / (1 + rs)
            val = rsi_s.iloc[-1]
            if val == val:
                rsi = round(float(val), 1)

        # 出来高比
        vol_ratio = None
        if len(hist_long) >= 30:
            v5 = hist_long["Volume"].iloc[-5:].mean()
            v30 = hist_long["Volume"].iloc[-30:].mean()
            if v30 > 0:
                vol_ratio = round(float(v5 / v30), 2)

        return {
            "price": close,
            "change": chg,
            "change_pct": chg_pct,
            "name": info.get("longName") or info.get("shortName", ""),
            "per": info.get("trailingPE"),
            "pbr": info.get("priceToBook"),
            "div_yield": _normalize_div_yield(info.get("dividendYield")),
            "rsi": rsi,
            "volume_ratio": vol_ratio,
            "high_52w": info.get("fiftyTwoWeekHigh"),
            "low_52w": info.get("fiftyTwoWeekLow"),
        }
    except Exception:
        return {}


def _check_alerts(quote: dict, watch_item: dict) -> list[str]:
    """条件到達をチェックしてアラートリストを返す。"""
    alerts = []
    price = quote.get("price", 0)
    rsi = quote.get("rsi")

    target_buy = watch_item.get("target_buy", 0)
    target_sell = watch_item.get("target_sell", 0)

    if target_buy > 0 and price <= target_buy:
        alerts.append(f"買い目標 ¥{target_buy:,.0f} に到達")
    if target_sell > 0 and price >= target_sell:
        alerts.append(f"売り目標 ¥{target_sell:,.0f} に到達")
    if rsi is not None and rsi <= 30:
        alerts.append(f"RSI {rsi} — 売られ過ぎ圏")
    if rsi is not None and rsi >= 70:
        alerts.append(f"RSI {rsi} — 買われ過ぎ圏")

    vol_ratio = quote.get("volume_ratio")
    if vol_ratio is not None and vol_ratio >= 2.0:
        alerts.append(f"出来高急増 ({vol_ratio}倍)")

    return alerts


# ─── 永続化（セッション） ─────────────────────────────────────────────────

def _save_watchlist():
    """ウォッチリストをJSON形式でセッションに保存。"""
    pass  # session_stateで管理するため不要だが拡張用に残す


# ─── メイン ───────────────────────────────────────────────────────────────

def main() -> None:
    st.title("👁 ウォッチリスト")
    st.caption("気になる銘柄を登録して監視。目標価格やRSI条件の到達時にハイライト表示します。")

    nikkei225 = load_tickers(TICKERS_PATH)
    all_tse, _ = load_all_tse_stocks()
    all_stocks = all_tse if all_tse else nikkei225
    stock_map = {s["code"]: s["name"] for s in all_stocks}

    # ─── データ復元 ─────────────────────────────────────────────
    load_into_session("watchlist_data", "watchlist", default=[])

    def _save_watchlist():
        save_from_session("watchlist_data", "watchlist")

    # ─── サイドバー：銘柄追加 ─────────────────────────────────────
    with st.sidebar:
        st.header("銘柄を追加")

        search = st.text_input("検索", placeholder="コード or 名前", key="wl_search")
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
            selected = st.selectbox("候補", options, key="wl_select")
            selected_code = selected.split(" ")[0] if selected else ""
        else:
            selected_code = st.text_input("銘柄コード", placeholder="7203.T", key="wl_code")
            if selected_code and not selected_code.endswith(".T"):
                selected_code = f"{selected_code.strip()}.T"

        c1, c2 = st.columns(2)
        target_buy = c1.number_input("買い目標 (¥)", min_value=0.0, value=0.0, step=100.0, key="wl_buy")
        target_sell = c2.number_input("売り目標 (¥)", min_value=0.0, value=0.0, step=100.0, key="wl_sell")

        memo = st.text_input("メモ（任意）", key="wl_memo", placeholder="例: 決算後に押したら買い")

        if st.button("追加", use_container_width=True, type="primary"):
            if selected_code:
                code = selected_code.strip()
                if not code.endswith(".T"):
                    code = f"{code}.T"
                existing = [w for w in st.session_state.watchlist if w["code"] == code]
                if existing:
                    st.warning(f"{code} は既に登録されています")
                else:
                    st.session_state.watchlist.append({
                        "code": code,
                        "name": stock_map.get(code, ""),
                        "target_buy": float(target_buy),
                        "target_sell": float(target_sell),
                        "memo": memo,
                        "added": pd.Timestamp.now().strftime("%Y-%m-%d"),
                    })
                    _save_watchlist()
                    st.rerun()

        st.divider()
        if st.button("全データ更新", use_container_width=True):
            _fetch_quote.clear()
            st.rerun()

    # ─── メインエリア ─────────────────────────────────────────────
    watchlist = st.session_state.watchlist

    if not watchlist:
        st.markdown(
            "<div style='text-align:center; color:#6b7280; padding:4em 1em; "
            "font-family:Inter,Noto Sans JP,sans-serif; font-size:0.9em;'>"
            "サイドバーから監視したい銘柄を追加してください"
            "</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # アラートがある銘柄を先に表示
    items_with_alerts = []
    items_normal = []

    for i, w in enumerate(watchlist):
        quote = _fetch_quote(w["code"])
        alerts = _check_alerts(quote, w) if quote else []
        entry = {"idx": i, "watch": w, "quote": quote, "alerts": alerts}
        if alerts:
            items_with_alerts.append(entry)
        else:
            items_normal.append(entry)

    # ─── アラート銘柄 ────────────────────────────────────────────
    if items_with_alerts:
        st.subheader("条件到達銘柄")
        for item in items_with_alerts:
            _render_watch_card(item, alert=True)
        st.divider()

    # ─── 通常銘柄 ────────────────────────────────────────────────
    st.subheader(f"監視中 ({len(watchlist)}銘柄)")
    for item in items_normal:
        _render_watch_card(item, alert=False)

    # ─── 削除処理 ────────────────────────────────────────────────
    if "wl_remove" in st.session_state and st.session_state.wl_remove is not None:
        idx = st.session_state.wl_remove
        if 0 <= idx < len(st.session_state.watchlist):
            st.session_state.watchlist.pop(idx)
            _save_watchlist()
        st.session_state.wl_remove = None
        st.rerun()


def _render_watch_card(item: dict, alert: bool) -> None:
    """ウォッチリストのカードを描画。"""
    w = item["watch"]
    q = item["quote"]
    alerts = item["alerts"]
    idx = item["idx"]

    price = q.get("price", 0)
    chg_pct = q.get("change_pct", 0)
    chg_color = "#5ca08b" if chg_pct >= 0 else "#c45c5c"
    border_color = "#d4af37" if alert else "rgba(212,175,55,0.06)"
    name = w["name"] or w["code"]

    # RSI/PER/出来高情報
    info_parts = []
    if q.get("rsi") is not None:
        rsi = q["rsi"]
        rsi_color = "#c45c5c" if rsi >= 70 else "#5ca08b" if rsi <= 30 else "#6b7280"
        info_parts.append(f"<span style='color:{rsi_color};'>RSI {rsi}</span>")
    if q.get("per") is not None:
        info_parts.append(f"PER {q['per']:.1f}")
    if q.get("div_yield") is not None:
        info_parts.append(f"配当 {q['div_yield']:.2f}%")
    if q.get("volume_ratio") is not None:
        vr = q["volume_ratio"]
        vr_color = "#d4af37" if vr >= 2.0 else "#6b7280"
        info_parts.append(f"<span style='color:{vr_color};'>出来高{vr}倍</span>")

    info_html = " ｜ ".join(info_parts)

    # アラート表示
    alert_html = ""
    if alerts:
        alert_items = "".join(
            f"<span style='background:rgba(212,175,55,0.12); border:1px solid rgba(212,175,55,0.2); "
            f"padding:3px 10px; border-radius:2px; font-size:0.65em; color:#d4af37; "
            f"letter-spacing:0.05em; margin-right:6px;'>{a}</span>"
            for a in alerts
        )
        alert_html = f"<div style='margin-top:8px;'>{alert_items}</div>"

    # メモ
    memo_html = ""
    if w.get("memo"):
        memo_html = (
            f"<div style='margin-top:6px; font-size:0.7em; color:#6b7280; "
            f"font-style:italic;'>📝 {w['memo']}</div>"
        )

    # カード内の各セクション
    info_section = ""
    if info_html:
        info_section = f'<div style="margin-top:6px; font-family:Inter,sans-serif; font-size:0.65em; color:#6b7280;">{info_html}</div>'

    card_html = (
        f'<div style="background:rgba(10,15,26,0.5); border:1px solid {border_color};'
        f' border-left:2px solid {border_color}; border-radius:2px; padding:18px 24px; margin-bottom:6px;">'
        f'<div style="display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;">'
        f'<span style="font-family:Cormorant Garamond,serif; font-size:1.1em; color:#f0ece4;">{name}</span>'
        f'<span style="font-family:Inter,sans-serif; font-size:0.6em; color:#6b7280; letter-spacing:0.12em;">{w["code"]}</span>'
        f'<span style="font-family:IBM Plex Mono,monospace; font-size:1.1em; color:#f0ece4; margin-left:auto;">¥{price:,.0f}</span>'
        f'<span style="font-family:IBM Plex Mono,monospace; font-size:0.8em; color:{chg_color};">{chg_pct:+.2f}%</span>'
        f'</div>'
        f'{info_section}{alert_html}{memo_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # アクションボタン
    c1, c2, c3 = st.columns([1, 1, 6])
    if c1.button("📊 チャート", key=f"wl_chart_{idx}"):
        st.session_state["selected_ticker"] = w["code"]
        st.switch_page("pages/dashboard.py")
    if c2.button("✕ 削除", key=f"wl_del_{idx}"):
        st.session_state.wl_remove = idx
        st.rerun()


main()
