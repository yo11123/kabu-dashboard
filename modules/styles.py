"""
Bloomberg 風ダークテーマ CSS
全ページの先頭で apply_theme() を呼ぶことで適用する。
"""
import streamlit as st

# ─── カラーパレット（Plotly チャートでも参照できるようエクスポート） ──
BG_BASE      = "#0e1523"   # メイン背景
BG_PANEL     = "#101c30"   # カード・パネル
BG_SIDEBAR   = "#0b1220"   # サイドバー
BORDER       = "#1e2d40"   # ボーダー
ACCENT       = "#1db8a0"   # ティール（アクセント）
ACCENT_HOVER = "#25d4b8"   # ホバー時アクセント
TEXT_PRIMARY  = "#e0eaf5"  # 主要テキスト
TEXT_MUTED   = "#4a7a8a"   # 補足テキスト
GRID_COLOR   = "#182538"   # チャートグリッド
UP_COLOR     = "#26a69a"   # 上昇色
DOWN_COLOR   = "#ef5350"   # 下落色

_CSS = """
<style>
/* ── Google Fonts: IBM Plex Mono / IBM Plex Sans JP ── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,300;0,400;0,500;0,600;1,400&family=IBM+Plex+Sans+JP:wght@300;400;500;600&display=swap');

/* ════════════════════════════════════
   ベースレイアウト
════════════════════════════════════ */
.stApp {
    background-color: #0e1523;
}

/* ── トップヘッダーバー ── */
header[data-testid="stHeader"] {
    background: rgba(11, 18, 32, 0.9) !important;
    border-bottom: 1px solid #1a2744;
    backdrop-filter: blur(6px);
}

/* ════════════════════════════════════
   サイドバー
════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: #0b1220 !important;
    border-right: 1px solid #1a2744 !important;
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #1db8a0 !important;
    border-bottom: 1px solid #1a2744;
    padding-bottom: 6px;
    margin-top: 1.2rem !important;
    margin-bottom: 0.75rem !important;
}
/* ページナビゲーションリンク */
[data-testid="stSidebarNav"] a span {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.78rem;
    letter-spacing: 0.03em;
}

/* ════════════════════════════════════
   見出し
════════════════════════════════════ */
h1 {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #1db8a0 !important;
}
h2, h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    letter-spacing: 0.04em;
}

/* ════════════════════════════════════
   メトリクスカード（Bloomberg セル風）
════════════════════════════════════ */
[data-testid="metric-container"] {
    background: #101c30 !important;
    border: 1px solid #1e2d40 !important;
    border-left: 3px solid #1db8a0 !important;
    border-radius: 6px !important;
    padding: 14px 18px !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
[data-testid="metric-container"]:hover {
    border-color: #2a4060 !important;
    border-left-color: #25d4b8 !important;
    box-shadow: 0 0 14px rgba(29, 184, 160, 0.08);
}
[data-testid="stMetricLabel"] p {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.6rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    color: #4a7a8a !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.55rem !important;
    font-weight: 600 !important;
    color: #e0eaf5 !important;
    letter-spacing: -0.01em;
}
[data-testid="stMetricDelta"] > div {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.02em;
}

/* ════════════════════════════════════
   ボタン
════════════════════════════════════ */
.stButton > button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    background: transparent !important;
    border: 1px solid #1db8a0 !important;
    color: #1db8a0 !important;
    border-radius: 4px !important;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background: #1db8a0 !important;
    color: #0e1523 !important;
    box-shadow: 0 0 12px rgba(29, 184, 160, 0.25);
}
.stButton > button[kind="primary"] {
    background: #1db8a0 !important;
    color: #0e1523 !important;
    font-weight: 600 !important;
    border: none !important;
}
.stButton > button[kind="primary"]:hover {
    background: #25d4b8 !important;
    box-shadow: 0 0 16px rgba(29, 184, 160, 0.35);
}

/* リンクボタン */
a[data-testid="stLinkButton"],
a[data-testid="stLinkButton"] p {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.04em;
}

/* ════════════════════════════════════
   フォーム要素
════════════════════════════════════ */
/* セレクトボックス */
[data-testid="stSelectbox"] > div > div {
    background: #101c30 !important;
    border: 1px solid #1e2d40 !important;
    border-radius: 4px !important;
}
/* テキスト入力 */
[data-testid="stTextInput"] input {
    background: #101c30 !important;
    border: 1px solid #1e2d40 !important;
    border-radius: 4px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #1db8a0 !important;
    box-shadow: 0 0 0 2px rgba(29, 184, 160, 0.15) !important;
}
/* スライダー */
[data-baseweb="slider"] [role="slider"] {
    background: #1db8a0 !important;
    border-color: #1db8a0 !important;
}
/* マルチセレクト */
[data-testid="stMultiSelect"] > div > div {
    background: #101c30 !important;
    border: 1px solid #1e2d40 !important;
    border-radius: 4px !important;
}

/* ════════════════════════════════════
   区切り線・キャプション
════════════════════════════════════ */
hr {
    border: none !important;
    border-top: 1px solid #1a2744 !important;
    margin: 0.9rem 0 !important;
}
[data-testid="stCaptionContainer"] p,
.stCaption {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.66rem !important;
    color: #3a5a6a !important;
    letter-spacing: 0.03em;
}

/* ════════════════════════════════════
   コンテナ（border=True）
════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #1e2d40 !important;
    border-radius: 6px !important;
    background: #0d1929 !important;
}

/* ════════════════════════════════════
   警告・エラー・成功バナー
════════════════════════════════════ */
[data-testid="stAlert"] {
    border-radius: 6px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* ════════════════════════════════════
   select_slider オプションラベル
════════════════════════════════════ */
[data-testid="stSlider"] span {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #4a7a8a;
}

/* ════════════════════════════════════
   Plotly チャート — viewport 収まり保証
   高さスライダーで大きくしても出来高バー
   が画面外に出ないよう上限を設ける
════════════════════════════════════ */
[data-testid="stPlotlyChart"] {
    max-height: calc(100vh - 320px);
    overflow: hidden;
}
</style>
"""


def apply_theme() -> None:
    """Bloomberg 風ダークテーマを適用する。各ページの先頭で呼ぶこと。"""
    st.markdown(_CSS, unsafe_allow_html=True)
