"""
日本株アプリ v1.2 — エントリーポイント
"""
import os
from PIL import Image
import streamlit as st
from modules.styles import apply_theme
from modules.persistence import init_persistence
from modules.alerts import get_alert_count_badge

_ICON_PATH = os.path.join(os.path.dirname(__file__), "static", "icon-192.png")
_APP_ICON = Image.open(_ICON_PATH) if os.path.exists(_ICON_PATH) else ":material/candlestick_chart:"

pages = {
    "分析": [
        st.Page("views/dashboard.py", title="チャート", icon=":material/candlestick_chart:", default=True),
        st.Page("views/nikkei_forecast.py", title="日経予測", icon=":material/trending_up:"),
        st.Page("views/buy_timing.py", title="買い時銘柄", icon=":material/target:"),
        st.Page("views/bb_scanner.py", title="BBスキャナー", icon=":material/radar:"),
        st.Page("views/stock_recommend.py", title="AIレコメンド", icon=":material/recommend:"),
    ],
    "マーケット": [
        st.Page("views/news.py", title="市場ニュース", icon=":material/newspaper:"),
        st.Page("views/market_indicators.py", title="市場指標", icon=":material/public:"),
        st.Page("views/market_overview.py", title="マーケット概況", icon=":material/trending_up:"),
        st.Page("views/sector_analysis.py", title="セクター分析", icon=":material/donut_small:"),
    ],
    "カレンダー": [
        st.Page("views/earnings_calendar.py", title="決算", icon=":material/event_note:"),
        st.Page("views/economic_calendar.py", title="経済指標", icon=":material/today:"),
    ],
    "運用": [
        st.Page("views/portfolio.py", title="ポートフォリオ", icon=":material/account_balance_wallet:"),
        st.Page("views/portfolio_analytics.py", title="PFアナリティクス", icon=":material/analytics:"),
        st.Page("views/watchlist.py", title="ウォッチリスト", icon=":material/visibility:"),
    ],
    "ツール": [
        st.Page("views/custom_screener.py", title="スクリーナー", icon=":material/filter_alt:"),
        st.Page("views/backtest.py", title="バックテスト", icon=":material/query_stats:"),
        st.Page("views/ml_backtest.py", title="MLバックテスト", icon=":material/science:"),
        st.Page("views/youtube_analysis.py", title="YouTube分析", icon=":material/smart_display:"),
        st.Page("views/author_note.py", title="相場観掲示板", icon=":material/forum:"),
        st.Page("views/data_sources.py", title="データソース", icon=":material/database:"),
        st.Page("views/ml_accuracy.py", title="ML精度", icon=":material/speed:"),
    ],
}

pg = st.navigation(pages)
st.set_page_config(page_title="日本株アプリ v1.2", page_icon=_APP_ICON, layout="wide")

# ── PWA: manifest + Service Worker 登録 ──
st.markdown(
    """<link rel="manifest" href="app/static/manifest.json">
<meta name="theme-color" content="#06090f">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="app/static/icon-192.png">
<link rel="icon" type="image/png" sizes="192x192" href="app/static/icon-192.png">
<script>
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('app/static/sw.js').catch(() => {});
}
</script>""",
    unsafe_allow_html=True,
)

apply_theme()
init_persistence()

# ── サイドバー：アラートバッジ ──
alert_count = get_alert_count_badge()
if alert_count > 0:
    with st.sidebar:
        st.markdown(
            f'<div style="background:rgba(196,92,92,0.15); border:1px solid rgba(196,92,92,0.3);'
            f' border-radius:4px; padding:8px 14px; margin-bottom:12px;'
            f' font-family:Inter,Noto Sans JP,sans-serif; font-size:0.78em; color:#f0ece4;'
            f' display:flex; align-items:center; gap:8px;">'
            f'<span style="background:#c45c5c; color:#fff; border-radius:50%;'
            f' width:22px; height:22px; display:inline-flex; align-items:center;'
            f' justify-content:center; font-size:0.75em; font-weight:600;">{alert_count}</span>'
            f' アラートがトリガーされました'
            f'</div>',
            unsafe_allow_html=True,
        )

pg.run()
