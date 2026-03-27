"""
日本株ダッシュボード — エントリーポイント
"""
import streamlit as st
from modules.styles import apply_theme
from modules.persistence import init_persistence

pages = [
    st.Page("views/dashboard.py", title="ダッシュボード", icon=":material/candlestick_chart:", default=True),
    st.Page("views/bb_scanner.py", title="BBスキャナー", icon=":material/radar:"),
    st.Page("views/buy_timing.py", title="買い時銘柄", icon=":material/target:"),
    st.Page("views/earnings_calendar.py", title="決算カレンダー", icon=":material/event_note:"),
    st.Page("views/market_indicators.py", title="市場指標", icon=":material/public:"),
    st.Page("views/market_overview.py", title="マーケット概況", icon=":material/trending_up:"),
    st.Page("views/portfolio.py", title="ポートフォリオ", icon=":material/account_balance_wallet:"),
    st.Page("views/watchlist.py", title="ウォッチリスト", icon=":material/visibility:"),
    st.Page("views/sector_analysis.py", title="セクター分析", icon=":material/donut_small:"),
    st.Page("views/custom_screener.py", title="カスタムスクリーナー", icon=":material/filter_alt:"),
    st.Page("views/backtest.py", title="バックテスト", icon=":material/query_stats:"),
]

pg = st.navigation(pages)
st.set_page_config(page_title="日本株ダッシュボード", page_icon=":material/candlestick_chart:", layout="wide")
apply_theme()
init_persistence()
pg.run()
