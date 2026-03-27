"""
Premium Dark テーマ CSS
Bloomberg 風をベースに、グラスモーフィズム・ゴールドアクセント・
グラデーションボーダーで高級感を演出。
全ページの先頭で apply_theme() を呼ぶことで適用する。
"""
import streamlit as st

# ─── カラーパレット（Plotly チャートでも参照できるようエクスポート） ──
BG_BASE      = "#080d18"   # メイン背景（より深い黒）
BG_PANEL     = "#0c1424"   # カード・パネル
BG_SIDEBAR   = "#060b14"   # サイドバー
BORDER       = "#1a2640"   # ボーダー
ACCENT       = "#1db8a0"   # ティール（アクセント）
ACCENT_HOVER = "#25d4b8"   # ホバー時アクセント
ACCENT_GOLD  = "#c9a84c"   # ゴールドアクセント
TEXT_PRIMARY  = "#e8f0fa"  # 主要テキスト
TEXT_MUTED   = "#4a7a8a"   # 補足テキスト
GRID_COLOR   = "#141e30"   # チャートグリッド
UP_COLOR     = "#26a69a"   # 上昇色
DOWN_COLOR   = "#ef5350"   # 下落色

_CSS = """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:ital,wght@0,300;0,400;0,500;0,600;1,400&family=Noto+Sans+JP:wght@300;400;500;600;700&display=swap');

/* ═══════════════════════════════════════════
   ベースレイアウト
═══════════════════════════════════════════ */
.stApp {
    background: linear-gradient(165deg, #080d18 0%, #0a1020 40%, #0c1226 100%);
}

/* ── トップヘッダーバー ── */
header[data-testid="stHeader"] {
    background: rgba(8, 13, 24, 0.75) !important;
    border-bottom: 1px solid rgba(29, 184, 160, 0.08);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}

/* ═══════════════════════════════════════════
   サイドバー — グラスモーフィズム
═══════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,
        rgba(6, 11, 20, 0.95) 0%,
        rgba(8, 14, 26, 0.92) 100%) !important;
    border-right: 1px solid rgba(29, 184, 160, 0.1) !important;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.62rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: #c9a84c !important;
    border-bottom: 1px solid rgba(201, 168, 76, 0.15);
    padding-bottom: 8px;
    margin-top: 1.4rem !important;
    margin-bottom: 0.8rem !important;
}
/* ページナビゲーションリンク */
[data-testid="stSidebarNav"] a span {
    font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
    font-size: 0.8rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    transition: color 0.2s ease;
}
[data-testid="stSidebarNav"] a:hover span {
    color: #1db8a0 !important;
}

/* ═══════════════════════════════════════════
   見出し — ゴールド＋ティールのアクセント
═══════════════════════════════════════════ */
h1 {
    font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    background: linear-gradient(135deg, #1db8a0 0%, #c9a84c 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
h2, h3 {
    font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em;
    color: #e8f0fa !important;
}

/* ═══════════════════════════════════════════
   メトリクスカード — グラスモーフィズム
═══════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: linear-gradient(135deg,
        rgba(12, 20, 36, 0.8) 0%,
        rgba(16, 28, 48, 0.6) 100%) !important;
    border: 1px solid rgba(29, 184, 160, 0.12) !important;
    border-left: 3px solid #1db8a0 !important;
    border-radius: 8px !important;
    padding: 16px 20px !important;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg,
        rgba(29, 184, 160, 0.03) 0%,
        transparent 50%);
    pointer-events: none;
}
[data-testid="metric-container"]:hover {
    border-color: rgba(29, 184, 160, 0.25) !important;
    border-left-color: #c9a84c !important;
    box-shadow:
        0 4px 24px rgba(29, 184, 160, 0.08),
        0 0 40px rgba(29, 184, 160, 0.04),
        inset 0 1px 0 rgba(255, 255, 255, 0.02);
    transform: translateY(-1px);
}
[data-testid="stMetricLabel"] p {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.58rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.16em !important;
    color: #4a7a8a !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.5rem !important;
    font-weight: 600 !important;
    color: #e8f0fa !important;
    letter-spacing: -0.02em;
}
[data-testid="stMetricDelta"] > div {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.76rem !important;
    letter-spacing: 0.02em;
}

/* ═══════════════════════════════════════════
   ボタン — グラデーションボーダー
═══════════════════════════════════════════ */
.stButton > button {
    font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    background: rgba(12, 20, 36, 0.6) !important;
    border: 1px solid rgba(29, 184, 160, 0.3) !important;
    color: #1db8a0 !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.stButton > button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg,
        transparent,
        rgba(29, 184, 160, 0.08),
        transparent);
    transition: left 0.5s ease;
}
.stButton > button:hover::before {
    left: 100%;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1db8a0, #18a08a) !important;
    color: #080d18 !important;
    border-color: #1db8a0 !important;
    box-shadow:
        0 4px 20px rgba(29, 184, 160, 0.25),
        0 0 40px rgba(29, 184, 160, 0.1);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1db8a0 0%, #18a890 100%) !important;
    color: #080d18 !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 2px 12px rgba(29, 184, 160, 0.2);
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #25d4b8 0%, #1db8a0 100%) !important;
    box-shadow:
        0 4px 24px rgba(29, 184, 160, 0.35),
        0 0 40px rgba(29, 184, 160, 0.15);
    transform: translateY(-1px);
}

/* リンクボタン */
a[data-testid="stLinkButton"],
a[data-testid="stLinkButton"] p {
    font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
    font-size: 0.74rem !important;
    letter-spacing: 0.03em;
}

/* ═══════════════════════════════════════════
   フォーム要素 — 洗練されたインプット
═══════════════════════════════════════════ */
/* セレクトボックス */
[data-testid="stSelectbox"] > div > div {
    background: rgba(12, 20, 36, 0.7) !important;
    border: 1px solid rgba(26, 38, 64, 0.8) !important;
    border-radius: 6px !important;
    transition: border-color 0.2s ease;
}
[data-testid="stSelectbox"] > div > div:hover {
    border-color: rgba(29, 184, 160, 0.3) !important;
}
/* テキスト入力 */
[data-testid="stTextInput"] input {
    background: rgba(12, 20, 36, 0.7) !important;
    border: 1px solid rgba(26, 38, 64, 0.8) !important;
    border-radius: 6px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease;
}
[data-testid="stTextInput"] input:focus {
    border-color: #1db8a0 !important;
    box-shadow:
        0 0 0 2px rgba(29, 184, 160, 0.12),
        0 0 20px rgba(29, 184, 160, 0.06) !important;
}
/* スライダー */
[data-baseweb="slider"] [role="slider"] {
    background: linear-gradient(135deg, #1db8a0, #c9a84c) !important;
    border-color: #1db8a0 !important;
    box-shadow: 0 0 8px rgba(29, 184, 160, 0.3);
}
/* マルチセレクト */
[data-testid="stMultiSelect"] > div > div {
    background: rgba(12, 20, 36, 0.7) !important;
    border: 1px solid rgba(26, 38, 64, 0.8) !important;
    border-radius: 6px !important;
}

/* ═══════════════════════════════════════════
   ラベル（フォーム要素のラベル）
═══════════════════════════════════════════ */
[data-testid="stWidgetLabel"] p {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.68rem !important;
    font-weight: 500;
    letter-spacing: 0.06em;
    color: #6a9aaa !important;
}

/* ═══════════════════════════════════════════
   区切り線・キャプション
═══════════════════════════════════════════ */
hr {
    border: none !important;
    border-top: 1px solid rgba(29, 184, 160, 0.08) !important;
    margin: 1rem 0 !important;
}
[data-testid="stCaptionContainer"] p,
.stCaption {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.64rem !important;
    color: #3a5a6a !important;
    letter-spacing: 0.04em;
}

/* ═══════════════════════════════════════════
   コンテナ（border=True）— グラスモーフィズム
═══════════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(26, 38, 64, 0.6) !important;
    border-radius: 10px !important;
    background: linear-gradient(135deg,
        rgba(10, 18, 32, 0.7) 0%,
        rgba(13, 22, 38, 0.5) 100%) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: border-color 0.3s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(29, 184, 160, 0.15) !important;
}

/* ═══════════════════════════════════════════
   警告・エラー・成功バナー
═══════════════════════════════════════════ */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
    font-size: 0.82rem !important;
    backdrop-filter: blur(6px);
}

/* ═══════════════════════════════════════════
   select_slider オプションラベル
═══════════════════════════════════════════ */
[data-testid="stSlider"] span {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.66rem;
    color: #4a7a8a;
}

/* ═══════════════════════════════════════════
   タブ — プレミアムスタイル
═══════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: rgba(6, 11, 20, 0.8);
    border-radius: 10px 10px 0 0;
    border: 1px solid rgba(26, 38, 64, 0.6);
    border-bottom: none;
    padding: 4px 6px 0;
    backdrop-filter: blur(10px);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
    font-size: 0.76rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    color: #4a7a8a;
    border-radius: 8px 8px 0 0;
    padding: 10px 22px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.stTabs [data-baseweb="tab"]:hover {
    color: #e8f0fa;
    background: rgba(29, 184, 160, 0.06);
}
.stTabs [aria-selected="true"] {
    color: #1db8a0 !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #1db8a0 !important;
    background: rgba(29, 184, 160, 0.05) !important;
    box-shadow: 0 -2px 12px rgba(29, 184, 160, 0.06);
}
.stTabs [data-baseweb="tab-panel"] {
    border: 1px solid rgba(26, 38, 64, 0.6);
    border-top: none;
    border-radius: 0 0 10px 10px;
    padding: 20px;
    background: rgba(10, 16, 28, 0.6);
    backdrop-filter: blur(8px);
}

/* ═══════════════════════════════════════════
   エクスパンダー
═══════════════════════════════════════════ */
[data-testid="stExpander"] {
    border: 1px solid rgba(26, 38, 64, 0.5) !important;
    border-radius: 8px !important;
    background: linear-gradient(135deg,
        rgba(10, 18, 32, 0.6) 0%,
        rgba(13, 22, 38, 0.4) 100%) !important;
    backdrop-filter: blur(6px);
    transition: border-color 0.3s ease;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(29, 184, 160, 0.2) !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 500;
    color: #6a9aaa;
    transition: color 0.2s ease;
}
[data-testid="stExpander"] summary:hover {
    color: #1db8a0;
}

/* ═══════════════════════════════════════════
   チャットメッセージ
═══════════════════════════════════════════ */
[data-testid="stChatMessage"] {
    font-family: 'Inter', 'Noto Sans JP', sans-serif !important;
    font-size: 0.88rem;
    border-radius: 10px;
    background: rgba(12, 20, 36, 0.6) !important;
    border: 1px solid rgba(26, 38, 64, 0.4);
}

/* ═══════════════════════════════════════════
   プログレスバー — グラデーション
═══════════════════════════════════════════ */
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg,
        #1db8a0 0%,
        #c9a84c 50%,
        #1db8a0 100%) !important;
    background-size: 200% 100%;
    animation: shimmer 2s ease-in-out infinite;
    border-radius: 4px;
}
@keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* ═══════════════════════════════════════════
   Plotly チャート
═══════════════════════════════════════════ */
[data-testid="stPlotlyChart"] {
    max-height: calc(100vh - 320px);
    overflow: hidden;
    border-radius: 8px;
}

/* ═══════════════════════════════════════════
   データフレーム / テーブル
═══════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
}

/* ═══════════════════════════════════════════
   スクロールバー — プレミアム
═══════════════════════════════════════════ */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: rgba(8, 13, 24, 0.4);
}
::-webkit-scrollbar-thumb {
    background: rgba(29, 184, 160, 0.2);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(29, 184, 160, 0.4);
}

/* ═══════════════════════════════════════════
   全体的な本文テキスト
═══════════════════════════════════════════ */
.stApp p, .stApp li, .stApp span {
    font-family: 'Inter', 'Noto Sans JP', sans-serif;
}

/* ═══════════════════════════════════════════
   ダイアログ — グラスモーフィズム
═══════════════════════════════════════════ */
[data-testid="stModal"] > div {
    background: linear-gradient(135deg,
        rgba(10, 16, 28, 0.95) 0%,
        rgba(12, 20, 36, 0.92) 100%) !important;
    border: 1px solid rgba(29, 184, 160, 0.15) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    box-shadow:
        0 20px 60px rgba(0, 0, 0, 0.5),
        0 0 40px rgba(29, 184, 160, 0.05);
}
</style>
"""


def apply_theme() -> None:
    """Premium Dark テーマを適用する。各ページの先頭で呼ぶこと。"""
    st.markdown(_CSS, unsafe_allow_html=True)
