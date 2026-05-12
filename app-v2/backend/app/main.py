from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api import symbols, stock, ai, health

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(symbols.router, prefix="/api/symbols")
app.include_router(stock.router, prefix="/api/stock")
app.include_router(ai.router, prefix="/api/ai")
