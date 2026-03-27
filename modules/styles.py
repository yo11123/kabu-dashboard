"""
Luxury Dark テーマ CSS
高級マンションのWebサイトを彷彿とさせる、洗練されたダークテーマ。
セリフ体見出し・シャンパンゴールド・グラスモーフィズムで上質感を演出。
全ページの先頭で apply_theme() を呼ぶことで適用する。
"""
import streamlit as st

# ─── カラーパレット（Plotly チャートでも参照できるようエクスポート） ──
BG_BASE      = "#06090f"   # メイン背景（漆黒）
BG_PANEL     = "#0a0f1a"   # カード・パネル
BG_SIDEBAR   = "#050810"   # サイドバー
BORDER       = "#1a1f2e"   # ボーダー（極めて控えめ）
ACCENT       = "#d4af37"   # シャンパンゴールド（メインアクセント）
ACCENT_HOVER = "#e6c34d"   # ホバー時ゴールド
ACCENT_SUB   = "#8fb8a0"   # セージグリーン（サブアクセント）
TEXT_PRIMARY  = "#f0ece4"  # アイボリーホワイト
TEXT_MUTED   = "#6b7280"   # グレー（補足テキスト）
GRID_COLOR   = "#111620"   # チャートグリッド
UP_COLOR     = "#5ca08b"   # 上昇色（落ち着いたグリーン）
DOWN_COLOR   = "#c45c5c"   # 下落色（落ち着いたレッド）

_CSS = """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&family=Noto+Sans+JP:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@300;400;500;600&display=swap');

/* ═══════════════════════════════════════════
   CSS Variables
═══════════════════════════════════════════ */
:root {
    --bg-base: #06090f;
    --bg-panel: #0a0f1a;
    --bg-elevated: #0e1320;
    --border: rgba(212, 175, 55, 0.06);
    --border-hover: rgba(212, 175, 55, 0.15);
    --gold: #d4af37;
    --gold-light: #e6c34d;
    --gold-dim: rgba(212, 175, 55, 0.5);
    --ivory: #f0ece4;
    --ivory-muted: #b8b0a2;
    --sage: #8fb8a0;
    --text-muted: #6b7280;
    --serif: 'Cormorant Garamond', 'Noto Sans JP', serif;
    --sans: 'Inter', 'Noto Sans JP', sans-serif;
    --mono: 'IBM Plex Mono', monospace;
    --ease: cubic-bezier(0.25, 0.1, 0.25, 1);
}

/* ═══════════════════════════════════════════
   ベースレイアウト
═══════════════════════════════════════════ */
.stApp {
    background: var(--bg-base);
}

/* 繊細な背景ノイズテクスチャ風 */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse at 20% 50%,
            rgba(212, 175, 55, 0.015) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 20%,
            rgba(143, 184, 160, 0.01) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

/* ── トップヘッダーバー ── */
header[data-testid="stHeader"] {
    background: rgba(6, 9, 15, 0.85) !important;
    border-bottom: 1px solid rgba(212, 175, 55, 0.05);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
}

/* ═══════════════════════════════════════════
   サイドバー — 静謐なパネル
═══════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,
        rgba(5, 8, 16, 0.97) 0%,
        rgba(8, 12, 20, 0.95) 100%) !important;
    border-right: 1px solid rgba(212, 175, 55, 0.06) !important;
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: var(--serif) !important;
    font-size: 0.8rem !important;
    font-weight: 400 !important;
    font-style: italic;
    text-transform: none;
    letter-spacing: 0.12em;
    color: var(--gold) !important;
    border-bottom: none;
    padding-bottom: 4px;
    margin-top: 1.6rem !important;
    margin-bottom: 0.6rem !important;
    position: relative;
}
[data-testid="stSidebar"] h2::after,
[data-testid="stSidebar"] h3::after {
    content: '';
    display: block;
    width: 32px;
    height: 1px;
    background: linear-gradient(90deg, var(--gold), transparent);
    margin-top: 8px;
}
/* ページナビゲーションリンク */
[data-testid="stSidebarNav"] a span {
    font-family: var(--sans) !important;
    font-size: 0.78rem;
    font-weight: 400;
    letter-spacing: 0.04em;
    color: var(--ivory-muted) !important;
    transition: all 0.4s var(--ease);
}
[data-testid="stSidebarNav"] a:hover span {
    color: var(--gold) !important;
    letter-spacing: 0.06em;
}

/* ═══════════════════════════════════════════
   見出し — エレガントなセリフ体
═══════════════════════════════════════════ */
h1 {
    font-family: var(--serif) !important;
    font-size: 1.6rem !important;
    font-weight: 300 !important;
    text-transform: none;
    letter-spacing: 0.15em;
    color: var(--ivory) !important;
    position: relative;
    padding-bottom: 12px;
}
h1::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 48px;
    height: 1px;
    background: linear-gradient(90deg, var(--gold), transparent);
}
h2 {
    font-family: var(--serif) !important;
    font-size: 1.2rem !important;
    font-weight: 400 !important;
    letter-spacing: 0.08em;
    color: var(--ivory) !important;
}
h3 {
    font-family: var(--sans) !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em;
    color: var(--ivory-muted) !important;
    text-transform: uppercase;
}

/* ═══════════════════════════════════════════
   メトリクスカード — ミニマルラグジュアリー
═══════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: rgba(10, 15, 26, 0.6) !important;
    border: 1px solid rgba(212, 175, 55, 0.06) !important;
    border-left: 2px solid var(--gold-dim) !important;
    border-radius: 2px !important;
    padding: 20px 24px !important;
    transition: all 0.5s var(--ease);
    position: relative;
}
[data-testid="metric-container"]:hover {
    border-left-color: var(--gold) !important;
    background: rgba(10, 15, 26, 0.8) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}
[data-testid="stMetricLabel"] p {
    font-family: var(--sans) !important;
    font-size: 0.6rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.2em !important;
    color: var(--text-muted) !important;
}
[data-testid="stMetricValue"] {
    font-family: var(--mono) !important;
    font-size: 1.45rem !important;
    font-weight: 400 !important;
    color: var(--ivory) !important;
    letter-spacing: 0.02em;
}
[data-testid="stMetricDelta"] > div {
    font-family: var(--mono) !important;
    font-size: 0.75rem !important;
    font-weight: 400;
    letter-spacing: 0.02em;
}

/* ═══════════════════════════════════════════
   ボタン — 洗練されたミニマリズム
═══════════════════════════════════════════ */
.stButton > button {
    font-family: var(--sans) !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    background: transparent !important;
    border: 1px solid rgba(212, 175, 55, 0.25) !important;
    color: var(--gold) !important;
    border-radius: 0px !important;
    padding: 10px 28px !important;
    transition: all 0.5s var(--ease);
}
.stButton > button:hover {
    background: var(--gold) !important;
    color: var(--bg-base) !important;
    border-color: var(--gold) !important;
    box-shadow: 0 4px 20px rgba(212, 175, 55, 0.15);
    letter-spacing: 0.2em;
}
.stButton > button[kind="primary"] {
    background: var(--gold) !important;
    color: var(--bg-base) !important;
    font-weight: 600 !important;
    border: 1px solid var(--gold) !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--gold-light) !important;
    box-shadow: 0 4px 24px rgba(212, 175, 55, 0.2);
    letter-spacing: 0.2em;
}

/* リンクボタン */
a[data-testid="stLinkButton"],
a[data-testid="stLinkButton"] p {
    font-family: var(--sans) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em;
}

/* ═══════════════════════════════════════════
   フォーム要素 — シンプルで上品
═══════════════════════════════════════════ */
[data-testid="stSelectbox"] > div > div {
    background: rgba(10, 15, 26, 0.5) !important;
    border: 1px solid rgba(212, 175, 55, 0.08) !important;
    border-radius: 2px !important;
    transition: border-color 0.3s var(--ease);
}
[data-testid="stSelectbox"] > div > div:hover {
    border-color: rgba(212, 175, 55, 0.2) !important;
}
[data-testid="stTextInput"] input {
    background: rgba(10, 15, 26, 0.5) !important;
    border: none !important;
    border-bottom: 1px solid rgba(212, 175, 55, 0.12) !important;
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-size: 0.85rem !important;
    color: var(--ivory) !important;
    padding: 8px 4px !important;
    transition: border-color 0.3s var(--ease);
}
[data-testid="stTextInput"] input:focus {
    border-bottom-color: var(--gold) !important;
    box-shadow: none !important;
}
[data-baseweb="slider"] [role="slider"] {
    background: var(--gold) !important;
    border-color: var(--gold) !important;
    box-shadow: 0 0 12px rgba(212, 175, 55, 0.2);
}
[data-testid="stMultiSelect"] > div > div {
    background: rgba(10, 15, 26, 0.5) !important;
    border: 1px solid rgba(212, 175, 55, 0.08) !important;
    border-radius: 2px !important;
}

/* ═══════════════════════════════════════════
   ラベル
═══════════════════════════════════════════ */
[data-testid="stWidgetLabel"] p {
    font-family: var(--sans) !important;
    font-size: 0.65rem !important;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--text-muted) !important;
}

/* ═══════════════════════════════════════════
   区切り線・キャプション
═══════════════════════════════════════════ */
hr {
    border: none !important;
    border-top: 1px solid rgba(212, 175, 55, 0.06) !important;
    margin: 1.2rem 0 !important;
}
[data-testid="stCaptionContainer"] p,
.stCaption {
    font-family: var(--sans) !important;
    font-size: 0.65rem !important;
    color: #505868 !important;
    letter-spacing: 0.06em;
    font-style: italic;
}

/* ═══════════════════════════════════════════
   コンテナ（border=True）
═══════════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(212, 175, 55, 0.05) !important;
    border-radius: 2px !important;
    background: rgba(10, 15, 26, 0.4) !important;
    transition: all 0.5s var(--ease);
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(212, 175, 55, 0.12) !important;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.15);
}

/* ═══════════════════════════════════════════
   警告・エラー・成功バナー
═══════════════════════════════════════════ */
[data-testid="stAlert"] {
    border-radius: 2px !important;
    font-family: var(--sans) !important;
    font-size: 0.8rem !important;
}

/* ═══════════════════════════════════════════
   スライダーラベル
═══════════════════════════════════════════ */
[data-testid="stSlider"] span {
    font-family: var(--mono);
    font-size: 0.65rem;
    color: var(--text-muted);
}

/* ═══════════════════════════════════════════
   タブ — ミニマルエレガンス
═══════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: transparent;
    border-radius: 0;
    border: none;
    border-bottom: 1px solid rgba(212, 175, 55, 0.08);
    padding: 0;
}
.stTabs [data-baseweb="tab"] {
    font-family: var(--sans) !important;
    font-size: 0.72rem;
    font-weight: 400;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
    border-radius: 0;
    padding: 14px 24px;
    border: none;
    transition: all 0.4s var(--ease);
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--ivory);
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: var(--gold) !important;
    font-weight: 500 !important;
    border-bottom: 1px solid var(--gold) !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-panel"] {
    border: none;
    border-top: none;
    border-radius: 0;
    padding: 24px 4px;
    background: transparent;
}

/* ═══════════════════════════════════════════
   エクスパンダー
═══════════════════════════════════════════ */
[data-testid="stExpander"] {
    border: none !important;
    border-bottom: 1px solid rgba(212, 175, 55, 0.06) !important;
    border-radius: 0 !important;
    background: transparent !important;
}
[data-testid="stExpander"] summary {
    font-family: var(--sans) !important;
    font-size: 0.78rem !important;
    font-weight: 400;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    transition: all 0.3s var(--ease);
}
[data-testid="stExpander"] summary:hover {
    color: var(--gold);
    letter-spacing: 0.08em;
}

/* ═══════════════════════════════════════════
   チャットメッセージ
═══════════════════════════════════════════ */
[data-testid="stChatMessage"] {
    font-family: var(--sans) !important;
    font-size: 0.88rem;
    border-radius: 2px;
    background: rgba(10, 15, 26, 0.4) !important;
    border: 1px solid rgba(212, 175, 55, 0.04);
}

/* ═══════════════════════════════════════════
   プログレスバー — ゴールドグラデーション
═══════════════════════════════════════════ */
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg,
        #d4af37, #e6c34d, #d4af37) !important;
    background-size: 200% 100%;
    animation: goldShimmer 3s ease-in-out infinite;
    border-radius: 0;
}
@keyframes goldShimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* ═══════════════════════════════════════════
   Plotly チャート
═══════════════════════════════════════════ */
[data-testid="stPlotlyChart"] {
    max-height: calc(100vh - 320px);
    overflow: hidden;
}

/* ═══════════════════════════════════════════
   スクロールバー
═══════════════════════════════════════════ */
::-webkit-scrollbar {
    width: 4px;
    height: 4px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(212, 175, 55, 0.15);
    border-radius: 0;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(212, 175, 55, 0.3);
}

/* ═══════════════════════════════════════════
   全体的な本文テキスト
═══════════════════════════════════════════ */
.stApp p, .stApp li {
    font-family: var(--sans);
    color: var(--ivory-muted);
    line-height: 1.7;
}

/* ═══════════════════════════════════════════
   ダイアログ
═══════════════════════════════════════════ */
[data-testid="stModal"] > div {
    background: rgba(8, 12, 20, 0.97) !important;
    border: 1px solid rgba(212, 175, 55, 0.1) !important;
    border-radius: 2px !important;
    backdrop-filter: blur(30px);
    -webkit-backdrop-filter: blur(30px);
    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6);
}

/* ═══════════════════════════════════════════
   セレクション（テキスト選択時）
═══════════════════════════════════════════ */
::selection {
    background: rgba(212, 175, 55, 0.2);
    color: var(--ivory);
}
</style>
"""


def apply_theme() -> None:
    """Luxury Dark テーマを適用する。各ページの先頭で呼ぶこと。"""
    st.markdown(_CSS, unsafe_allow_html=True)
