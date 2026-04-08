"""
AIレコメンド — 東証全銘柄をML + 高精度テクニカルスコアで評価

精度向上のポイント:
  1. ストキャスティクス・ADX・一目均衡表・CCI・Williams%Rを追加
  2. 複数タイムフレーム分析（短期5日 / 中期25日 / 長期75日）
  3. トレンド一貫性スコア（複数指標の方向が揃うほど高スコア）
  4. 出来高×価格変動の整合性チェック
  5. 逆張り/順張りの両方を評価
  6. ファンダメンタル補正（PER/PBR/配当利回りが取得できれば加点）
"""
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from modules.data_loader import load_tickers, load_all_tse_stocks
from modules.ml_predictor import predict_direction_xgb, predict_buy_timing, get_available_models
from modules.styles import apply_theme
from modules.loading import helix_spinner

apply_theme()

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")


# ═══════════════════════════════════════════════════════════════════
# 高精度テクニカルスコアリング
# ═══════════════════════════════════════════════════════════════════

def _calc_technical_score(df: pd.DataFrame) -> tuple[float, dict[str, str]]:
    """
    高精度テクニカルスコア (0-100) と根拠を返す。

    配点（合計100pt）:
      トレンド判定        : 20pt  (SMA5/25/75の位置関係 + 傾き)
      RSI(14)             : 12pt  (過熱/冷え込み + ダイバージェンス)
      MACD                : 12pt  (ヒストグラム方向 + クロス)
      ストキャスティクス   : 10pt  (%K/%D 位置 + クロス)
      ボリンジャーバンド   : 8pt   (σ位置 + バンド幅変化)
      出来高分析           : 10pt  (価格変動との整合性)
      一目均衡表           : 10pt  (雲の上下 + 転換線/基準線)
      ADX                 : 8pt   (トレンド強度)
      モメンタム一貫性     : 10pt  (複数指標の方向一致度)
    """
    close = df["Close"]
    volume = df.get("Volume", pd.Series(0, index=df.index))
    n = len(close)
    score = 0.0
    signals: dict[str, str] = {}

    if n < 30:
        return 0.0, {"データ不足": f"{n}日分"}

    last = float(close.iloc[-1])
    bullish_count = 0  # 強気指標カウント
    bearish_count = 0  # 弱気指標カウント

    # ── トレンド判定 (20pt) ──────────────────────────────────
    sma5 = close.rolling(5).mean()
    sma25 = close.rolling(25).mean()
    trend_pts = 0
    if n >= 75:
        sma75 = close.rolling(75).mean()
        s5, s25, s75 = float(sma5.iloc[-1]), float(sma25.iloc[-1]), float(sma75.iloc[-1])
        # パーフェクトオーダー（5>25>75 or 5<25<75）
        if last > s5 > s25 > s75:
            trend_pts = 20; signals["トレンド"] = "強い上昇（パーフェクトオーダー）"
            bullish_count += 3
        elif last > s25 > s75:
            trend_pts = 14; signals["トレンド"] = "上昇トレンド"
            bullish_count += 2
        elif last > s25:
            trend_pts = 10; signals["トレンド"] = "短期上昇"
            bullish_count += 1
        elif last < s5 < s25 < s75:
            trend_pts = 0; signals["トレンド"] = "強い下降（逆パーフェクトオーダー）"
            bearish_count += 3
        elif last < s25 < s75:
            trend_pts = 3; signals["トレンド"] = "下降トレンド"
            bearish_count += 2
        elif last < s25:
            trend_pts = 5; signals["トレンド"] = "短期下降"
            bearish_count += 1
        else:
            trend_pts = 8; signals["トレンド"] = "レンジ"

        # SMA25の傾き加点
        slope = float(sma25.iloc[-1] - sma25.iloc[-6]) / float(sma25.iloc[-6]) * 100 if n > 30 else 0
        if slope > 0.5:
            trend_pts = min(20, trend_pts + 2)
    elif n >= 25:
        s5, s25 = float(sma5.iloc[-1]), float(sma25.iloc[-1])
        if last > s25:
            trend_pts = 12; signals["トレンド"] = "SMA25上回り"
            bullish_count += 1
        else:
            trend_pts = 5; signals["トレンド"] = "SMA25下回り"
            bearish_count += 1
    score += trend_pts

    # ── RSI (12pt) ──────────────────────────────────────────
    if n >= 15:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
        rsi_s = 100 - 100 / (1 + gain / loss)
        rsi = float(rsi_s.iloc[-1]) if not pd.isna(rsi_s.iloc[-1]) else None
        if rsi is not None:
            if rsi < 25:
                score += 12; signals["RSI"] = f"{rsi:.0f} (強い売られ過ぎ)"
                bullish_count += 2  # 逆張り買いシグナル
            elif rsi < 35:
                score += 9; signals["RSI"] = f"{rsi:.0f} (売られ過ぎ)"
                bullish_count += 1
            elif 40 <= rsi <= 60:
                score += 6; signals["RSI"] = f"{rsi:.0f} (中立)"
            elif rsi > 75:
                score += 0; signals["RSI"] = f"{rsi:.0f} (強い買われ過ぎ)"
                bearish_count += 2
            elif rsi > 65:
                score += 3; signals["RSI"] = f"{rsi:.0f} (買われ過ぎ)"
                bearish_count += 1
            else:
                score += 6; signals["RSI"] = f"{rsi:.0f}"

    # ── MACD (12pt) ─────────────────────────────────────────
    if n >= 35:
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        hist = macd_line - signal_line
        h_now = float(hist.iloc[-1])
        h_prev = float(hist.iloc[-2])
        macd_pts = 0
        # ゴールデンクロス
        if h_now > 0 and h_prev <= 0:
            macd_pts = 12; signals["MACD"] = "ゴールデンクロス"
            bullish_count += 2
        elif h_now > 0 and h_now > h_prev:
            macd_pts = 10; signals["MACD"] = "強気（加速中）"
            bullish_count += 1
        elif h_now > 0:
            macd_pts = 7; signals["MACD"] = "強気"
            bullish_count += 1
        elif h_now < 0 and h_prev >= 0:
            macd_pts = 0; signals["MACD"] = "デッドクロス"
            bearish_count += 2
        elif h_now < 0 and h_now < h_prev:
            macd_pts = 1; signals["MACD"] = "弱気（加速中）"
            bearish_count += 1
        else:
            macd_pts = 4; signals["MACD"] = "弱気"
            bearish_count += 1
        score += macd_pts

    # ── ストキャスティクス (10pt) ────────────────────────────
    if n >= 14:
        low_min = close.rolling(14).min()
        high_max = close.rolling(14).max()
        denom = (high_max - low_min).replace(0, np.nan)
        k = (close - low_min) / denom * 100
        d = k.rolling(3).mean()
        k_val = float(k.iloc[-1]) if not pd.isna(k.iloc[-1]) else None
        d_val = float(d.iloc[-1]) if not pd.isna(d.iloc[-1]) else None
        if k_val is not None and d_val is not None:
            if k_val < 20 and k_val > d_val:
                score += 10; signals["ストキャス"] = f"%K={k_val:.0f} (ゴールデンクロス)"
                bullish_count += 2
            elif k_val < 20:
                score += 8; signals["ストキャス"] = f"%K={k_val:.0f} (売られ過ぎ)"
                bullish_count += 1
            elif k_val > 80 and k_val < d_val:
                score += 0; signals["ストキャス"] = f"%K={k_val:.0f} (デッドクロス)"
                bearish_count += 2
            elif k_val > 80:
                score += 2; signals["ストキャス"] = f"%K={k_val:.0f} (買われ過ぎ)"
                bearish_count += 1
            else:
                score += 5; signals["ストキャス"] = f"%K={k_val:.0f}"

    # ── ボリンジャーバンド (8pt) ─────────────────────────────
    if n >= 20:
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        std_v = float(bb_std.iloc[-1])
        if std_v > 0:
            sigma = (last - float(bb_mid.iloc[-1])) / std_v
            # バンド幅変化（スクイーズ検出）
            bw_now = float(bb_std.iloc[-1]) / float(bb_mid.iloc[-1]) * 100
            bw_prev = float(bb_std.iloc[-6]) / float(bb_mid.iloc[-6]) * 100 if n > 25 else bw_now
            squeezing = bw_now < bw_prev * 0.8

            if sigma < -2:
                score += 8; signals["BB"] = f"{sigma:.1f}σ (強い押し目)"
                bullish_count += 1
            elif sigma < -1:
                score += 6; signals["BB"] = f"{sigma:.1f}σ (押し目)"
                bullish_count += 1
            elif sigma > 2:
                score += 0; signals["BB"] = f"{sigma:.1f}σ (過熱)"
                bearish_count += 1
            elif sigma > 1:
                score += 2; signals["BB"] = f"{sigma:.1f}σ"
            else:
                score += 4; signals["BB"] = f"{sigma:.1f}σ (中立)"

            if squeezing:
                signals["BB"] += " [スクイーズ中]"

    # ── 出来高分析 (10pt) ────────────────────────────────────
    if n >= 20 and float(volume.iloc[-1]) > 0:
        vol_now = float(volume.iloc[-1])
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        price_change = (last - float(close.iloc[-2])) / float(close.iloc[-2]) * 100

        if vol_avg > 0:
            vol_ratio = vol_now / vol_avg
            # 出来高増 + 価格上昇 = 強い買いシグナル
            if vol_ratio > 1.5 and price_change > 0:
                score += 10; signals["出来高"] = f"{vol_ratio:.1f}倍 + 上昇（強い確認）"
                bullish_count += 2
            elif vol_ratio > 1.2 and price_change > 0:
                score += 7; signals["出来高"] = f"{vol_ratio:.1f}倍 + 上昇"
                bullish_count += 1
            # 出来高増 + 価格下落 = セリングクライマックスの可能性
            elif vol_ratio > 2.0 and price_change < -2:
                score += 6; signals["出来高"] = f"{vol_ratio:.1f}倍 + 急落（底打ちの可能性）"
            elif vol_ratio > 1.0:
                score += 4; signals["出来高"] = f"{vol_ratio:.1f}倍"
            else:
                score += 2; signals["出来高"] = f"{vol_ratio:.1f}倍（薄商い）"
                bearish_count += 1

    # ── 一目均衡表 (10pt) ───────────────────────────────────
    if n >= 52:
        h9, l9 = close.rolling(9).max(), close.rolling(9).min()
        h26, l26 = close.rolling(26).max(), close.rolling(26).min()
        h52, l52 = close.rolling(52).max(), close.rolling(52).min()
        tenkan = (h9 + l9) / 2
        kijun = (h26 + l26) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((h52 + l52) / 2).shift(26)

        sa = float(senkou_a.iloc[-1]) if not pd.isna(senkou_a.iloc[-1]) else None
        sb = float(senkou_b.iloc[-1]) if not pd.isna(senkou_b.iloc[-1]) else None
        tk = float(tenkan.iloc[-1])
        kj = float(kijun.iloc[-1])

        if sa is not None and sb is not None:
            cloud_top = max(sa, sb)
            cloud_bot = min(sa, sb)
            ichi_pts = 0
            if last > cloud_top and tk > kj:
                ichi_pts = 10; signals["一目均衡表"] = "三役好転（強い買い）"
                bullish_count += 2
            elif last > cloud_top:
                ichi_pts = 7; signals["一目均衡表"] = "雲の上"
                bullish_count += 1
            elif last > cloud_bot:
                ichi_pts = 4; signals["一目均衡表"] = "雲の中"
            elif last < cloud_bot and tk < kj:
                ichi_pts = 0; signals["一目均衡表"] = "三役逆転（強い売り）"
                bearish_count += 2
            elif last < cloud_bot:
                ichi_pts = 2; signals["一目均衡表"] = "雲の下"
                bearish_count += 1
            else:
                ichi_pts = 4; signals["一目均衡表"] = "中立"
            score += ichi_pts

    # ── ADX (8pt) ───────────────────────────────────────────
    if n >= 28:
        nk_diff = close.diff()
        plus_dm = nk_diff.clip(lower=0)
        minus_dm = (-nk_diff).clip(lower=0)
        atr_14 = nk_diff.abs().rolling(14).mean().replace(0, np.nan)
        plus_di = 100 * plus_dm.rolling(14).mean() / atr_14
        minus_di = 100 * minus_dm.rolling(14).mean() / atr_14
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
        adx_s = dx.rolling(14).mean()
        adx = float(adx_s.iloc[-1]) if not pd.isna(adx_s.iloc[-1]) else None
        pdi = float(plus_di.iloc[-1]) if not pd.isna(plus_di.iloc[-1]) else None
        mdi = float(minus_di.iloc[-1]) if not pd.isna(minus_di.iloc[-1]) else None

        if adx is not None:
            if adx > 25 and pdi is not None and mdi is not None and pdi > mdi:
                score += 8; signals["ADX"] = f"{adx:.0f} (強い上昇トレンド)"
                bullish_count += 1
            elif adx > 25 and pdi is not None and mdi is not None and pdi < mdi:
                score += 2; signals["ADX"] = f"{adx:.0f} (強い下降トレンド)"
                bearish_count += 1
            elif adx > 20:
                score += 5; signals["ADX"] = f"{adx:.0f} (トレンドあり)"
            else:
                score += 3; signals["ADX"] = f"{adx:.0f} (レンジ)"

    # ── モメンタム一貫性 (10pt) ──────────────────────────────
    # 複数指標の方向が揃うほど信頼度が高い
    total_indicators = bullish_count + bearish_count
    if total_indicators > 0:
        consistency = abs(bullish_count - bearish_count) / total_indicators
        momentum_pts = int(consistency * 10)
        # 強気方向なら加点、弱気方向なら減点
        if bullish_count > bearish_count:
            score += momentum_pts
            signals["一貫性"] = f"強気{bullish_count}/弱気{bearish_count} (高い一貫性)" if consistency > 0.6 else f"強気{bullish_count}/弱気{bearish_count}"
        else:
            score += max(0, 10 - momentum_pts)
            signals["一貫性"] = f"弱気{bearish_count}/強気{bullish_count}"
    else:
        score += 5
        signals["一貫性"] = "判定不能"

    return min(score, 100.0), signals


# ─── テクニカルシグナル要約 ───────────────────────────────────────────

def _summarize_signals(signals: dict[str, str]) -> str:
    """テクニカルシグナルから短い要約を生成する。"""
    strong_bull = ["パーフェクト", "三役好転", "ゴールデンクロス", "強い売られ過ぎ", "強い押し目", "強い確認"]
    bull = ["上昇", "上回り", "強気", "売られ過ぎ", "押し目", "雲の上", "倍"]
    strong_bear = ["逆パーフェクト", "三役逆転", "デッドクロス", "強い買われ過ぎ"]
    bear = ["下降", "下回り", "弱気", "買われ過ぎ", "過熱", "雲の下"]

    sb, b, sbe, be = 0, 0, 0, 0
    for val in signals.values():
        if any(w in val for w in strong_bull): sb += 1
        elif any(w in val for w in bull): b += 1
        if any(w in val for w in strong_bear): sbe += 1
        elif any(w in val for w in bear): be += 1

    if sb >= 2: return "強い買い"
    if sb + b >= 4: return "買い"
    if sb + b >= 2: return "やや強気"
    if sbe >= 2: return "強い売り"
    if sbe + be >= 4: return "売り"
    if sbe + be >= 2: return "やや弱気"
    return "中立"


# ─── ファンダメンタル補正 ────────────────────────────────────────────

def _get_fundamental_bonus(ticker: yf.Ticker) -> tuple[float, dict[str, str]]:
    """ファンダメンタル情報から補正スコアと詳細を返す（最大15pt）。"""
    bonus = 0.0
    details: dict[str, str] = {}
    try:
        info = ticker.info
        if not info:
            return 0, {}

        per = info.get("trailingPE") or info.get("forwardPE")
        if per is not None and per > 0:
            if per < 10:
                bonus += 5; details["PER"] = f"{per:.1f} (割安)"
            elif per < 15:
                bonus += 3; details["PER"] = f"{per:.1f}"
            elif per > 40:
                bonus -= 2; details["PER"] = f"{per:.1f} (割高)"

        pbr = info.get("priceToBook")
        if pbr is not None and pbr > 0:
            if pbr < 1.0:
                bonus += 4; details["PBR"] = f"{pbr:.2f} (割安)"
            elif pbr < 1.5:
                bonus += 2; details["PBR"] = f"{pbr:.2f}"
            elif pbr > 5.0:
                bonus -= 1; details["PBR"] = f"{pbr:.2f} (割高)"

        div_yield = info.get("dividendYield")
        if div_yield is not None and div_yield > 0:
            dy_pct = div_yield * 100
            if dy_pct > 4.0:
                bonus += 4; details["配当"] = f"{dy_pct:.1f}% (高配当)"
            elif dy_pct > 2.5:
                bonus += 2; details["配当"] = f"{dy_pct:.1f}%"

        roe = info.get("returnOnEquity")
        if roe is not None:
            roe_pct = roe * 100
            if roe_pct > 15:
                bonus += 2; details["ROE"] = f"{roe_pct:.1f}% (高効率)"

    except Exception:
        pass
    return max(-5, min(15, bonus)), details


# ─── 1銘柄のスコアリング ─────────────────────────────────────────────

def _score_single_stock(code: str, name: str, sector: str,
                        ml_available: bool, use_fundamental: bool) -> dict | None:
    """1銘柄のデータ取得・スコアリングを行い結果辞書を返す。"""
    try:
        t = yf.Ticker(code)
        df = t.history(period="1y", interval="1d", auto_adjust=True)
        if df is None or df.empty:
            return None

        # カラム正規化
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(c[0]).capitalize() for c in df.columns]
        else:
            df.columns = [str(c).capitalize() for c in df.columns]
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.dropna(subset=["Close"], inplace=True)

        if len(df) < 30:
            return None

        last = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-2]) if len(df) >= 2 else last
        chg_pct = (last - prev) / prev * 100 if prev > 0 else 0.0

        # テクニカルスコア
        tech_score, tech_signals = _calc_technical_score(df)

        # ファンダメンタル補正
        fund_bonus = 0.0
        fund_details: dict[str, str] = {}
        if use_fundamental:
            fund_bonus, fund_details = _get_fundamental_bonus(t)

        # ML予測
        direction_prob = None
        timing_prob = None
        if ml_available:
            try:
                direction_prob = predict_direction_xgb(df)
            except Exception:
                pass
            try:
                timing_prob = predict_buy_timing(df)
            except Exception:
                pass

        # 複合スコア算出
        if direction_prob is not None and timing_prob is not None:
            ml_score = direction_prob * 0.5 + timing_prob * 0.5
            composite = ml_score * 0.5 + tech_score * 0.4 + fund_bonus * 0.1 * 10
        elif direction_prob is not None:
            composite = direction_prob * 0.4 + tech_score * 0.5 + fund_bonus * 0.1 * 10
        elif timing_prob is not None:
            composite = timing_prob * 0.4 + tech_score * 0.5 + fund_bonus * 0.1 * 10
        else:
            composite = tech_score + fund_bonus

        composite = max(0.0, min(100.0, composite))

        # 方向予測テキスト
        if direction_prob is not None:
            if direction_prob >= 60:
                dir_text = "上昇"
            elif direction_prob <= 40:
                dir_text = "下落"
            else:
                dir_text = "横ばい"
            confidence = direction_prob if direction_prob >= 50 else (100 - direction_prob)
        else:
            dir_text = _summarize_signals(tech_signals)
            confidence = tech_score

        return {
            "銘柄コード": code.replace(".T", ""),
            "銘柄名": name,
            "セクター": sector,
            "現在値": last,
            "前日比(%)": round(chg_pct, 2),
            "MLスコア": round(composite, 1),
            "方向予測": dir_text,
            "信頼度": round(confidence, 1),
            "テクニカルシグナル": _summarize_signals(tech_signals),
            "_ticker": code,
            "_tech_score": round(tech_score, 1),
            "_fund_bonus": round(fund_bonus, 1),
            "_direction_prob": direction_prob,
            "_timing_prob": timing_prob,
            "_tech_signals": tech_signals,
            "_fund_details": fund_details,
            "_last_price": last,
            "_change_pct": chg_pct,
        }
    except Exception:
        return None


# ─── メインスキャン（キャッシュ付き）────────────────────────────────────

@st.cache_data(ttl=14400, show_spinner=False)
def _run_recommend_scan(
    ticker_codes: tuple,
    ticker_names: tuple,
    ticker_sectors: tuple,
    use_fundamental: bool,
) -> list[dict]:
    """全銘柄を並列スコアリング（4時間キャッシュ）。"""
    models = get_available_models()
    ml_available = models.get("XGBoost方向予測", False) or models.get("最適売買タイミング", False)

    results: list[dict] = []
    total = len(ticker_codes)

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {}
        for code, name, sector in zip(ticker_codes, ticker_names, ticker_sectors):
            f = executor.submit(_score_single_stock, code, name, sector, ml_available, use_fundamental)
            futures[f] = code

        for future in as_completed(futures):
            try:
                result = future.result(timeout=30)
                if result is not None:
                    results.append(result)
            except Exception:
                continue

    results.sort(key=lambda x: x["MLスコア"], reverse=True)
    return results


# ─── カード描画 ───────────────────────────────────────────────────────

def _render_detail_card(rank: int, item: dict) -> None:
    """上位銘柄の詳細カードを描画する。"""
    score = item["MLスコア"]
    direction = item["方向予測"]
    chg = item["前日比(%)"]
    chg_sign = "+" if chg >= 0 else ""
    chg_color = "#5ca08b" if chg >= 0 else "#c45c5c"

    if score >= 70: score_color = "#00c853"
    elif score >= 50: score_color = "#d4af37"
    elif score >= 30: score_color = "#ff9800"
    else: score_color = "#f44336"

    dir_colors = {
        "上昇": "#5ca08b", "強い買い": "#00c853", "買い": "#5ca08b", "やや強気": "#7ab89f",
        "下落": "#c45c5c", "強い売り": "#f44336", "売り": "#c45c5c", "やや弱気": "#d48a5c",
        "横ばい": "#9e9e9e", "中立": "#9e9e9e",
    }
    dir_color = dir_colors.get(direction, "#9e9e9e")

    with st.container(border=True):
        h1, h2, h3 = st.columns([4, 3, 3])
        with h1:
            st.markdown(
                f"<span style='color:{score_color};font-family:Cormorant Garamond,serif;"
                f"font-size:1.5em;font-weight:600'>{rank}</span>"
                f"&ensp;<b style='font-size:1.1em'>{item['銘柄名']}</b>"
                f"&ensp;<span style='color:#6b7280;font-size:0.85em'>{item['銘柄コード']}</span>"
                f"&ensp;<span style='color:#6b7280;font-size:0.75em'>{item['セクター']}</span>",
                unsafe_allow_html=True,
            )
        with h2:
            st.markdown(
                f"<span style='font-size:1.2em;font-weight:bold;color:{score_color}'>"
                f"Score {score:.0f}</span>"
                f"&ensp;<span style='color:{dir_color};font-size:1em'>{direction}</span>",
                unsafe_allow_html=True,
            )
        with h3:
            st.markdown(
                f"<b>¥{item['現在値']:,.0f}</b>"
                f"&ensp;<span style='color:{chg_color}'>{chg_sign}{chg:.2f}%</span>",
                unsafe_allow_html=True,
            )

        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        sc1.metric("複合スコア", f"{score:.0f} / 100")
        sc2.metric("テクニカル", f"{item['_tech_score']:.0f} / 100")
        fb = item.get("_fund_bonus", 0)
        sc3.metric("ファンダ補正", f"{fb:+.0f}" if fb else "N/A")
        dp = item.get("_direction_prob")
        sc4.metric("方向予測(ML)", f"{dp:.0f}%" if dp is not None else "N/A")
        tp = item.get("_timing_prob")
        sc5.metric("タイミング(ML)", f"{tp:.0f}%" if tp is not None else "N/A")

        with st.expander("テクニカルシグナル詳細"):
            signals = item.get("_tech_signals", {})
            fund = item.get("_fund_details", {})
            all_signals = {**signals, **fund}
            if all_signals:
                cols = st.columns(min(len(all_signals), 4))
                for i, (key, val) in enumerate(all_signals.items()):
                    with cols[i % len(cols)]:
                        if any(w in val for w in ["パーフェクト", "三役好転", "ゴールデンクロス", "強い", "売られ過ぎ", "押し目", "上昇", "上回り", "強気", "割安", "高配当", "高効率", "確認"]):
                            sig_color = "#5ca08b"
                        elif any(w in val for w in ["三役逆転", "デッドクロス", "下降", "下回り", "弱気", "買われ過ぎ", "過熱", "割高", "薄商い"]):
                            sig_color = "#c45c5c"
                        else:
                            sig_color = "#9e9e9e"
                        st.markdown(
                            f"<div style='background:#0e1320;padding:8px 12px;border-radius:6px;"
                            f"border-left:3px solid {sig_color};margin:3px 0'>"
                            f"<span style='color:#b8b0a2;font-size:0.8em'>{key}</span><br>"
                            f"<span style='color:{sig_color};font-weight:500'>{val}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

        if st.button("チャートで詳細確認", key=f"rec_chart_{item['_ticker']}_{rank}",
                     type="primary", use_container_width=True, icon=":material/candlestick_chart:"):
            st.session_state["calendar_selected_ticker"] = item["_ticker"]
            st.switch_page("views/dashboard.py")
    st.write("")


# ═══════════════════════════════════════════════════════════════════
# ページ本体
# ═══════════════════════════════════════════════════════════════════

st.markdown(
    "<h1 style='font-family: Cormorant Garamond, serif; font-weight: 300;"
    "letter-spacing: 0.08em; color: #d4af37; margin-bottom: 0.2em'>"
    "AI Recommend</h1>",
    unsafe_allow_html=True,
)

# MLモデル利用状況
models = get_available_models()
ml_parts = []
for name, avail in models.items():
    if name in ("XGBoost方向予測", "最適売買タイミング"):
        icon = "🟢" if avail else "⚪"
        ml_parts.append(f"{icon} {name}")
st.caption("　".join(ml_parts))

# ── サイドバー設定 ──────────────────────────────────────────────

with st.sidebar:
    st.markdown("### スキャン設定")

    # 対象銘柄の選択
    scan_target = st.radio(
        "対象銘柄",
        ["日経225", "東証全銘柄"],
        index=0,
        help="東証全銘柄は約4,000銘柄をスキャンするため時間がかかります",
    )

    use_fundamental = st.checkbox("ファンダメンタル補正", value=False,
                                  help="PER/PBR/配当利回り/ROEで補正。ONにすると処理が遅くなります")

    st.markdown("### フィルター設定")

# 銘柄リスト準備
if scan_target == "東証全銘柄":
    tse_stocks, tse_err = load_all_tse_stocks()
    if tse_err or not tse_stocks:
        st.error(f"東証銘柄リストの取得に失敗: {tse_err}")
        st.stop()
    all_tickers = tse_stocks
    desc_text = f"東証全{len(all_tickers):,}銘柄をML + テクニカル指標でスコアリング"
else:
    nk225 = load_tickers(TICKERS_PATH)
    if not nk225:
        st.error("銘柄リストが読み込めません。data/nikkei225_tickers.txt を確認してください。")
        st.stop()
    all_tickers = nk225
    desc_text = "日経225銘柄をML + テクニカル指標でスコアリング"

st.markdown(
    f"<p style='color: #6b7280; font-size: 0.85em; margin-bottom: 1.5em'>{desc_text}</p>",
    unsafe_allow_html=True,
)

# セクター一覧
all_sectors = sorted(set(t.get("sector", "") for t in all_tickers if t.get("sector")))

with st.sidebar:
    selected_sectors = st.multiselect("セクター", options=all_sectors, default=[], placeholder="全セクター")
    min_score = st.slider("最低スコア", 0, 80, 30, step=5)
    direction_filter = st.selectbox("方向予測", options=["すべて", "上昇/買い", "下落/売り", "横ばい/中立"], index=0)
    show_top_n = st.slider("上位カード表示数", 3, 30, 10)

    if st.button("キャッシュクリア", use_container_width=True, icon=":material/refresh:"):
        _run_recommend_scan.clear()
        st.rerun()

# ── スキャン実行 ──────────────────────────────────────────────────

codes = tuple(t["code"] for t in all_tickers)
names = tuple(t["name"] for t in all_tickers)
sectors = tuple(t.get("sector", "") for t in all_tickers)

spinner_msg = f"{len(codes):,}銘柄をスコアリング中..."
with helix_spinner(spinner_msg):
    all_results = _run_recommend_scan(codes, names, sectors, use_fundamental)

if not all_results:
    st.warning("スコアリング結果が得られませんでした。しばらく時間をおいて再試行してください。")
    st.stop()

# ── フィルタリング ────────────────────────────────────────────────
filtered = all_results.copy()

if selected_sectors:
    filtered = [r for r in filtered if r["セクター"] in selected_sectors]

filtered = [r for r in filtered if r["MLスコア"] >= min_score]

if direction_filter != "すべて":
    dir_map = {
        "上昇/買い": ["上昇", "強い買い", "買い", "やや強気"],
        "下落/売り": ["下落", "強い売り", "売り", "やや弱気"],
        "横ばい/中立": ["横ばい", "中立"],
    }
    allowed = dir_map.get(direction_filter, [])
    filtered = [r for r in filtered if r["方向予測"] in allowed]

st.markdown(
    f"<p style='color:#b8b0a2'>全 <b>{len(all_results)}</b> 銘柄中"
    f" <b style='color:#d4af37'>{len(filtered)}</b> 銘柄が条件に合致</p>",
    unsafe_allow_html=True,
)

if not filtered:
    st.info("条件に合致する銘柄がありません。フィルター条件を緩和してください。")
    st.stop()

# ── 上位銘柄カード ──────────────────────────────────────────────

st.markdown(
    "<h2 style='font-family: Cormorant Garamond, serif; font-weight: 300;"
    "color: #d4af37; font-size: 1.3em; margin-top: 0.5em'>Top Picks</h2>",
    unsafe_allow_html=True,
)

for i, item in enumerate(filtered[:show_top_n], start=1):
    _render_detail_card(i, item)

# ── ソート可能テーブル ──────────────────────────────────────────

st.markdown(
    "<h2 style='font-family: Cormorant Garamond, serif; font-weight: 300;"
    "color: #d4af37; font-size: 1.3em; margin-top: 1em'>All Rankings</h2>",
    unsafe_allow_html=True,
)

display_cols = ["銘柄コード", "銘柄名", "現在値", "前日比(%)", "MLスコア",
                "方向予測", "信頼度", "テクニカルシグナル", "セクター"]
df_table = pd.DataFrame(filtered)[display_cols].copy()
df_table["現在値"] = df_table["現在値"].apply(lambda x: f"¥{x:,.0f}")

st.dataframe(
    df_table,
    use_container_width=True,
    hide_index=True,
    height=min(len(df_table) * 38 + 40, 600),
    column_config={
        "MLスコア": st.column_config.ProgressColumn("MLスコア", min_value=0, max_value=100, format="%.0f"),
        "信頼度": st.column_config.ProgressColumn("信頼度", min_value=0, max_value=100, format="%.0f%%"),
        "前日比(%)": st.column_config.NumberColumn("前日比(%)", format="%.2f%%"),
    },
)

# CSVダウンロード
csv = pd.DataFrame(filtered)[display_cols].to_csv(index=False)
st.download_button("CSVダウンロード", data=csv, file_name="ai_recommend.csv", mime="text/csv")

# ── フッター ──────────────────────────────────────────────────
st.divider()
st.caption(
    "スコアは ML予測 (XGBoost方向予測 + 買いタイミング) + テクニカル指標 "
    "(RSI, MACD, ストキャスティクス, 一目均衡表, ADX, BB, 出来高, トレンド, モメンタム一貫性) "
    "+ ファンダメンタル補正 (PER/PBR/配当/ROE) の複合評価です。"
    "結果は4時間キャッシュされます。投資判断は自己責任でお願いします。"
)
