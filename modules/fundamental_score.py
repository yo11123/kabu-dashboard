"""
ファンダメンタル分析スコアリングモジュール

日本株を7カテゴリ・0-100スケールで定量評価する。
yfinance と Kabutan のデータを統合し、欠損データがあっても
ウェイトを再配分して堅牢にスコアを算出する。

UIコードは含まない（純粋な計算モジュール）。
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# データクラス定義
# ═══════════════════════════════════════════════════════════════════════════════

@dataclasses.dataclass
class CategoryScore:
    """カテゴリ別スコア"""
    name: str                     # カテゴリ名（日本語）
    score: float                  # 0-100 スコア
    weight: float                 # 配分ウェイト（再正規化後）
    weighted: float               # score * weight
    details: dict[str, str]       # 指標名 → "値 → スコア" の説明
    available: int                # 取得できた指標数
    total: int                    # 試行した指標数


@dataclasses.dataclass
class FundamentalScore:
    """総合ファンダメンタルスコア"""
    total_score: float            # 加重合計 0-100
    categories: list[CategoryScore]
    data_coverage: float          # データ取得率 0.0-1.0
    grade: str                    # A+, A, B+, B, C, D
    summary: str                  # 1行サマリー（日本語）
    raw_metrics: dict[str, float | None]  # 生の指標値


# ═══════════════════════════════════════════════════════════════════════════════
# スコアリングユーティリティ
# ═══════════════════════════════════════════════════════════════════════════════

def _safe(val: Any) -> float | None:
    """値を float に変換。None / NaN / 非数値は None を返す。"""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _threshold_score(value: float, thresholds: list[tuple[float, float]]) -> float:
    """
    閾値テーブルからスコアを算出する。

    thresholds は (上限値, スコア) のリスト（昇順）。
    最後の要素が上限なし（それ以上の値）のスコアとなる。

    例: [(8, 100), (12, 80), (16, 60), (25, 40), (40, 20)]
        → value<8 → 100, 8<=value<12 → 80, ..., value>=40 → thresholds末尾のスコア
    """
    for limit, score in thresholds:
        if value < limit:
            return score
    # 最後の閾値を超えた場合
    return thresholds[-1][1]


def _threshold_score_desc(value: float, thresholds: list[tuple[float, float]],
                          default_low: float = 0.0) -> float:
    """
    降順閾値テーブル（値が大きいほど高スコア）。

    thresholds は (下限値, スコア) のリスト（降順）。
    value >= 下限値 なら対応するスコアを返す。

    例: [(20, 100), (15, 85), (10, 70), (5, 45)]
        → value>=20 → 100, 15<=value<20 → 85, ...
    """
    for limit, score in thresholds:
        if value >= limit:
            return score
    return default_low


def _lerp_score(value: float, low: float, high: float,
                score_at_low: float, score_at_high: float) -> float:
    """
    2点間の線形補間でスコアを算出する。
    value が low〜high の範囲外ならクランプする。
    """
    if high == low:
        return (score_at_low + score_at_high) / 2
    t = (value - low) / (high - low)
    t = max(0.0, min(1.0, t))
    return score_at_low + t * (score_at_high - score_at_low)


def _growth_rate(newer: float | None, older: float | None) -> float | None:
    """成長率を計算する。ゼロ除算や欠損は None。"""
    if newer is None or older is None:
        return None
    if older == 0:
        return None
    return (newer - older) / abs(older)


def _cagr(start: float | None, end: float | None, years: int) -> float | None:
    """CAGR（年平均成長率）を計算する。"""
    if start is None or end is None or years <= 0:
        return None
    if start <= 0 or end <= 0:
        return None
    try:
        return (end / start) ** (1.0 / years) - 1.0
    except (ValueError, ZeroDivisionError):
        return None


def _weighted_avg(scores: list[tuple[float, float]]) -> float:
    """(スコア, ウェイト) リストの加重平均を計算する。"""
    total_w = sum(w for _, w in scores)
    if total_w <= 0:
        return 0.0
    return sum(s * w for s, w in scores) / total_w


# ═══════════════════════════════════════════════════════════════════════════════
# カテゴリ別スコアリング関数
# ═══════════════════════════════════════════════════════════════════════════════

def _score_valuation(yf_info: dict, kb_data: dict) -> CategoryScore:
    """
    割安度スコア (Valuation)

    PER, PBR, Forward/Trailing PER 比, PSR の4指標で評価する。
    PER が低いほど割安、PBR が低いほど資産価値に対して割安。
    """
    scores: list[tuple[float, float]] = []  # (スコア, ウェイト)
    details: dict[str, str] = {}
    total = 4
    available = 0

    # --- PER (35%) ---
    per = _safe(yf_info.get("trailingPE")) or _safe(kb_data.get("per"))
    if per is not None and per > 0:
        s = _threshold_score(per, [
            (8, 100), (12, 80), (16, 60), (25, 40), (40, 20),
        ])
        # 最後の閾値(40)を超えた場合は 0
        if per >= 40:
            s = 0.0
        scores.append((s, 0.35))
        details["PER"] = f"{per:.1f}倍 → {s:.0f}点"
        available += 1

    # --- PBR (30%) ---
    pbr = _safe(yf_info.get("priceToBook")) or _safe(kb_data.get("pbr"))
    if pbr is not None and pbr > 0:
        s = _threshold_score(pbr, [
            (0.5, 100), (0.8, 85), (1.0, 70), (1.5, 50), (3.0, 30),
        ])
        if pbr >= 3.0:
            s = 10.0
        scores.append((s, 0.30))
        details["PBR"] = f"{pbr:.2f}倍 → {s:.0f}点"
        available += 1

    # --- Forward/Trailing PER 比 (15%) ---
    forward_pe = _safe(yf_info.get("forwardPE"))
    trailing_pe = _safe(yf_info.get("trailingPE")) or _safe(kb_data.get("per"))
    if forward_pe is not None and trailing_pe is not None and trailing_pe > 0:
        # Forward PER < Trailing PER → 利益成長が見込まれる → 高評価
        s = 80.0 if forward_pe < trailing_pe else 30.0
        ratio = forward_pe / trailing_pe
        scores.append((s, 0.15))
        details["Forward/Trailing PER"] = f"{ratio:.2f} → {s:.0f}点"
        available += 1

    # --- PSR (20%) ---
    market_cap = _safe(yf_info.get("marketCap")) or _safe(kb_data.get("market_cap"))
    # Kabutan の売上高は百万円単位（financials[0].sales_m）
    kb_fins = kb_data.get("financials", [])
    sales = None
    if kb_fins and kb_fins[0].get("sales_m") is not None:
        sales = _safe(kb_fins[0]["sales_m"])
        if sales is not None:
            sales *= 1e6  # 百万円 → 円
    if market_cap and sales and sales > 0:
        psr = market_cap / sales
        s = _threshold_score(psr, [
            (0.5, 100), (1.0, 80), (2.0, 60), (5.0, 30),
        ])
        if psr >= 5.0:
            s = 10.0
        scores.append((s, 0.20))
        details["PSR"] = f"{psr:.2f} → {s:.0f}点"
        available += 1

    score = _weighted_avg(scores) if scores else 0.0

    return CategoryScore(
        name="割安度",
        score=round(score, 1),
        weight=0.20,
        weighted=0.0,  # 後で再計算
        details=details,
        available=available,
        total=total,
    )


def _score_growth(yf_info: dict, kb_data: dict) -> CategoryScore:
    """
    成長性スコア (Growth)

    売上成長率、営業利益成長率、EPS CAGR、Forward EPS 成長率の4指標。
    """
    scores: list[tuple[float, float]] = []
    details: dict[str, str] = {}
    total = 4
    available = 0
    kb_fins = kb_data.get("financials", [])

    # --- 売上成長率 YoY (30%) ---
    rev_growth = _safe(yf_info.get("revenueGrowth"))
    # yfinance の revenueGrowth は小数（0.10 = 10%）
    if rev_growth is not None:
        pct = rev_growth * 100
        s = _threshold_score_desc(pct, [
            (20, 100), (10, 80), (5, 60), (0, 40),
        ], default_low=10.0)
        scores.append((s, 0.30))
        details["売上成長率YoY"] = f"{pct:+.1f}% → {s:.0f}点"
        available += 1

    # --- 営業利益成長率 YoY (30%) ---
    if len(kb_fins) >= 2:
        op_new = _safe(kb_fins[0].get("op_profit_m"))
        op_old = _safe(kb_fins[1].get("op_profit_m"))
        gr = _growth_rate(op_new, op_old)
        if gr is not None:
            pct = gr * 100
            s = _threshold_score_desc(pct, [
                (20, 100), (10, 80), (5, 60), (0, 40),
            ], default_low=10.0)
            scores.append((s, 0.30))
            details["営業利益成長率YoY"] = f"{pct:+.1f}% → {s:.0f}点"
            available += 1

    # --- EPS CAGR 3年 (25%) ---
    if len(kb_fins) >= 3:
        eps_newest = _safe(kb_fins[0].get("eps"))
        eps_oldest = _safe(kb_fins[-1].get("eps"))
        years = len(kb_fins) - 1
        cagr = _cagr(eps_oldest, eps_newest, years)
        if cagr is not None:
            pct = cagr * 100
            s = _threshold_score_desc(pct, [
                (20, 100), (10, 80), (5, 60), (0, 40),
            ], default_low=10.0)
            scores.append((s, 0.25))
            details["EPS CAGR"] = f"{pct:+.1f}%/年 ({years}年) → {s:.0f}点"
            available += 1

    # --- Forward EPS 成長率 (15%) ---
    forward_eps = _safe(yf_info.get("forwardEps"))
    trailing_eps = _safe(yf_info.get("trailingEps"))
    if forward_eps is not None and trailing_eps is not None and trailing_eps > 0:
        gr = (forward_eps / trailing_eps - 1.0) * 100
        s = _threshold_score_desc(gr, [
            (20, 100), (10, 80), (5, 60), (0, 40),
        ], default_low=10.0)
        scores.append((s, 0.15))
        details["Forward EPS成長率"] = f"{gr:+.1f}% → {s:.0f}点"
        available += 1

    score = _weighted_avg(scores) if scores else 0.0

    return CategoryScore(
        name="成長性",
        score=round(score, 1),
        weight=0.18,
        weighted=0.0,
        details=details,
        available=available,
        total=total,
    )


def _score_profitability(yf_info: dict, kb_data: dict) -> CategoryScore:
    """
    収益性スコア (Profitability)

    ROE, 営業利益率, ROA, 純利益率, ROIC近似 の5指標。
    """
    scores: list[tuple[float, float]] = []
    details: dict[str, str] = {}
    total = 5
    available = 0
    kb_fins = kb_data.get("financials", [])

    # --- ROE (30%) ---
    roe = _safe(yf_info.get("returnOnEquity"))
    if roe is not None:
        pct = roe * 100  # yfinance は小数 (0.15 = 15%)
        s = _threshold_score_desc(pct, [
            (20, 100), (15, 85), (10, 70), (5, 45),
        ], default_low=20.0)
        scores.append((s, 0.30))
        details["ROE"] = f"{pct:.1f}% → {s:.0f}点"
        available += 1

    # --- 営業利益率 (25%) ---
    op_margin = _safe(yf_info.get("operatingMargins"))
    if op_margin is not None:
        pct = op_margin * 100
        s = _threshold_score_desc(pct, [
            (20, 100), (15, 80), (10, 65), (5, 45),
        ], default_low=25.0)
        scores.append((s, 0.25))
        details["営業利益率"] = f"{pct:.1f}% → {s:.0f}点"
        available += 1

    # --- ROA (20%) ---
    roa = _safe(yf_info.get("returnOnAssets"))
    if roa is not None:
        pct = roa * 100
        s = _threshold_score_desc(pct, [
            (10, 100), (7, 80), (5, 65), (3, 45),
        ], default_low=20.0)
        scores.append((s, 0.20))
        details["ROA"] = f"{pct:.1f}% → {s:.0f}点"
        available += 1

    # --- 純利益率（Kabutan: net_profit / sales）(15%) ---
    if kb_fins:
        net = _safe(kb_fins[0].get("net_profit_m"))
        sales = _safe(kb_fins[0].get("sales_m"))
        if net is not None and sales is not None and sales > 0:
            margin_pct = (net / sales) * 100
            s = _threshold_score_desc(margin_pct, [
                (15, 100), (10, 80), (5, 60), (2, 40),
            ], default_low=20.0)
            scores.append((s, 0.15))
            details["純利益率"] = f"{margin_pct:.1f}% → {s:.0f}点"
            available += 1

    # --- ROIC 近似 (10%) ---
    # ROIC ≈ NOPAT / (総資産 - 現金) → 簡易的に op_profit*(1-0.3) / marketCap で近似
    # 正確ではないが、利用可能なデータで最善の近似
    market_cap = _safe(yf_info.get("marketCap")) or _safe(kb_data.get("market_cap"))
    if kb_fins and market_cap and market_cap > 0:
        op = _safe(kb_fins[0].get("op_profit_m"))
        if op is not None:
            # 税率30%想定、百万円→円変換
            nopat = op * 1e6 * 0.7
            roic_pct = (nopat / market_cap) * 100
            s = _threshold_score_desc(roic_pct, [
                (10, 100), (7, 80), (5, 65), (3, 45),
            ], default_low=20.0)
            scores.append((s, 0.10))
            details["ROIC近似"] = f"{roic_pct:.1f}% → {s:.0f}点"
            available += 1

    score = _weighted_avg(scores) if scores else 0.0

    return CategoryScore(
        name="収益性",
        score=round(score, 1),
        weight=0.18,
        weighted=0.0,
        details=details,
        available=available,
        total=total,
    )


def _score_financial_health(yf_info: dict, kb_data: dict) -> CategoryScore:
    """
    財務健全性スコア (Financial Health)

    FCF利回り, FCF正負, 利益の質, 配当安定性 の4指標。
    """
    scores: list[tuple[float, float]] = []
    details: dict[str, str] = {}
    total = 4
    available = 0
    kb_fins = kb_data.get("financials", [])

    fcf = _safe(yf_info.get("freeCashflow"))
    market_cap = _safe(yf_info.get("marketCap")) or _safe(kb_data.get("market_cap"))

    # --- FCF利回り (40%) ---
    if fcf is not None and market_cap and market_cap > 0:
        fcf_yield = (fcf / market_cap) * 100
        if fcf_yield < 0:
            s = 15.0
        else:
            s = _threshold_score_desc(fcf_yield, [
                (8, 100), (5, 80), (3, 60), (0, 40),
            ], default_low=15.0)
        scores.append((s, 0.40))
        details["FCF利回り"] = f"{fcf_yield:.1f}% → {s:.0f}点"
        available += 1

    # --- FCF正負 (15%) ---
    if fcf is not None:
        s = 70.0 if fcf > 0 else 20.0
        scores.append((s, 0.15))
        label = "プラス" if fcf > 0 else "マイナス"
        details["FCF正負"] = f"{label} → {s:.0f}点"
        available += 1

    # --- 利益の質: 純利益/営業利益 比率 (25%) ---
    if kb_fins:
        net = _safe(kb_fins[0].get("net_profit_m"))
        op = _safe(kb_fins[0].get("op_profit_m"))
        if net is not None and op is not None and op != 0:
            ratio = net / op
            # 0.6-0.9 が健全（税金・特損控除後の適正範囲）
            if 0.6 <= ratio <= 0.9:
                s = 80.0
            elif 0.4 <= ratio < 0.6:
                s = 60.0
            elif 0.9 < ratio <= 1.1:
                s = 65.0  # 特益で嵩上げの可能性
            elif ratio > 1.1:
                s = 40.0  # 特別利益に依存
            else:
                s = 30.0  # 低すぎる（特損・税負担大）
            scores.append((s, 0.25))
            details["利益の質"] = f"純利益/営業利益 = {ratio:.2f} → {s:.0f}点"
            available += 1

    # --- 配当安定性（Kabutan 財務データの DPS 推移）(20%) ---
    if len(kb_fins) >= 2:
        dps_list = [_safe(f.get("dps")) for f in kb_fins]
        dps_valid = [d for d in dps_list if d is not None]
        if len(dps_valid) >= 2:
            # 減配回数をカウント（新しい方から古い方へ）
            decreases = 0
            for i in range(len(dps_valid) - 1):
                # dps_valid[0] が最新、dps_valid[-1] が最古
                if dps_valid[i] < dps_valid[i + 1]:
                    decreases += 1
            # 全期間増配 or 維持 → 高評価
            if decreases == 0:
                s = 90.0
            elif decreases == 1:
                s = 60.0
            else:
                s = 30.0
            # 無配の場合
            if all(d == 0 for d in dps_valid):
                s = 20.0
            scores.append((s, 0.20))
            details["配当安定性"] = f"減配{decreases}回/{len(dps_valid)-1}期 → {s:.0f}点"
            available += 1

    score = _weighted_avg(scores) if scores else 0.0

    return CategoryScore(
        name="財務健全性",
        score=round(score, 1),
        weight=0.15,
        weighted=0.0,
        details=details,
        available=available,
        total=total,
    )


def _score_shareholder_return(yf_info: dict, kb_data: dict) -> CategoryScore:
    """
    株主還元スコア (Shareholder Return)

    配当利回り, 配当性向, 配当成長CAGR, トータルリターン の4指標。
    """
    scores: list[tuple[float, float]] = []
    details: dict[str, str] = {}
    total = 4
    available = 0
    kb_fins = kb_data.get("financials", [])

    # --- 配当利回り (35%) ---
    # Kabutan: %値、yfinance: 小数
    div_yield = _safe(kb_data.get("dividend_yield"))
    if div_yield is None:
        yf_dy = _safe(yf_info.get("dividendYield"))
        if yf_dy is not None:
            div_yield = yf_dy * 100  # 小数 → %
    if div_yield is not None:
        s = _threshold_score_desc(div_yield, [
            (5.0, 100), (4.0, 90), (3.0, 75), (2.0, 55), (1.0, 35),
        ], default_low=15.0)
        scores.append((s, 0.35))
        details["配当利回り"] = f"{div_yield:.2f}% → {s:.0f}点"
        available += 1

    # --- 配当性向 (20%) ---
    if kb_fins:
        dps = _safe(kb_fins[0].get("dps"))
        eps = _safe(kb_fins[0].get("eps"))
        if dps is not None and eps is not None and eps > 0:
            payout = (dps / eps) * 100
            # 30-50% が理想的
            if 30 <= payout <= 50:
                s = 100.0
            elif 20 <= payout < 30:
                s = 75.0
            elif 50 < payout <= 70:
                s = 70.0
            elif 10 <= payout < 20:
                s = 50.0
            elif 70 < payout <= 100:
                s = 40.0
            elif payout > 100:
                s = 15.0  # 配当が利益を超えている（持続不可能）
            else:
                s = 25.0  # 10%未満
            scores.append((s, 0.20))
            details["配当性向"] = f"{payout:.1f}% → {s:.0f}点"
            available += 1

    # --- 配当成長 CAGR (25%) ---
    if len(kb_fins) >= 2:
        dps_newest = _safe(kb_fins[0].get("dps"))
        dps_oldest = _safe(kb_fins[-1].get("dps"))
        years = len(kb_fins) - 1
        dps_cagr = _cagr(dps_oldest, dps_newest, years)
        if dps_cagr is not None:
            pct = dps_cagr * 100
            s = _threshold_score_desc(pct, [
                (15, 100), (10, 85), (5, 70), (0, 45),
            ], default_low=20.0)
            scores.append((s, 0.25))
            details["配当成長CAGR"] = f"{pct:+.1f}%/年 → {s:.0f}点"
            available += 1

    # --- トータルリターン（配当利回り + 益回り）(20%) ---
    per = _safe(yf_info.get("trailingPE")) or _safe(kb_data.get("per"))
    if div_yield is not None and per is not None and per > 0:
        earnings_yield = 100.0 / per  # 益回り（%）
        total_return = div_yield + earnings_yield
        s = _threshold_score_desc(total_return, [
            (15, 100), (10, 80), (7, 65), (5, 50), (3, 35),
        ], default_low=20.0)
        scores.append((s, 0.20))
        details["トータルリターン"] = f"{total_return:.1f}%（配当{div_yield:.1f}%+益回り{earnings_yield:.1f}%） → {s:.0f}点"
        available += 1

    score = _weighted_avg(scores) if scores else 0.0

    return CategoryScore(
        name="株主還元",
        score=round(score, 1),
        weight=0.12,
        weighted=0.0,
        details=details,
        available=available,
        total=total,
    )


def _score_sector_relative(
    yf_info: dict,
    kb_data: dict,
    sector_avgs: dict | None,
) -> CategoryScore:
    """
    セクター相対スコア (Sector-Relative)

    PER, ROE, 利益率, 配当利回り をセクター平均と比較する。
    sector_avgs が None の場合は全指標スキップ。
    """
    scores: list[tuple[float, float]] = []
    details: dict[str, str] = {}
    total = 4
    available = 0

    if not sector_avgs:
        return CategoryScore(
            name="セクター相対",
            score=0.0,
            weight=0.10,
            weighted=0.0,
            details={"注記": "セクター平均データなし"},
            available=0,
            total=total,
        )

    # --- PER vs セクター中央値 (25%) ---
    per = _safe(yf_info.get("trailingPE")) or _safe(kb_data.get("per"))
    sec_per = _safe(sector_avgs.get("per"))
    if per is not None and sec_per is not None and sec_per > 0:
        ratio = per / sec_per
        # 割安（低PER）が良い → ratio < 1 が高評価
        if ratio < 0.7:
            s = 100.0
        elif ratio < 0.85:
            s = 80.0
        elif ratio < 1.0:
            s = 65.0
        elif ratio < 1.2:
            s = 45.0
        else:
            s = 25.0
        scores.append((s, 0.25))
        details["PER vs セクター"] = f"{per:.1f} / 平均{sec_per:.1f} = {ratio:.2f} → {s:.0f}点"
        available += 1

    # --- ROE vs セクター中央値 (25%) ---
    roe = _safe(yf_info.get("returnOnEquity"))
    sec_roe = _safe(sector_avgs.get("roe"))
    if roe is not None and sec_roe is not None and sec_roe > 0:
        roe_pct = roe * 100
        sec_roe_pct = sec_roe if sec_roe > 1 else sec_roe * 100  # %値に統一
        ratio = roe_pct / sec_roe_pct if sec_roe_pct > 0 else 1.0
        # 高ROEが良い → ratio > 1 が高評価
        if ratio > 1.5:
            s = 100.0
        elif ratio > 1.2:
            s = 80.0
        elif ratio > 1.0:
            s = 65.0
        elif ratio > 0.8:
            s = 45.0
        else:
            s = 25.0
        scores.append((s, 0.25))
        details["ROE vs セクター"] = f"{roe_pct:.1f}% / 平均{sec_roe_pct:.1f}% = {ratio:.2f} → {s:.0f}点"
        available += 1

    # --- 利益率 vs セクター中央値 (25%) ---
    margin = _safe(yf_info.get("operatingMargins"))
    sec_margin = _safe(sector_avgs.get("operating_margin"))
    if margin is not None and sec_margin is not None and sec_margin > 0:
        margin_pct = margin * 100
        sec_margin_pct = sec_margin if sec_margin > 1 else sec_margin * 100
        ratio = margin_pct / sec_margin_pct if sec_margin_pct > 0 else 1.0
        if ratio > 1.5:
            s = 100.0
        elif ratio > 1.2:
            s = 80.0
        elif ratio > 1.0:
            s = 65.0
        elif ratio > 0.8:
            s = 45.0
        else:
            s = 25.0
        scores.append((s, 0.25))
        details["利益率 vs セクター"] = f"{margin_pct:.1f}% / 平均{sec_margin_pct:.1f}% = {ratio:.2f} → {s:.0f}点"
        available += 1

    # --- 配当利回り vs セクター中央値 (25%) ---
    div_yield = _safe(kb_data.get("dividend_yield"))
    if div_yield is None:
        yf_dy = _safe(yf_info.get("dividendYield"))
        if yf_dy is not None:
            div_yield = yf_dy * 100
    sec_div = _safe(sector_avgs.get("dividend_yield"))
    if div_yield is not None and sec_div is not None and sec_div > 0:
        sec_div_pct = sec_div if sec_div > 1 else sec_div * 100
        ratio = div_yield / sec_div_pct if sec_div_pct > 0 else 1.0
        if ratio > 1.5:
            s = 100.0
        elif ratio > 1.2:
            s = 80.0
        elif ratio > 1.0:
            s = 65.0
        elif ratio > 0.8:
            s = 45.0
        else:
            s = 25.0
        scores.append((s, 0.25))
        details["配当利回り vs セクター"] = f"{div_yield:.2f}% / 平均{sec_div_pct:.2f}% = {ratio:.2f} → {s:.0f}点"
        available += 1

    score = _weighted_avg(scores) if scores else 0.0

    return CategoryScore(
        name="セクター相対",
        score=round(score, 1),
        weight=0.10,
        weighted=0.0,
        details=details,
        available=available,
        total=total,
    )


def _score_macro_sensitivity(
    yf_info: dict,
    commodity_bonus: float,
    beta: float | None,
) -> CategoryScore:
    """
    マクロ感応度スコア (Macro Sensitivity)

    コモディティ/為替の追い風スコア と ベータリスク の2指標。
    """
    scores: list[tuple[float, float]] = []
    details: dict[str, str] = {}
    total = 2
    available = 0

    # --- コモディティ/為替追い風スコア (70%) ---
    # commodity_bonus は -10〜+10 の範囲を想定
    # 線形補間で 0〜100 にマッピング
    cb = max(-10.0, min(10.0, commodity_bonus))
    s = _lerp_score(cb, -10.0, 10.0, 0.0, 100.0)
    scores.append((s, 0.70))
    details["コモディティ/為替"] = f"ボーナス {commodity_bonus:+.1f} → {s:.0f}点"
    available += 1

    # --- ベータリスク (30%) ---
    beta_val = _safe(beta) or _safe(yf_info.get("beta"))
    if beta_val is not None:
        # 低ベータ（ディフェンシブ）ほど高スコア
        if beta_val < 0.5:
            s = 95.0
        elif beta_val < 0.8:
            s = 90.0
        elif beta_val <= 1.2:
            s = 70.0
        elif beta_val <= 1.5:
            s = 45.0
        else:
            s = 30.0
        scores.append((s, 0.30))
        details["ベータ"] = f"{beta_val:.2f} → {s:.0f}点"
        available += 1

    score = _weighted_avg(scores) if scores else 0.0

    return CategoryScore(
        name="マクロ感応度",
        score=round(score, 1),
        weight=0.07,
        weighted=0.0,
        details=details,
        available=available,
        total=total,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# グレード判定
# ═══════════════════════════════════════════════════════════════════════════════

def _assign_grade(score: float) -> str:
    """スコアからグレードを割り当てる。"""
    if score >= 85:
        return "A+"
    if score >= 75:
        return "A"
    if score >= 65:
        return "B+"
    if score >= 55:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def _generate_summary(
    total_score: float,
    grade: str,
    categories: list[CategoryScore],
    data_coverage: float,
) -> str:
    """スコアに基づく1行サマリーを日本語で生成する。"""
    # 最高・最低カテゴリを特定（available > 0 のもの）
    active = [c for c in categories if c.available > 0]
    if not active:
        return "データ不足のため評価不能"

    best = max(active, key=lambda c: c.score)
    worst = min(active, key=lambda c: c.score)

    grade_desc = {
        "A+": "非常に優秀",
        "A": "優秀",
        "B+": "良好",
        "B": "平均以上",
        "C": "平均的",
        "D": "要注意",
    }

    desc = grade_desc.get(grade, "")
    coverage_pct = data_coverage * 100

    return (
        f"総合{grade}（{desc}）: {best.name}が強み（{best.score:.0f}点）、"
        f"{worst.name}が課題（{worst.score:.0f}点）。"
        f"データカバー率 {coverage_pct:.0f}%"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# メインエントリポイント
# ═══════════════════════════════════════════════════════════════════════════════

def _collect_raw_metrics(yf_info: dict, kb_data: dict) -> dict[str, float | None]:
    """生の指標値を辞書にまとめる（デバッグ・表示用）。"""
    kb_fins = kb_data.get("financials", [])

    metrics: dict[str, float | None] = {
        "PER": _safe(yf_info.get("trailingPE")) or _safe(kb_data.get("per")),
        "PBR": _safe(yf_info.get("priceToBook")) or _safe(kb_data.get("pbr")),
        "Forward PER": _safe(yf_info.get("forwardPE")),
        "ROE": _safe(yf_info.get("returnOnEquity")),
        "ROA": _safe(yf_info.get("returnOnAssets")),
        "営業利益率": _safe(yf_info.get("operatingMargins")),
        "配当利回り": _safe(kb_data.get("dividend_yield")) or (
            (_safe(yf_info.get("dividendYield")) or 0) * 100 or None
        ),
        "時価総額": _safe(yf_info.get("marketCap")) or _safe(kb_data.get("market_cap")),
        "FCF": _safe(yf_info.get("freeCashflow")),
        "売上成長率": _safe(yf_info.get("revenueGrowth")),
        "ベータ": _safe(yf_info.get("beta")),
        "EPS（実績）": _safe(yf_info.get("trailingEps")),
        "EPS（予想）": _safe(yf_info.get("forwardEps")),
    }

    # Kabutan 財務データ（直近期）
    if kb_fins:
        f0 = kb_fins[0]
        metrics["売上高(百万円)"] = _safe(f0.get("sales_m"))
        metrics["営業利益(百万円)"] = _safe(f0.get("op_profit_m"))
        metrics["純利益(百万円)"] = _safe(f0.get("net_profit_m"))
        metrics["EPS(Kabutan)"] = _safe(f0.get("eps"))
        metrics["DPS(Kabutan)"] = _safe(f0.get("dps"))

    return metrics


def calc_fundamental_score(
    yf_info: dict | None = None,
    kb_data: dict | None = None,
    sector_avgs: dict | None = None,
    commodity_bonus: float = 0.0,
    sector: str = "",
) -> FundamentalScore:
    """
    ファンダメンタルスコアを総合算出する。

    Parameters
    ----------
    yf_info : dict | None
        yfinance の .info 辞書（trailingPE, forwardPE, priceToBook, etc.）
    kb_data : dict | None
        fetch_fundamental_kabutan() の返り値（per, pbr, dividend_yield, financials, etc.）
    sector_avgs : dict | None
        セクター平均値の辞書（per, roe, operating_margin, dividend_yield）
    commodity_bonus : float
        コモディティ/為替追い風スコア（-10〜+10）
    sector : str
        セクター名（現在は未使用、将来の拡張用）

    Returns
    -------
    FundamentalScore
        総合スコア・グレード・カテゴリ別詳細を含むデータクラス
    """
    yf_info = yf_info or {}
    kb_data = kb_data or {}

    # 各カテゴリのスコアを算出
    categories = [
        _score_valuation(yf_info, kb_data),
        _score_growth(yf_info, kb_data),
        _score_profitability(yf_info, kb_data),
        _score_financial_health(yf_info, kb_data),
        _score_shareholder_return(yf_info, kb_data),
        _score_sector_relative(yf_info, kb_data, sector_avgs),
        _score_macro_sensitivity(yf_info, commodity_bonus, _safe(yf_info.get("beta"))),
    ]

    # ── ウェイト再配分（欠損カテゴリの除外）──────────────────────────
    # available == 0 のカテゴリはウェイト0にし、残りを比例配分
    active_weight_sum = sum(c.weight for c in categories if c.available > 0)

    if active_weight_sum > 0:
        for c in categories:
            if c.available > 0:
                # 再正規化: 元のウェイトを比例拡大して合計1.0にする
                c.weight = c.weight / active_weight_sum
                c.weighted = round(c.score * c.weight, 2)
            else:
                c.weight = 0.0
                c.weighted = 0.0
    else:
        # 全カテゴリがデータなし
        for c in categories:
            c.weight = 0.0
            c.weighted = 0.0

    # 総合スコア
    total_score = sum(c.weighted for c in categories)
    total_score = round(max(0.0, min(100.0, total_score)), 1)

    # データカバー率
    total_available = sum(c.available for c in categories)
    total_attempted = sum(c.total for c in categories)
    data_coverage = total_available / total_attempted if total_attempted > 0 else 0.0

    # グレード
    grade = _assign_grade(total_score)

    # サマリー
    summary = _generate_summary(total_score, grade, categories, data_coverage)

    # 生の指標値
    raw_metrics = _collect_raw_metrics(yf_info, kb_data)

    return FundamentalScore(
        total_score=total_score,
        categories=categories,
        data_coverage=round(data_coverage, 3),
        grade=grade,
        summary=summary,
        raw_metrics=raw_metrics,
    )
