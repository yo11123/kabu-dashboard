from __future__ import annotations

import math
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import (
    FundamentalsResponse,
    OHLCVPoint,
    OHLCVResponse,
    TechnicalPoint,
    TechnicalResponse,
    TechnicalSummary,
)
from ..services import indicators
from ..services.data_loader import fetch_info, fetch_ohlcv, normalize_symbol

router = APIRouter()


def _safe(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _df_to_ohlcv(df: pd.DataFrame) -> list[OHLCVPoint]:
    points: list[OHLCVPoint] = []
    for ts, row in df.iterrows():
        points.append(
            OHLCVPoint(
                time=ts.strftime("%Y-%m-%d"),
                open=_safe(row.get("Open")) or 0.0,
                high=_safe(row.get("High")) or 0.0,
                low=_safe(row.get("Low")) or 0.0,
                close=_safe(row.get("Close")) or 0.0,
                volume=_safe(row.get("Volume")),
            )
        )
    return points


@router.get("/{symbol}/ohlcv", response_model=OHLCVResponse)
def ohlcv(
    symbol: str,
    period: str = Query("1y"),
    interval: str = Query("1d"),
) -> OHLCVResponse:
    df = fetch_ohlcv(symbol, period=period, interval=interval)  # type: ignore[arg-type]
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    return OHLCVResponse(
        symbol=normalize_symbol(symbol),
        interval=interval,
        period=period,
        points=_df_to_ohlcv(df),
    )


@router.get("/{symbol}/technicals", response_model=TechnicalResponse)
def technicals(symbol: str, period: str = Query("1y")) -> TechnicalResponse:
    df = fetch_ohlcv(symbol, period=period, interval="1d")  # type: ignore[arg-type]
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    close = df["Close"]
    sma20 = indicators.sma(close, 20)
    sma50 = indicators.sma(close, 50)
    sma200 = indicators.sma(close, 200)
    bb = indicators.bollinger(close, 20, 2.0)
    rsi14 = indicators.rsi(close, 14)
    macd = indicators.macd(close)

    series: list[TechnicalPoint] = []
    for ts in df.index:
        series.append(
            TechnicalPoint(
                time=ts.strftime("%Y-%m-%d"),
                sma20=_safe(sma20.get(ts)),
                sma50=_safe(sma50.get(ts)),
                sma200=_safe(sma200.get(ts)),
                bb_upper=_safe(bb["upper"].get(ts)),
                bb_middle=_safe(bb["middle"].get(ts)),
                bb_lower=_safe(bb["lower"].get(ts)),
                rsi14=_safe(rsi14.get(ts)),
                macd=_safe(macd["macd"].get(ts)),
                macd_signal=_safe(macd["signal"].get(ts)),
                macd_hist=_safe(macd["hist"].get(ts)),
            )
        )

    last_close = _safe(close.iloc[-1])
    last_sma50 = _safe(sma50.iloc[-1])
    last_sma200 = _safe(sma200.iloc[-1])
    last_rsi = _safe(rsi14.iloc[-1])
    last_macd = _safe(macd["macd"].iloc[-1])
    last_signal = _safe(macd["signal"].iloc[-1])
    last_bb_up = _safe(bb["upper"].iloc[-1])
    last_bb_mid = _safe(bb["middle"].iloc[-1])
    last_bb_low = _safe(bb["lower"].iloc[-1])

    if last_close and last_sma50 and last_sma200:
        if last_close > last_sma50 > last_sma200:
            trend = "bullish"
        elif last_close < last_sma50 < last_sma200:
            trend = "bearish"
        else:
            trend = "neutral"
    else:
        trend = "neutral"

    if last_rsi is None:
        rsi_state = "neutral"
    elif last_rsi >= 70:
        rsi_state = "overbought"
    elif last_rsi <= 30:
        rsi_state = "oversold"
    else:
        rsi_state = "neutral"

    if last_macd is not None and last_signal is not None:
        prev_macd = _safe(macd["macd"].iloc[-2]) if len(macd) >= 2 else None
        prev_signal = _safe(macd["signal"].iloc[-2]) if len(macd) >= 2 else None
        if prev_macd is not None and prev_signal is not None:
            if prev_macd < prev_signal and last_macd > last_signal:
                macd_state = "bullish_cross"
            elif prev_macd > prev_signal and last_macd < last_signal:
                macd_state = "bearish_cross"
            else:
                macd_state = "neutral"
        else:
            macd_state = "neutral"
    else:
        macd_state = "neutral"

    if last_close and last_bb_up and last_bb_low and last_bb_mid:
        if last_close >= last_bb_mid + 0.5 * (last_bb_up - last_bb_mid):
            bb_position = "upper"
        elif last_close <= last_bb_mid - 0.5 * (last_bb_mid - last_bb_low):
            bb_position = "lower"
        else:
            bb_position = "middle"
    else:
        bb_position = "middle"

    return TechnicalResponse(
        symbol=normalize_symbol(symbol),
        series=series,
        summary=TechnicalSummary(
            trend=trend,
            rsi_state=rsi_state,
            macd_state=macd_state,
            bb_position=bb_position,
        ),
    )


@router.get("/{symbol}/fundamentals", response_model=FundamentalsResponse)
def fundamentals(symbol: str) -> FundamentalsResponse:
    info = fetch_info(symbol)
    if not info:
        raise HTTPException(status_code=404, detail=f"No info for {symbol}")

    return FundamentalsResponse(
        symbol=normalize_symbol(symbol),
        name=info.get("longName") or info.get("shortName"),
        currency=info.get("currency"),
        market_cap=_safe(info.get("marketCap")),
        pe=_safe(info.get("trailingPE")),
        forward_pe=_safe(info.get("forwardPE")),
        pb=_safe(info.get("priceToBook")),
        roe=_safe(info.get("returnOnEquity")),
        dividend_yield=_safe(info.get("dividendYield")),
        profit_margin=_safe(info.get("profitMargins")),
        revenue_growth=_safe(info.get("revenueGrowth")),
        sector=info.get("sector"),
        industry=info.get("industry"),
        summary=info.get("longBusinessSummary"),
    )
