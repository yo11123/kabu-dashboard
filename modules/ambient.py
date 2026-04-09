"""
アンビエントUI — 市場状況に応じた背景パーティクル・ティッカーテープ・ゲージ

背景パーティクル:
  - 暴落時（日経-3%以上）→ 雨
  - 夜間（18:00-06:00 JST）→ 星/蛍
  - 通常 → なし（アンビエント光のみ）

ティッカーテープ:
  - 画面上部に主要指数がスクロール表示

ゲージ:
  - VIX恐怖指数/RSI のスピードメーター風表示
"""
import streamlit as st
from datetime import datetime
import math


# ═══════════════════════════════════════════════════════════════════
# 背景パーティクル
# ═══════════════════════════════════════════════════════════════════

_PARTICLE_CSS = """
/* === 雨（暴落時）=== */
.ambient-rain { position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:0; overflow:hidden; }
.ambient-rain .drop {
    position:absolute; top:-20px; width:2px; background:linear-gradient(to bottom, transparent, rgba(100,140,180,0.4));
    border-radius:0 0 2px 2px; animation:ambientRainDrop linear infinite; pointer-events:none;
}
@keyframes ambientRainDrop {
    0%   { transform:translateY(-20px); opacity:0.7; }
    100% { transform:translateY(100vh); opacity:0.01; }
}

/* === 星（夜間）=== */
.ambient-stars { position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:0; overflow:hidden; }
.ambient-stars .star {
    position:absolute; width:3px; height:3px; background:#f0ece4; border-radius:50%;
    animation:ambientStarTwinkle ease-in-out infinite; pointer-events:none;
}
@keyframes ambientStarTwinkle {
    0%, 100% { opacity:0.2; transform:scale(0.8); }
    50%      { opacity:0.9; transform:scale(1.2); }
}

/* === 蛍（夜間）=== */
.ambient-fireflies { position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:0; overflow:hidden; }
.ambient-fireflies .firefly {
    position:absolute; width:6px; height:6px; border-radius:50%;
    background:radial-gradient(circle, rgba(212,175,55,0.8), rgba(212,175,55,0.01));
    box-shadow:0 0 8px rgba(212,175,55,0.4);
    animation:ambientFireflyFloat ease-in-out infinite; pointer-events:none;
}
@keyframes ambientFireflyFloat {
    0%   { transform:translate(0, 0) scale(1); opacity:0.3; }
    25%  { transform:translate(15px, -20px) scale(1.1); opacity:0.8; }
    50%  { transform:translate(-10px, -35px) scale(0.9); opacity:0.5; }
    75%  { transform:translate(20px, -15px) scale(1.05); opacity:0.7; }
    100% { transform:translate(0, 0) scale(1); opacity:0.3; }
}
"""


def _generate_rain_html(intensity: int = 20) -> str:
    """雨のHTMLを生成する。"""
    drops = []
    for i in range(intensity):
        left = (i * 37 + 13) % 100
        height = 15 + (i * 7) % 20
        duration = 0.8 + (i * 0.03)
        delay = (i * 0.15) % 3
        drops.append(
            f'<div class="drop" style="left:{left}%;height:{height}px;'
            f'animation-duration:{duration}s;animation-delay:{delay}s;"></div>'
        )
    return f'<div class="ambient-rain">{"".join(drops)}</div>'


def _generate_stars_html(count: int = 30) -> str:
    """星のHTMLを生成する。"""
    stars = []
    for i in range(count):
        left = (i * 31 + 7) % 98 + 1
        top = (i * 43 + 11) % 90 + 2
        size = 2 + (i % 3)
        duration = 2 + (i * 0.3) % 4
        delay = (i * 0.2) % 5
        stars.append(
            f'<div class="star" style="left:{left}%;top:{top}%;width:{size}px;height:{size}px;'
            f'animation-duration:{duration}s;animation-delay:{delay}s;"></div>'
        )
    return f'<div class="ambient-stars">{"".join(stars)}</div>'


def _generate_fireflies_html(count: int = 8) -> str:
    """蛍のHTMLを生成する。"""
    flies = []
    for i in range(count):
        left = 5 + (i * 23 + 9) % 85
        top = 10 + (i * 31 + 17) % 70
        duration = 4 + (i * 1.5) % 6
        delay = (i * 0.8) % 4
        flies.append(
            f'<div class="firefly" style="left:{left}%;top:{top}%;'
            f'animation-duration:{duration}s;animation-delay:{delay}s;"></div>'
        )
    return f'<div class="ambient-fireflies">{"".join(flies)}</div>'


def render_ambient_background(nikkei_change_pct: float | None = None) -> None:
    """市場状況に応じた背景パーティクルを表示する。

    Args:
        nikkei_change_pct: 日経平均の前日比(%)。Noneの場合は時間帯のみで判定。
    """
    # CSSを注入
    st.markdown(f"<style>{_PARTICLE_CSS}</style>", unsafe_allow_html=True)

    # 暴落判定（-3%以上の下落）
    if nikkei_change_pct is not None and nikkei_change_pct <= -3.0:
        st.markdown(_generate_rain_html(25), unsafe_allow_html=True)
        return

    # 夜間判定（JST 18:00 - 06:00）
    try:
        from modules.market_hours import get_jst_now
        jst_now = get_jst_now()
    except Exception:
        from datetime import timezone, timedelta
        jst_now = datetime.now(timezone(timedelta(hours=9)))

    hour = jst_now.hour
    if hour >= 18 or hour < 6:
        # 夜は星と蛍の両方
        st.markdown(_generate_stars_html(25), unsafe_allow_html=True)
        st.markdown(_generate_fireflies_html(6), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# ティッカーテープ
# ═══════════════════════════════════════════════════════════════════

_TICKER_CSS = """
.ticker-wrap {
    position: relative;
    overflow: hidden;
    background: rgba(6, 9, 15, 0.85);
    border-bottom: 1px solid rgba(212, 175, 55, 0.06);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    padding: 6px 0;
    margin: -1rem -1rem 1rem -1rem;
    z-index: 10;
}
.ticker-track {
    display: flex;
    animation: tickerScroll 40s linear infinite;
    white-space: nowrap;
    width: max-content;
}
.ticker-track:hover { animation-play-state: paused; }
@keyframes tickerScroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
.ticker-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0 20px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78em;
    border-right: 1px solid rgba(255,255,255,0.04);
}
.ticker-name {
    color: #b8b0a2;
    font-weight: 500;
}
.ticker-price {
    color: #f0ece4;
}
"""


def render_ticker_tape(items: list[dict] | None = None) -> None:
    """ティッカーテープを表示する。

    Args:
        items: [{"name": "日経平均", "price": "38,450", "change": "+2.34%", "up": True}, ...]
               Noneの場合はリアルタイムデータを取得する。
    """
    if items is None:
        items = _fetch_ticker_data()

    if not items:
        return

    st.markdown(f"<style>{_TICKER_CSS}</style>", unsafe_allow_html=True)

    # 2倍にして無限スクロール
    item_html = ""
    for item in items:
        color = "#5ca08b" if item.get("up", True) else "#c45c5c"
        change = item.get("change", "")
        item_html += (
            f'<span class="ticker-item">'
            f'<span class="ticker-name">{item["name"]}</span>'
            f'<span class="ticker-price">{item.get("price", "")}</span>'
            f'<span style="color:{color};">{change}</span>'
            f'</span>'
        )

    # 2倍にしてループ
    doubled = item_html * 2
    st.markdown(
        f'<div class="ticker-wrap"><div class="ticker-track">{doubled}</div></div>',
        unsafe_allow_html=True,
    )


def _fetch_ticker_data() -> list[dict]:
    """主要指数のデータを取得する。"""
    try:
        import yfinance as yf
        tickers = {
            "日経平均": "^N225", "TOPIX": "1306.T", "S&P500": "^GSPC",
            "ダウ": "^DJI", "NASDAQ": "^IXIC", "VIX": "^VIX",
            "ドル円": "JPY=X", "金": "GC=F", "原油": "CL=F", "BTC": "BTC-USD",
        }
        items = []
        for name, ticker in tickers.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="2d")
                if hist is not None and len(hist) >= 2:
                    if hasattr(hist.columns, 'levels'):
                        hist.columns = [c[0] if isinstance(c, tuple) else c for c in hist.columns]
                    last = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    change_pct = (last - prev) / prev * 100
                    if name == "ドル円":
                        price = f"¥{last:.2f}"
                    elif name in ("金", "原油", "BTC"):
                        price = f"${last:,.0f}"
                    elif name == "VIX":
                        price = f"{last:.1f}"
                    else:
                        price = f"{last:,.0f}"
                    items.append({
                        "name": name, "price": price,
                        "change": f"{change_pct:+.2f}%",
                        "up": change_pct >= 0,
                    })
            except Exception:
                continue
        return items
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════
# スピードメーターゲージ
# ═══════════════════════════════════════════════════════════════════

_GAUGE_CSS = """
.gauge-container {
    position: relative;
    display: inline-block;
    width: 140px;
    height: 85px;
}
.gauge-bg { stroke: rgba(255,255,255,0.06); }
.gauge-fill {
    stroke-dasharray: 0 170;
    animation: gaugeFill 1.5s ease-out forwards;
    stroke-linecap: round;
}
.gauge-needle {
    transform-origin: 70px 75px;
    animation: gaugeNeedle 1.5s ease-out forwards;
    stroke: #f0ece4;
    stroke-width: 2;
}
@keyframes gaugeFill { to { stroke-dasharray: var(--gv) 170; } }
@keyframes gaugeNeedle {
    0%   { transform: rotate(-90deg); }
    100% { transform: rotate(var(--ga)); }
}
.gauge-label {
    position: absolute;
    bottom: 0; left: 50%;
    transform: translateX(-50%);
    text-align: center;
}
.gauge-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.3em;
    font-weight: 600;
}
.gauge-name {
    font-family: Inter, sans-serif;
    font-size: 0.65em;
    color: #6b7280;
    letter-spacing: 0.1em;
}
"""

_gauge_css_injected = False


def render_gauge(
    value: float,
    min_val: float = 0,
    max_val: float = 100,
    label: str = "",
    thresholds: dict | None = None,
    key: str = "",
) -> None:
    """スピードメーター風ゲージを表示する。

    Args:
        value: 現在の値
        min_val: 最小値
        max_val: 最大値
        label: ラベル（例: "VIX", "RSI"）
        thresholds: 色の閾値。例: {"danger": 70, "warning": 50, "safe": 30}
        key: 一意キー
    """
    global _gauge_css_injected
    if not _gauge_css_injected:
        st.markdown(f"<style>{_GAUGE_CSS}</style>", unsafe_allow_html=True)
        _gauge_css_injected = True

    # 値を0-100にスケーリング
    pct = max(0, min(100, (value - min_val) / (max_val - min_val) * 100))

    # 色の決定
    if thresholds:
        danger = thresholds.get("danger", 70)
        warning = thresholds.get("warning", 50)
        if pct >= danger:
            color = "#c45c5c"
        elif pct >= warning:
            color = "#d4af37"
        else:
            color = "#5ca08b"
    else:
        if pct >= 70:
            color = "#c45c5c"
        elif pct >= 40:
            color = "#d4af37"
        else:
            color = "#5ca08b"

    # SVGパラメータ
    fill_length = pct * 1.7  # max stroke-dasharray = 170
    angle = pct * 1.8 - 90   # -90deg to 90deg

    uid = key or f"gauge_{label}_{id(value)}"

    st.markdown(f"""
    <div class="gauge-container" id="{uid}">
        <svg width="140" height="85" viewBox="0 0 140 85">
            <path class="gauge-bg" d="M10,75 A60,60 0 0,1 130,75"
                fill="none" stroke-width="10"/>
            <path class="gauge-fill" d="M10,75 A60,60 0 0,1 130,75"
                fill="none" stroke="{color}" stroke-width="10"
                style="--gv:{fill_length:.0f};"/>
            <line class="gauge-needle" x1="70" y1="75" x2="70" y2="22"
                style="--ga:{angle:.0f}deg;"/>
            <circle cx="70" cy="75" r="5" fill="{color}"/>
        </svg>
        <div class="gauge-label">
            <div class="gauge-value" style="color:{color};">{value:.1f}</div>
            <div class="gauge-name">{label}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_vix_gauge(vix_value: float) -> None:
    """VIX恐怖指数のゲージを表示する。"""
    render_gauge(
        value=vix_value,
        min_val=10, max_val=50,
        label="VIX 恐怖指数",
        thresholds={"danger": 30, "warning": 20, "safe": 0},
        key="vix_gauge",
    )


def render_rsi_gauge(rsi_value: float) -> None:
    """RSI指標のゲージを表示する。"""
    render_gauge(
        value=rsi_value,
        min_val=0, max_val=100,
        label="RSI (14)",
        thresholds={"danger": 70, "warning": 50, "safe": 30},
        key="rsi_gauge",
    )
