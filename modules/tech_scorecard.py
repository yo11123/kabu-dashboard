"""
テクニカルスコアカード
calc_technical_summary() の結果を受け取り、
色分けされたコンパクトなカードを st.markdown() で描画する。
"""
from __future__ import annotations

import streamlit as st


# ─── 配色定数 ─────────────────────────────────────────────────────
_GREEN = "#5ca08b"   # 買いシグナル
_RED = "#c45c5c"     # 売りシグナル
_GRAY = "#6b7280"    # 中立
_GOLD = "#d4af37"    # アクセント
_BG = "#0a0f1a"      # カード背景
_BG_ROW = "#0e1320"  # 行背景
_TEXT = "#e8ecf1"    # 本文テキスト
_TEXT_DIM = "#8b92a0" # 薄いテキスト


# ─── スコア計算ヘルパー ──────────────────────────────────────────

def _score_rsi(rsi: float | None) -> tuple[int, str, str]:
    """RSI → (スコア/20, シグナル文字列, 色)"""
    if rsi is None:
        return 10, "N/A", _GRAY
    if rsi <= 30:
        # 売られすぎ → 買いシグナル
        score = 20
        return score, "売られすぎ（買い）", _GREEN
    elif rsi >= 70:
        # 買われすぎ → 売りシグナル
        score = 0
        return score, "買われすぎ（売り）", _RED
    else:
        # 中立圏：30-50 は買い寄り、50-70 は売り寄りに傾斜
        score = int(10 + (50 - rsi) / 20 * 10)
        score = max(0, min(20, score))
        return score, "中立", _GRAY


def _score_macd(macd: dict) -> tuple[int, str, str]:
    """MACD → (スコア/20, シグナル文字列, 色)"""
    if not macd:
        return 10, "N/A", _GRAY
    bullish_cross = macd.get("bullish_cross", False)
    bearish_cross = macd.get("bearish_cross", False)
    hist = macd.get("histogram", 0)

    if bullish_cross:
        return 20, "ゴールデンクロス", _GREEN
    elif bearish_cross:
        return 0, "デッドクロス", _RED
    elif hist > 0:
        return 15, "強気（MACD > Signal）", _GREEN
    else:
        return 5, "弱気（MACD < Signal）", _RED


def _score_stochastic(stoch: dict) -> tuple[int, str, str]:
    """ストキャスティクス → (スコア/15, シグナル文字列, 色)"""
    if not stoch:
        return 7, "N/A", _GRAY
    k = stoch.get("k")
    d = stoch.get("d")
    if k is None:
        return 7, "N/A", _GRAY

    if k <= 20:
        return 15, "売られすぎ（買い）", _GREEN
    elif k >= 80:
        return 0, "買われすぎ（売り）", _RED
    else:
        # 中立圏：K の位置で線形補間
        score = int(15 * (80 - k) / 60)
        return max(0, min(15, score)), "中立", _GRAY


def _score_bb(bb_sigma: float | None) -> tuple[int, str, str]:
    """BB σ位置 → (スコア/10, シグナル文字列, 色)"""
    if bb_sigma is None:
        return 5, "N/A", _GRAY
    if bb_sigma <= -2.0:
        return 10, f"−{abs(bb_sigma):.1f}σ（買い）", _GREEN
    elif bb_sigma >= 2.0:
        return 0, f"+{bb_sigma:.1f}σ（売り）", _RED
    elif bb_sigma <= -1.0:
        return 8, f"{bb_sigma:+.1f}σ（やや買い）", _GREEN
    elif bb_sigma >= 1.0:
        return 2, f"+{bb_sigma:.1f}σ（やや売り）", _RED
    else:
        return 5, f"{bb_sigma:+.1f}σ（中立）", _GRAY


def _score_volume(vol_ratio: float | None) -> tuple[int, str, str]:
    """出来高比率 (5日/30日) → (スコア/10, シグナル文字列, 色)"""
    if vol_ratio is None:
        return 5, "N/A", _GRAY
    if vol_ratio >= 1.5:
        # 出来高急増 → 注目度高い（方向は他の指標で判断、ここではやや加点）
        return 8, f"×{vol_ratio:.2f}（活況）", _GREEN
    elif vol_ratio >= 1.1:
        return 6, f"×{vol_ratio:.2f}（やや増加）", _GREEN
    elif vol_ratio <= 0.5:
        return 2, f"×{vol_ratio:.2f}（低調）", _RED
    elif vol_ratio <= 0.8:
        return 4, f"×{vol_ratio:.2f}（やや減少）", _GRAY
    else:
        return 5, f"×{vol_ratio:.2f}（平常）", _GRAY


def _score_trend(above_sma25: bool | None, above_sma75: bool | None) -> tuple[int, str, str]:
    """SMA25/75 との位置関係 → (スコア/15, シグナル文字列, 色)"""
    if above_sma25 is None and above_sma75 is None:
        return 7, "N/A", _GRAY

    score = 0
    parts = []

    if above_sma25 is True:
        score += 7
        parts.append("SMA25↑")
    elif above_sma25 is False:
        parts.append("SMA25↓")

    if above_sma75 is True:
        score += 8
        parts.append("SMA75↑")
    elif above_sma75 is False:
        parts.append("SMA75↓")

    label = "・".join(parts)
    if score >= 12:
        return score, f"{label}（上昇トレンド）", _GREEN
    elif score <= 3:
        return score, f"{label}（下降トレンド）", _RED
    else:
        return score, f"{label}（もみあい）", _GRAY


def _score_52w(pct_from_high: float | None, pct_from_low: float | None) -> tuple[int, str, str]:
    """52週高値/安値からの位置 → (スコア/10, シグナル文字列, 色)"""
    if pct_from_high is None or pct_from_low is None:
        return 5, "N/A", _GRAY

    # 安値に近い = 割安感（買い方向）、高値に近い = 割高感（売り方向）
    total_range = pct_from_low - pct_from_high  # 常に正（高値からは負、安値からは正）
    if total_range <= 0:
        return 5, "N/A", _GRAY

    # 高値からの下落幅が大きいほど買いスコアが高い
    # pct_from_high は負値（-20 なら 20% 下落）
    position = abs(pct_from_high) / total_range * 100  # 0=高値、100=安値

    if position <= 10:
        return 1, f"52週高値圏（{pct_from_high:+.1f}%）", _RED
    elif position <= 30:
        return 3, f"高値寄り（{pct_from_high:+.1f}%）", _RED
    elif position >= 90:
        return 10, f"52週安値圏（安値+{pct_from_low:.1f}%）", _GREEN
    elif position >= 70:
        return 8, f"安値寄り（安値+{pct_from_low:.1f}%）", _GREEN
    else:
        return 5, f"中間（高値{pct_from_high:+.1f}%）", _GRAY


# ─── 総合スコア計算 ──────────────────────────────────────────────

def _calc_total_score(tech: dict) -> tuple[int, list[dict]]:
    """
    tech dict から総合スコア (0-100) と各指標の詳細リストを返す。
    各指標は {name, value_text, score, max_score, signal, color, pct} の辞書。
    """
    rows: list[dict] = []

    # RSI (20pt)
    rsi_val = tech.get("rsi")
    rsi_score, rsi_signal, rsi_color = _score_rsi(rsi_val)
    rows.append({
        "name": "RSI(14)",
        "value_text": f"{rsi_val:.1f}" if rsi_val is not None else "N/A",
        "score": rsi_score,
        "max_score": 20,
        "signal": rsi_signal,
        "color": rsi_color,
        "pct": (rsi_val / 100) if rsi_val is not None else 0.5,  # ゲージ用 0-1
    })

    # MACD (20pt)
    macd_data = tech.get("macd", {})
    macd_score, macd_signal, macd_color = _score_macd(macd_data)
    macd_hist = macd_data.get("histogram", 0)
    rows.append({
        "name": "MACD",
        "value_text": f"Hist: {macd_hist:+.2f}" if macd_data else "N/A",
        "score": macd_score,
        "max_score": 20,
        "signal": macd_signal,
        "color": macd_color,
        "pct": max(0, min(1, (macd_score / 20))),
    })

    # ストキャスティクス (15pt)
    stoch_data = tech.get("stochastic", {})
    stoch_score, stoch_signal, stoch_color = _score_stochastic(stoch_data)
    k_val = stoch_data.get("k")
    d_val = stoch_data.get("d")
    stoch_text = f"%K:{k_val:.0f} %D:{d_val:.0f}" if k_val is not None and d_val is not None else "N/A"
    rows.append({
        "name": "ストキャスティクス",
        "value_text": stoch_text,
        "score": stoch_score,
        "max_score": 15,
        "signal": stoch_signal,
        "color": stoch_color,
        "pct": (k_val / 100) if k_val is not None else 0.5,
    })

    # BB位置 (10pt)
    bb_sigma = tech.get("bb_sigma")
    bb_score, bb_signal, bb_color = _score_bb(bb_sigma)
    rows.append({
        "name": "BB位置",
        "value_text": f"{bb_sigma:+.2f}σ" if bb_sigma is not None else "N/A",
        "score": bb_score,
        "max_score": 10,
        "signal": bb_signal,
        "color": bb_color,
        "pct": max(0, min(1, (bb_sigma + 3) / 6)) if bb_sigma is not None else 0.5,
    })

    # 出来高比率 (10pt)
    vol_ratio = tech.get("volume_ratio_5d_30d")
    vol_score, vol_signal, vol_color = _score_volume(vol_ratio)
    rows.append({
        "name": "出来高比率",
        "value_text": f"×{vol_ratio:.2f}" if vol_ratio is not None else "N/A",
        "score": vol_score,
        "max_score": 10,
        "signal": vol_signal,
        "color": vol_color,
        "pct": max(0, min(1, vol_ratio / 2)) if vol_ratio is not None else 0.5,
    })

    # トレンド (15pt)
    trend_score, trend_signal, trend_color = _score_trend(
        tech.get("above_sma25"), tech.get("above_sma75")
    )
    rows.append({
        "name": "トレンド",
        "value_text": trend_signal.split("（")[0] if "（" in trend_signal else trend_signal,
        "score": trend_score,
        "max_score": 15,
        "signal": trend_signal,
        "color": trend_color,
        "pct": trend_score / 15,
    })

    # 52週位置 (10pt)
    w52_score, w52_signal, w52_color = _score_52w(
        tech.get("pct_from_52w_high"), tech.get("pct_from_52w_low")
    )
    rows.append({
        "name": "52週高値/安値",
        "value_text": w52_signal.split("（")[0] if "（" in w52_signal else w52_signal,
        "score": w52_score,
        "max_score": 10,
        "signal": w52_signal,
        "color": w52_color,
        "pct": w52_score / 10,
    })

    total = sum(r["score"] for r in rows)
    return total, rows


# ─── 総合スコアのラベルと色 ──────────────────────────────────────

def _total_label(score: int) -> tuple[str, str]:
    """総合スコアに対する判定ラベルと色を返す。"""
    if score >= 75:
        return "強気買い", _GREEN
    elif score >= 60:
        return "買い", _GREEN
    elif score >= 40:
        return "中立", _GRAY
    elif score >= 25:
        return "売り", _RED
    else:
        return "強気売り", _RED


# ─── HTML レンダリング ───────────────────────────────────────────

def _bar_html(pct: float, color: str, width_px: int = 80) -> str:
    """ミニゲージバーの HTML を生成する。"""
    fill = max(0, min(100, pct * 100))
    return (
        f'<div style="width:{width_px}px;height:6px;background:#1a1f2e;border-radius:3px;overflow:hidden;">'
        f'<div style="width:{fill:.0f}%;height:100%;background:{color};border-radius:3px;'
        f'transition:width 0.3s;"></div></div>'
    )


def _signal_badge(text: str, color: str) -> str:
    """シグナルバッジの HTML を生成する。"""
    # 買い/売り/中立 を短縮表記で抽出
    if "買い" in text:
        short = "買い"
    elif "売り" in text:
        short = "売り"
    else:
        short = "中立"
    return (
        f'<span style="display:inline-block;padding:1px 8px;border-radius:10px;'
        f'font-size:0.7em;font-weight:600;letter-spacing:0.05em;'
        f'background:{color}22;color:{color};border:1px solid {color}44;">'
        f'{short}</span>'
    )


def render_scorecard(tech: dict, current_price: float) -> None:
    """
    テクニカルスコアカードを Streamlit に描画する。

    Parameters
    ----------
    tech : dict
        calc_technical_summary() が返す辞書。
    current_price : float
        現在の株価。
    """
    total_score, rows = _calc_total_score(tech)
    total_label, total_color = _total_label(total_score)

    # ── 総合スコアのリングゲージ（SVG）──
    # 円周 = 2πr ≈ 251.3 (r=40)
    circumference = 251.3
    offset = circumference * (1 - total_score / 100)

    ring_svg = f'''
    <svg width="90" height="90" viewBox="0 0 90 90">
      <circle cx="45" cy="45" r="40" fill="none" stroke="#1a1f2e" stroke-width="6"/>
      <circle cx="45" cy="45" r="40" fill="none" stroke="{total_color}" stroke-width="6"
        stroke-dasharray="{circumference}" stroke-dashoffset="{offset:.1f}"
        stroke-linecap="round" transform="rotate(-90 45 45)"
        style="transition: stroke-dashoffset 0.6s ease;"/>
      <text x="45" y="42" text-anchor="middle" fill="{_TEXT}" font-size="22"
        font-family="IBM Plex Mono,monospace" font-weight="600">{total_score}</text>
      <text x="45" y="58" text-anchor="middle" fill="{_TEXT_DIM}" font-size="9"
        font-family="Inter,sans-serif">/ 100</text>
    </svg>
    '''

    # ── 各指標の行 HTML ──
    indicator_rows_html = ""
    for row in rows:
        bar = _bar_html(row["pct"], row["color"])
        badge = _signal_badge(row["signal"], row["color"])
        score_text = f'{row["score"]}/{row["max_score"]}'

        indicator_rows_html += f'''
        <div style="display:grid;grid-template-columns:120px 90px 90px 1fr 50px;
            align-items:center;gap:8px;padding:8px 14px;
            background:{_BG_ROW};border-radius:4px;margin-bottom:3px;">
          <span style="font-size:0.78em;color:{_TEXT};font-weight:500;
              font-family:'Noto Sans JP',sans-serif;white-space:nowrap;">
            {row["name"]}
          </span>
          <span style="font-size:0.75em;color:{_TEXT_DIM};
              font-family:'IBM Plex Mono',monospace;white-space:nowrap;">
            {row["value_text"]}
          </span>
          <span>{bar}</span>
          <span style="text-align:center;">{badge}</span>
          <span style="font-size:0.72em;color:{row["color"]};text-align:right;
              font-family:'IBM Plex Mono',monospace;font-weight:600;">
            {score_text}
          </span>
        </div>
        '''

    # ── カード全体を組み立て ──
    html = f'''
    <div style="background:{_BG};border:1px solid rgba(212,175,55,0.06);
        border-radius:6px;padding:20px 24px;margin-bottom:16px;">

      <!-- ヘッダー: 総合スコア -->
      <div style="display:flex;align-items:center;gap:20px;margin-bottom:16px;
          padding-bottom:14px;border-bottom:1px solid #1a1f2e;">
        <div>{ring_svg}</div>
        <div>
          <div style="font-family:'Cormorant Garamond','Noto Sans JP',serif;
              font-size:1.15em;color:{_TEXT};letter-spacing:0.05em;font-weight:400;">
            テクニカルスコア
          </div>
          <div style="font-size:1.3em;font-weight:700;color:{total_color};
              font-family:'Inter',sans-serif;margin-top:2px;">
            {total_label}
          </div>
          <div style="font-size:0.72em;color:{_TEXT_DIM};margin-top:4px;
              font-family:'Inter',sans-serif;">
            現在値 ¥{current_price:,.0f}　|　RSI {tech.get("rsi", "N/A")}　|
            BB {tech.get("bb_sigma", "N/A")}σ
          </div>
        </div>
      </div>

      <!-- 指標ヘッダー -->
      <div style="display:grid;grid-template-columns:120px 90px 90px 1fr 50px;
          align-items:center;gap:8px;padding:4px 14px;margin-bottom:4px;">
        <span style="font-size:0.65em;color:{_TEXT_DIM};text-transform:uppercase;
            letter-spacing:0.12em;font-family:'Inter',sans-serif;">指標</span>
        <span style="font-size:0.65em;color:{_TEXT_DIM};text-transform:uppercase;
            letter-spacing:0.12em;font-family:'Inter',sans-serif;">値</span>
        <span style="font-size:0.65em;color:{_TEXT_DIM};text-transform:uppercase;
            letter-spacing:0.12em;font-family:'Inter',sans-serif;">ゲージ</span>
        <span style="font-size:0.65em;color:{_TEXT_DIM};text-transform:uppercase;
            letter-spacing:0.12em;text-align:center;font-family:'Inter',sans-serif;">
          シグナル</span>
        <span style="font-size:0.65em;color:{_TEXT_DIM};text-transform:uppercase;
            letter-spacing:0.12em;text-align:right;font-family:'Inter',sans-serif;">
          点数</span>
      </div>

      <!-- 指標行 -->
      {indicator_rows_html}

      <!-- フッター -->
      <div style="margin-top:10px;padding-top:8px;border-top:1px solid #1a1f2e;
          font-size:0.62em;color:{_TEXT_DIM};font-family:'Inter',sans-serif;
          letter-spacing:0.03em;">
        ※ スコアは各テクニカル指標を加重合計した参考値です。投資助言ではありません。
      </div>
    </div>
    '''

    st.markdown(html, unsafe_allow_html=True)
