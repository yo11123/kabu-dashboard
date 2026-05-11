"""Symbol search.

Phase 1 uses an embedded short list of well-known JP + US tickers plus
free-form passthrough (e.g. typing 'AAPL' or '7203' yields a usable hit
even when not in the curated list). A future phase can swap this for the
JPX official list / yfinance lookup.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..models.schemas import SymbolHit
from ..services.data_loader import normalize_symbol

router = APIRouter()


_CURATED: list[SymbolHit] = [
    SymbolHit(symbol="7203.T", name="トヨタ自動車", market="JP"),
    SymbolHit(symbol="9984.T", name="ソフトバンクグループ", market="JP"),
    SymbolHit(symbol="6758.T", name="ソニーグループ", market="JP"),
    SymbolHit(symbol="8306.T", name="三菱UFJフィナンシャル・グループ", market="JP"),
    SymbolHit(symbol="9432.T", name="日本電信電話", market="JP"),
    SymbolHit(symbol="6861.T", name="キーエンス", market="JP"),
    SymbolHit(symbol="8035.T", name="東京エレクトロン", market="JP"),
    SymbolHit(symbol="4063.T", name="信越化学工業", market="JP"),
    SymbolHit(symbol="AAPL", name="Apple Inc.", market="US"),
    SymbolHit(symbol="MSFT", name="Microsoft Corporation", market="US"),
    SymbolHit(symbol="GOOGL", name="Alphabet Inc.", market="US"),
    SymbolHit(symbol="AMZN", name="Amazon.com Inc.", market="US"),
    SymbolHit(symbol="NVDA", name="NVIDIA Corporation", market="US"),
    SymbolHit(symbol="META", name="Meta Platforms Inc.", market="US"),
    SymbolHit(symbol="TSLA", name="Tesla Inc.", market="US"),
    SymbolHit(symbol="BRK-B", name="Berkshire Hathaway Inc.", market="US"),
]


@router.get("/search", response_model=list[SymbolHit])
def search(q: str = Query("", max_length=32), limit: int = 8) -> list[SymbolHit]:
    q = q.strip()
    if not q:
        return _CURATED[:limit]

    q_lower = q.lower()
    matches = [
        s
        for s in _CURATED
        if q_lower in s.symbol.lower() or q_lower in s.name.lower()
    ]

    if not matches:
        normalized = normalize_symbol(q)
        market = "JP" if normalized.endswith(".T") else "US"
        matches = [SymbolHit(symbol=normalized, name=normalized, market=market)]

    return matches[:limit]
