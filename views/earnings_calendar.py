"""
決算カレンダーページ
日経225採用銘柄の次回決算予定をまとめて表示する。
"""
import os
import sys
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
import pandas as pd
import yfinance as yf

# modules パッケージを参照できるようにパスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.data_loader import load_tickers
from modules.styles import apply_theme

from modules.loading import helix_spinner
apply_theme()

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")


# ─── データ取得 ───────────────────────────────────────────────────────

def _fetch_one(args: tuple) -> dict | None:
    """1 銘柄の次回決算日を yfinance.calendar から取得する（並列処理用）。"""
    code, name, sector = args
    try:
        cal = yf.Ticker(code).calendar
        if not cal:
            return None
        dates = cal.get("Earnings Date", [])
        if not dates:
            return None
        next_dt = dates[0] if isinstance(dates, list) else dates
        # date / datetime どちらでも date に統一
        next_date = next_dt.date() if hasattr(next_dt, "date") else next_dt
        return {"code": code, "name": name, "sector": sector, "next_earnings_date": next_date}
    except Exception:
        return None


@st.cache_data(ttl=3600 * 12)
def fetch_all_next_earnings(tickers_tuple: tuple) -> list[dict]:
    """
    全銘柄の次回決算日を並列取得する（12 時間キャッシュ）。
    tickers_tuple: ({"code": ..., "name": ..., "sector": ...}, ...) の tuple
    """
    inputs = [(t["code"], t["name"], t["sector"]) for t in tickers_tuple]
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(_fetch_one, inp): inp for inp in inputs}
        for future in as_completed(futures, timeout=120):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception:
                pass
    return sorted(results, key=lambda x: x["next_earnings_date"])


# ─── ページ本体 ────────────────────────────────────────────────────────

st.title("決算カレンダー")
st.caption("日経225採用銘柄の次回決算発表予定日（yfinance データ）")

tickers = load_tickers(TICKERS_PATH)

# ── フィルター ──
col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
days_ahead = col_f1.slider("表示期間（今後 N 日）", 7, 120, 60)
sectors = ["全セクター"] + sorted({t["sector"] for t in tickers if t["sector"]})
selected_sector = col_f2.selectbox("セクター", sectors)

refresh_btn = col_f3.button("🔄 再取得", use_container_width=True, help="キャッシュをクリアして再取得")
if refresh_btn:
    fetch_all_next_earnings.clear()
    st.rerun()

# ── データ取得 ──
with helix_spinner("決算日データを取得中... 初回は1〜2分かかります"):
    all_earnings = fetch_all_next_earnings(tuple(
        {"code": t["code"], "name": t["name"], "sector": t["sector"]} for t in tickers
    ))

today = date.today()
cutoff = today + timedelta(days=days_ahead)

filtered = [
    e for e in all_earnings
    if today <= e["next_earnings_date"] <= cutoff
    and (selected_sector == "全セクター" or e["sector"] == selected_sector)
]

st.divider()

if not filtered:
    st.info(f"今後 {days_ahead} 日間に決算予定の銘柄が見つかりません。")
    st.stop()

st.subheader(f"今後 {days_ahead} 日間の決算予定  ―  {len(filtered)} 社")

# ── 日付ごとにグループ化して表示 ──
df_all = pd.DataFrame(filtered)
df_all["next_earnings_date"] = pd.to_datetime(df_all["next_earnings_date"])
df_all["days_until"] = (df_all["next_earnings_date"].dt.date - today).apply(lambda d: d.days)

for earn_date, group in df_all.groupby("next_earnings_date"):
    date_label = earn_date.strftime("%Y年%-m月%-d日") if sys.platform != "win32" \
        else earn_date.strftime("%Y年%m月%d日")
    days_left = (earn_date.date() - today).days
    badge = "🔴 本日" if days_left == 0 else (f"📌 あと {days_left} 日" if days_left <= 7 else f"あと {days_left} 日")

    with st.expander(f"**{date_label}**　{badge}　({len(group)} 社)", expanded=(days_left <= 14)):
        # テーブルヘッダー
        hdr = st.columns([2, 4, 3, 2])
        hdr[0].markdown("**コード**")
        hdr[1].markdown("**銘柄名**")
        hdr[2].markdown("**セクター**")
        hdr[3].markdown("**チャート**")

        for _, row in group.iterrows():
            c1, c2, c3, c4 = st.columns([2, 4, 3, 2])
            c1.markdown(f"`{row['code']}`")
            c2.markdown(row["name"])
            c3.markdown(f"_{row['sector']}_")

            # チャートページへ遷移（session_state 経由で銘柄を渡す）
            if c4.button("📊 表示", key=f"open_{row['code']}_{earn_date}", use_container_width=True):
                st.session_state["calendar_selected_ticker"] = row["code"]
                st.switch_page("views/dashboard.py")
