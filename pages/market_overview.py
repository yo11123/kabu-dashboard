"""
マーケット概況ページ - 主要指数・先物・為替のリアルタイムチャート
"""
import os
import sys
from datetime import datetime
import pytz

import streamlit as st
import pandas as pd
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.chart import create_candlestick_chart
from modules.market_hours import market_status_label
from modules.styles import apply_theme

apply_theme()

JST = pytz.timezone("Asia/Tokyo")

# 表示する指数・先物・為替
INDICES = [
    {"ticker": "^N225",   "name": "日経平均",          "unit": "円"},
    {"ticker": "NKD=F",   "name": "日経225先物(CME)",  "unit": "USD"},
    {"ticker": "^DJI",    "name": "ダウ平均",           "unit": "USD"},
    {"ticker": "^GSPC",   "name": "S&P 500",            "unit": "USD"},
    {"ticker": "^IXIC",   "name": "ナスダック",         "unit": "USD"},
    {"ticker": "JPY=X",   "name": "ドル円 (USD/JPY)",   "unit": "円"},
]

PERIOD_MAP = {
    "1ヶ月": "1mo",
    "3ヶ月": "3mo",
    "6ヶ月": "6mo",
    "1年":   "1y",
    "2年":   "2y",
}


@st.cache_data(ttl=60)
def fetch_market_data(ticker: str, period: str) -> pd.DataFrame | None:
    """指数データを取得（TTL=60秒）。"""
    try:
        df = yf.Ticker(ticker).history(period=period, interval="1d")
        if df is None or df.empty:
            return None
        df.columns = [c.capitalize() for c in df.columns]
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        cols = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
        df = df[cols].copy()
        df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)
        return df
    except Exception:
        return None


# ─── ページ設定 ──────────────────────────────────────────────────────
st.title("📈 マーケット概況")
st.caption("主要指数・先物・為替（yfinance データ、最大15分遅延）")

# 平日は 60 秒ごとに自動更新
if datetime.now(JST).weekday() < 5:
    st_autorefresh(interval=60_000, key="market_autorefresh")

# ─── コントロール ────────────────────────────────────────────────────
ctrl1, ctrl2 = st.columns([4, 1])
period_label = ctrl1.select_slider(
    "表示期間",
    options=list(PERIOD_MAP.keys()),
    value="3ヶ月",
)
period = PERIOD_MAP[period_label]

if ctrl2.button("🔄 更新", use_container_width=True, help="キャッシュをクリアして再取得"):
    fetch_market_data.clear()
    st.rerun()

st.divider()

# ─── 2 列グリッドでチャートを表示 ──────────────────────────────────
for i in range(0, len(INDICES), 2):
    row_indices = INDICES[i:i + 2]
    cols = st.columns(2)

    for col, idx in zip(cols, row_indices):
        with col:
            with st.spinner(f"{idx['name']} 取得中..."):
                df = fetch_market_data(idx["ticker"], period)

            if df is None or df.empty:
                st.warning(f"⚠️ {idx['name']} のデータを取得できませんでした")
                continue

            # ── 現在値・騰落率メトリクス ──
            last  = float(df["Close"].iloc[-1])
            prev  = float(df["Close"].iloc[-2]) if len(df) >= 2 else last
            chg   = last - prev
            chg_p = chg / prev * 100 if prev != 0 else 0.0

            # 表示フォーマット（為替は小数2桁）
            if idx["ticker"] == "JPY=X":
                price_str = f"{last:.2f} {idx['unit']}"
                chg_str   = f"{chg:+.2f} ({chg_p:+.2f}%)"
            else:
                price_str = f"{last:,.0f} {idx['unit']}"
                chg_str   = f"{chg:+,.0f} ({chg_p:+.2f}%)"

            st.metric(
                label=idx["name"],
                value=price_str,
                delta=chg_str,
                delta_color="normal" if chg >= 0 else "inverse",
            )

            # ── ミニチャート（出来高なし、マーカーなし）──
            fig, _, _ = create_candlestick_chart(
                df=df,
                title="",
                show_sma=[25],
                show_ema=[],
                show_bb=False,
                chart_height=320,
            )
            st.plotly_chart(
                fig,
                use_container_width=True,
                key=f"mkt_{idx['ticker']}_{period}",
                config={"scrollZoom": True, "displayModeBar": False},
            )

    # 行の間に少し余白
    if i + 2 < len(INDICES):
        st.divider()

# ─── フッター ────────────────────────────────────────────────────────
st.caption(market_status_label())
