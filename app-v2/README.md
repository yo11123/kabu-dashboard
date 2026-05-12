# Kabu Dashboard v2

Stock analysis app — Next.js 16 + FastAPI rebuild of the original Streamlit app.
Phase 1 MVP focuses on the chart display flow with PC/mobile UX separation.

## Stack
- Frontend: Next.js 16 (App Router) + React 19 + Tailwind v4 + TanStack Query + Zustand + lightweight-charts
- Backend: FastAPI + yfinance + pandas (pure-logic services ported from `../modules/`)
- Markets: JP (4-digit codes auto-suffixed `.T`) + US tickers
- AI: BYOK — user provides Anthropic / OpenAI / Gemini API key in Settings; calls go directly from the frontend, never through the backend

Final target is a Tauri desktop app; web build works today as a development environment.

## Run (dev)

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
# open http://localhost:3000
```

The frontend rewrites `/api/*` to `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_BASE`).

## API endpoints
- `GET  /api/health`
- `GET  /api/symbols/search?q=`
- `GET  /api/stock/{symbol}/ohlcv?period=1y&interval=1d`
- `GET  /api/stock/{symbol}/technicals?period=1y`
- `GET  /api/stock/{symbol}/fundamentals`
- `POST /api/ai/build-prompt`

## Pages
- `/` — Search + recent symbols
- `/stock/[symbol]` — Chart + Technical / Fundamentals / AI tabs (PC: 3-col, Mobile: stacked + bottom-sheet tabs)
- `/settings` — Theme picker + BYOK API keys

## Themes
Set via `data-theme` on `<html>`. Three variants ship in Phase 1: `claude-warm`, `claude-dark`, `terminal`. Define new themes in `frontend/src/app/globals.css` and register them in `frontend/src/lib/themes/index.ts`.
