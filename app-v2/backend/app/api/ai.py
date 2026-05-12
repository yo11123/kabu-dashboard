"""AI prompt builder.

Returns the system + user prompt and structured context bundle.
The frontend then calls Anthropic/OpenAI/Gemini directly with the
user's BYOK API key — this backend never sees the key.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models.schemas import AIPromptRequest, AIPromptResponse
from ..services.data_loader import fetch_info, fetch_ohlcv, normalize_symbol
from ..services import indicators

router = APIRouter()


_SYSTEM_JA = (
    "あなたはプロの株式アナリストです。提供された定量データに基づき、"
    "簡潔かつ実用的な投資コメントを日本語で返してください。"
    "結論→根拠→リスクの順で、過度な確信を避け、不確実性も明記してください。"
)
_SYSTEM_EN = (
    "You are a professional equity analyst. Based on the supplied quantitative "
    "data, return a concise actionable comment in English. Use conclusion → "
    "reasoning → risks order, avoid overconfidence, and acknowledge uncertainty."
)


@router.post("/build-prompt", response_model=AIPromptResponse)
def build_prompt(req: AIPromptRequest) -> AIPromptResponse:
    sym = normalize_symbol(req.symbol)

    context: dict = {"symbol": sym}

    if req.include_technicals:
        df = fetch_ohlcv(req.symbol, period="6mo", interval="1d")
        if df is not None and not df.empty:
            close = df["Close"]
            last = float(close.iloc[-1])
            sma50 = indicators.sma(close, 50).iloc[-1]
            sma200 = indicators.sma(close, 200).iloc[-1]
            rsi = indicators.rsi(close, 14).iloc[-1]
            macd_df = indicators.macd(close)
            macd_v = macd_df["macd"].iloc[-1]
            macd_s = macd_df["signal"].iloc[-1]
            context["price"] = round(last, 4)
            context["sma50"] = None if sma50 != sma50 else round(float(sma50), 4)
            context["sma200"] = None if sma200 != sma200 else round(float(sma200), 4)
            context["rsi14"] = None if rsi != rsi else round(float(rsi), 2)
            context["macd"] = None if macd_v != macd_v else round(float(macd_v), 4)
            context["macd_signal"] = None if macd_s != macd_s else round(float(macd_s), 4)
            context["change_1m"] = round((last / float(close.iloc[-21]) - 1) * 100, 2) if len(close) > 21 else None
            context["change_3m"] = round((last / float(close.iloc[-63]) - 1) * 100, 2) if len(close) > 63 else None

    if req.include_fundamentals:
        info = fetch_info(req.symbol)
        if info:
            context["fundamentals"] = {
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "pe": info.get("trailingPE"),
                "pb": info.get("priceToBook"),
                "roe": info.get("returnOnEquity"),
                "dividend_yield": info.get("dividendYield"),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency"),
            }

    if len(context) <= 1:
        raise HTTPException(status_code=404, detail=f"No data for {sym}")

    system = _SYSTEM_JA if req.language == "ja" else _SYSTEM_EN

    if req.language == "ja":
        user = (
            f"以下のデータをもとに {sym} の現状分析と短期見通しを 250 文字程度で述べてください。\n\n"
            f"```json\n{context}\n```"
        )
    else:
        user = (
            f"Analyze {sym} based on the data below and provide a short outlook "
            f"in ~80 words.\n\n```json\n{context}\n```"
        )

    return AIPromptResponse(symbol=sym, system=system, user=user, context=context)
