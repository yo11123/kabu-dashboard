"""
セクターローテーション分析モジュール

東証セクター ETF を使ったセクター別パフォーマンス分析、
資金フロー検出、景気循環フェーズ推定を提供する。
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
import streamlit as st

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. セクター ETF マッピング
# ---------------------------------------------------------------------------

def get_sector_etfs() -> dict[str, str]:
    """TOPIX セクター ETF のティッカーマッピングを返す。"""
    return {
        "電気機器": "1613.T",
        "輸送用機器": "1614.T",
        "情報・通信": "1626.T",
        "銀行": "1615.T",
        "医薬品": "1621.T",
        "機械": "1620.T",
        "化学": "1619.T",
        "食料品": "1617.T",
        "小売": "1630.T",
        "建設": "1618.T",
        "不動産": "1633.T",
        "サービス": "1634.T",
        "鉄鋼": "1623.T",
        "証券・商品先物": "1632.T",
    }


# ---------------------------------------------------------------------------
# 内部ヘルパー
# ---------------------------------------------------------------------------

def _download_one(ticker: str, period: str) -> pd.DataFrame | None:
    """単一ティッカーの価格データを取得する。失敗時は None を返す。"""
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            # MultiIndex columns が返る場合があるのでフラット化
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
    except Exception as e:
        logger.warning("Failed to download %s: %s", ticker, e)
    return None


def _fetch_all_sectors(period: str, max_workers: int = 8) -> dict[str, pd.DataFrame]:
    """全セクター ETF の価格データを並列取得する。"""
    etfs = get_sector_etfs()
    results: dict[str, pd.DataFrame] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_download_one, ticker, period): sector
            for sector, ticker in etfs.items()
        }
        for future in as_completed(futures):
            sector = futures[future]
            try:
                df = future.result()
                if df is not None:
                    results[sector] = df
            except Exception as e:
                logger.warning("Error fetching sector %s: %s", sector, e)

    return results


def _safe_return(series: pd.Series, days: int) -> float | None:
    """直近 *days* 営業日のリターン (%) を計算する。データ不足時は None。"""
    if series is None or len(series) < days + 1:
        return None
    try:
        return float((series.iloc[-1] / series.iloc[-1 - days] - 1) * 100)
    except (ZeroDivisionError, IndexError):
        return None


# ---------------------------------------------------------------------------
# 2. セクターパフォーマンス
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def fetch_sector_performance(period_days: int = 90) -> pd.DataFrame:
    """
    全セクター ETF のリターン・出来高変化率・モメンタムスコアを算出する。

    Returns
    -------
    DataFrame with columns:
        sector, return_1w, return_1m, return_3m, return_6m,
        volume_ratio, momentum_score
    """
    # 6 か月分は取得しておく (period_days は最低限だが 6m リターンも出す)
    data = _fetch_all_sectors(period="9mo", max_workers=8)

    if not data:
        logger.warning("No sector data fetched.")
        return pd.DataFrame(
            columns=[
                "sector", "return_1w", "return_1m", "return_3m",
                "return_6m", "volume_ratio", "momentum_score",
            ]
        )

    rows: list[dict] = []
    for sector, df in data.items():
        close = df["Close"]
        volume = df["Volume"] if "Volume" in df.columns else pd.Series(dtype=float)

        ret_1w = _safe_return(close, 5)
        ret_1m = _safe_return(close, 21)
        ret_3m = _safe_return(close, 63)
        ret_6m = _safe_return(close, 126)

        # 出来高変化率: 直近 5 日平均 / 30 日平均
        vol_ratio = None
        if volume is not None and len(volume) >= 30:
            avg_5 = volume.iloc[-5:].mean()
            avg_30 = volume.iloc[-30:].mean()
            if avg_30 > 0:
                vol_ratio = round(float(avg_5 / avg_30), 3)

        # モメンタムスコア: 短期リターンと中期リターンの加重合計
        momentum = None
        if ret_1w is not None and ret_1m is not None and ret_3m is not None:
            momentum = round(ret_1w * 0.5 + ret_1m * 0.3 + ret_3m * 0.2, 3)

        rows.append(
            {
                "sector": sector,
                "return_1w": round(ret_1w, 3) if ret_1w is not None else None,
                "return_1m": round(ret_1m, 3) if ret_1m is not None else None,
                "return_3m": round(ret_3m, 3) if ret_3m is not None else None,
                "return_6m": round(ret_6m, 3) if ret_6m is not None else None,
                "volume_ratio": vol_ratio,
                "momentum_score": momentum,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. 資金フロー
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def calc_fund_flow(period_days: int = 30) -> pd.DataFrame:
    """
    セクターごとの資金フロー (出来高 x 価格変動) を推計する。

    Returns
    -------
    DataFrame with columns:
        sector, fund_flow, flow_direction ("流入"/"流出"), magnitude
    """
    # period_days + バッファ
    days_needed = period_days + 10
    period_str = f"{days_needed}d"
    data = _fetch_all_sectors(period=period_str, max_workers=8)

    if not data:
        logger.warning("No sector data for fund flow.")
        return pd.DataFrame(
            columns=["sector", "fund_flow", "flow_direction", "magnitude"]
        )

    rows: list[dict] = []
    for sector, df in data.items():
        try:
            df_recent = df.iloc[-period_days:] if len(df) >= period_days else df
            close = df_recent["Close"]
            volume = df_recent["Volume"] if "Volume" in df_recent.columns else None

            if volume is None or close is None or len(close) < 2:
                continue

            # 日次の (出来高 * 価格変動率) を累積合計
            price_change = close.pct_change().fillna(0)
            daily_flow = volume * price_change
            cumulative_flow = float(daily_flow.sum())

            direction = "流入" if cumulative_flow >= 0 else "流出"
            magnitude = abs(cumulative_flow)

            rows.append(
                {
                    "sector": sector,
                    "fund_flow": round(cumulative_flow, 2),
                    "flow_direction": direction,
                    "magnitude": round(magnitude, 2),
                }
            )
        except Exception as e:
            logger.warning("Fund flow calc failed for %s: %s", sector, e)

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("magnitude", ascending=False).reset_index(drop=True)
    return result


# ---------------------------------------------------------------------------
# 4. セクターローテーション検出
# ---------------------------------------------------------------------------

def detect_sector_rotation(perf_df: pd.DataFrame) -> dict:
    """
    モメンタムの加速・減速からセクターローテーションを検出する。

    Parameters
    ----------
    perf_df : fetch_sector_performance() の戻り値

    Returns
    -------
    dict with keys:
        leaders, laggards, emerging, cycle_phase
    """
    result: dict = {
        "leaders": [],
        "laggards": [],
        "emerging": [],
        "cycle_phase": "不明",
    }

    if perf_df.empty:
        return result

    df = perf_df.dropna(subset=["return_1w", "return_1m"]).copy()
    if df.empty:
        return result

    # モメンタム差分: 1w リターン - (1m リターン / 4)
    # 週次ペースに正規化した月次リターンとの差で加速度を測る
    df["accel"] = df["return_1w"] - (df["return_1m"] / 4)

    # リーダー: 1w リターンがプラスかつ加速中
    leaders_mask = (df["return_1w"] > 0) & (df["accel"] > 0)
    result["leaders"] = df.loc[leaders_mask, "sector"].tolist()

    # ラガード: 1w リターンがマイナスかつ減速中
    laggards_mask = (df["return_1w"] < 0) & (df["accel"] < 0)
    result["laggards"] = df.loc[laggards_mask, "sector"].tolist()

    # 新興 (ローテーション先候補):
    # 短期が長期に対して改善 (1w > 0 だが 1m <= 0、または accel が上位)
    if "return_3m" in df.columns:
        emerging_mask = (
            (df["return_1w"] > 0)
            & (df["return_1m"] <= 0)
        )
        # 3m も見れる場合は、3m がマイナスで直近改善しているものも追加
        alt_mask = (
            (df["return_1w"] > 0)
            & (df["return_3m"] < 0)
            & (df["accel"] > 0)
        )
        combined = emerging_mask | alt_mask
        result["emerging"] = df.loc[combined, "sector"].tolist()
    else:
        emerging_mask = (df["return_1w"] > 0) & (df["return_1m"] <= 0)
        result["emerging"] = df.loc[emerging_mask, "sector"].tolist()

    # 景気循環フェーズ推定
    result["cycle_phase"] = _estimate_cycle_phase(result["leaders"])

    return result


def _estimate_cycle_phase(leaders: list[str]) -> str:
    """リーダーセクターから景気循環フェーズを推定する。"""
    cycle_map = get_cycle_sector_map()

    if not leaders:
        return "不明"

    # 各フェーズのリーダーセクターとの重複数をカウント
    scores: dict[str, int] = {}
    for phase, sectors in cycle_map.items():
        overlap = len(set(leaders) & set(sectors))
        scores[phase] = overlap

    max_score = max(scores.values())
    if max_score == 0:
        return "不明"

    # 最もスコアの高いフェーズを返す
    best_phase = max(scores, key=scores.get)  # type: ignore[arg-type]
    return best_phase


# ---------------------------------------------------------------------------
# 5. 景気循環マップ
# ---------------------------------------------------------------------------

def get_cycle_sector_map() -> dict:
    """景気循環フェーズと主導セクターのマッピングを返す。"""
    return {
        "回復期": ["銀行", "不動産", "建設", "証券・商品先物"],
        "拡大期": ["電気機器", "機械", "情報・通信", "輸送用機器"],
        "後退期": ["医薬品", "食料品", "小売"],
        "低迷期": ["電気機器", "化学", "鉄鋼"],
    }


# ---------------------------------------------------------------------------
# 6. 月次セクターリターン
# ---------------------------------------------------------------------------

@st.cache_data(ttl=7200)
def calc_monthly_sector_returns(stocks: list[dict], months: int = 6) -> pd.DataFrame:
    """
    セクター ETF を使って月次リターンを算出する。

    Parameters
    ----------
    stocks : list[dict]
        未使用 (セクター ETF で代替するため)。互換性のために残す。
    months : int
        遡る月数。デフォルト 6。

    Returns
    -------
    DataFrame: index=sector, columns=YYYY-MM, values=return (%)
    """
    period_str = f"{months + 2}mo"
    data = _fetch_all_sectors(period=period_str, max_workers=8)

    if not data:
        logger.warning("No sector data for monthly returns.")
        return pd.DataFrame()

    sector_monthly: dict[str, dict[str, float]] = {}

    for sector, df in data.items():
        try:
            close = df["Close"]
            # 月末リサンプリング
            monthly = close.resample("ME").last().dropna()
            if len(monthly) < 2:
                continue

            returns = monthly.pct_change().dropna() * 100
            # 直近 months 分に絞る
            returns = returns.iloc[-months:]

            month_dict: dict[str, float] = {}
            for dt, val in returns.items():
                key = dt.strftime("%Y-%m")  # type: ignore[union-attr]
                month_dict[key] = round(float(val), 2)

            sector_monthly[sector] = month_dict
        except Exception as e:
            logger.warning("Monthly return calc failed for %s: %s", sector, e)

    if not sector_monthly:
        return pd.DataFrame()

    result = pd.DataFrame.from_dict(sector_monthly, orient="index")
    # 列を時系列順にソート
    result = result.reindex(sorted(result.columns), axis=1)
    result.index.name = "sector"

    return result
