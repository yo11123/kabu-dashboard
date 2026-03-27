"""
日本株ダッシュボード — エントリーポイント
"""
import streamlit as st
from modules.styles import apply_theme
from modules.persistence import init_persistence

# ─── ページ定義 ───────────────────────────────────────────────────────────

pages = [
    st.Page("pages/dashboard.py", title="ダッシュボード", icon=":material/candlestick_chart:", default=True),
    st.Page("pages/bb_scanner.py", title="BBスキャナー", icon=":material/radar:"),
    st.Page("pages/buy_timing.py", title="買い時銘柄", icon=":material/target:"),
    st.Page("pages/earnings_calendar.py", title="決算カレンダー", icon=":material/event_note:"),
    st.Page("pages/market_indicators.py", title="市場指標", icon=":material/public:"),
    st.Page("pages/market_overview.py", title="マーケット概況", icon=":material/trending_up:"),
    st.Page("pages/portfolio.py", title="ポートフォリオ", icon=":material/account_balance_wallet:"),
    st.Page("pages/watchlist.py", title="ウォッチリスト", icon=":material/visibility:"),
    st.Page("pages/sector_analysis.py", title="セクター分析", icon=":material/donut_small:"),
    st.Page("pages/custom_screener.py", title="カスタムスクリーナー", icon=":material/filter_alt:"),
    st.Page("pages/backtest.py", title="バックテスト", icon=":material/query_stats:"),
]

pg = st.navigation(pages)
st.set_page_config(page_title="日本株ダッシュボード", page_icon=":material/candlestick_chart:", layout="wide")
apply_theme()
init_persistence()
pg.run()
