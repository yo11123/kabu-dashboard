from typing import Literal, Optional

from pydantic import BaseModel


class SymbolHit(BaseModel):
    symbol: str
    name: str
    market: Literal["JP", "US", "OTHER"]


class OHLCVPoint(BaseModel):
    time: str  # ISO date
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


class OHLCVResponse(BaseModel):
    symbol: str
    interval: str
    period: str
    points: list[OHLCVPoint]


class TechnicalPoint(BaseModel):
    time: str
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    rsi14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None


class TechnicalSummary(BaseModel):
    trend: Literal["bullish", "bearish", "neutral"]
    rsi_state: Literal["overbought", "oversold", "neutral"]
    macd_state: Literal["bullish_cross", "bearish_cross", "neutral"]
    bb_position: Literal["upper", "middle", "lower"]


class TechnicalResponse(BaseModel):
    symbol: str
    series: list[TechnicalPoint]
    summary: TechnicalSummary


class FundamentalsResponse(BaseModel):
    symbol: str
    name: Optional[str] = None
    currency: Optional[str] = None
    market_cap: Optional[float] = None
    pe: Optional[float] = None
    forward_pe: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    dividend_yield: Optional[float] = None
    profit_margin: Optional[float] = None
    revenue_growth: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    summary: Optional[str] = None


class AIPromptRequest(BaseModel):
    symbol: str
    language: Literal["ja", "en"] = "ja"
    include_fundamentals: bool = True
    include_technicals: bool = True


class AIPromptResponse(BaseModel):
    symbol: str
    system: str
    user: str
    context: dict
