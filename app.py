"""
日本株ダッシュボード — エントリーポイント
st.navigation() で全ページを Material Icons 付きで登録する。
"""
import streamlit as st
from modules.styles import apply_theme
from modules.persistence import init_persistence

# ─── ページ定義 ───────────────────────────────────────────────────────────

pages = [
    st.Page("pages/dashboard.py", title="ダッシュボード", icon=":material/candlestick_chart:", default=True),
    st.Page("pages/1_📡_BBスキャナー.py", title="BBスキャナー", icon=":material/radar:"),
    st.Page("pages/2_🎯_買い時銘柄.py", title="買い時銘柄", icon=":material/target:"),
    st.Page("pages/3_📅_決算カレンダー.py", title="決算カレンダー", icon=":material/event_note:"),
    st.Page("pages/4_🌐_市場指標.py", title="市場指標", icon=":material/public:"),
    st.Page("pages/5_📈_マーケット概況.py", title="マーケット概況", icon=":material/trending_up:"),
    st.Page("pages/6_💼_ポートフォリオ.py", title="ポートフォリオ", icon=":material/account_balance_wallet:"),
    st.Page("pages/7_👁_ウォッチリスト.py", title="ウォッチリスト", icon=":material/visibility:"),
    st.Page("pages/8_🔄_セクター分析.py", title="セクター分析", icon=":material/donut_small:"),
    st.Page("pages/9_🔍_カスタムスクリーナー.py", title="カスタムスクリーナー", icon=":material/filter_alt:"),
    st.Page("pages/10_📊_バックテスト.py", title="バックテスト", icon=":material/query_stats:"),
]

pg = st.navigation(pages)

# ─── 全ページ共通設定 ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="日本株ダッシュボード",
    page_icon=":material/candlestick_chart:",
    layout="wide",
)

apply_theme()

# ─── Cookie から全永続データを復元（JS準備完了まで待機）─
init_persistence()

# ─── 選択されたページを実行 ───────────────────────────────────────────────
pg.run()
