import time
import pandas as pd
import yfinance as yf
import streamlit as st


@st.cache_data(ttl=60)
def fetch_stock_data_max_realtime(ticker: str) -> pd.DataFrame | None:
    """
    上場来全データをリアルタイム取得（TTL=60秒）。東証開場中に使用する。
    """
    return _fetch(ticker, "max", "1d")


@st.cache_data(ttl=21600)
def fetch_stock_data_max(ticker: str) -> pd.DataFrame | None:
    """
    上場来全データを取得（TTL=6時間）。東証閉場中に使用する。
    """
    return _fetch(ticker, "max", "1d")


def _fetch(ticker: str, period: str, interval: str) -> pd.DataFrame | None:
    for attempt in range(3):
        try:
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(period=period, interval=interval)

            if df is None or df.empty:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return None

            df.columns = [col.capitalize() for col in df.columns]

            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
            df = df[cols].copy()

            if df["Close"].isna().sum() > len(df) * 0.3:
                return None

            df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)
            return df

        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return None

    return None


@st.cache_data(ttl=3600)
def fetch_ticker_info(ticker: str) -> dict:
    """
    銘柄の基本情報（会社名・ウェブサイトなど）を取得する。
    """
    try:
        info = yf.Ticker(ticker).info
        return {
            "name": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector", ""),
            "market_cap": info.get("marketCap"),
            "website": info.get("website", ""),
            "currency": info.get("currency", "JPY"),
        }
    except Exception:
        return {"name": ticker, "sector": "", "market_cap": None, "website": "", "currency": "JPY"}


def load_tickers(filepath: str) -> list[dict]:
    """
    nikkei225_tickers.txt を読み込んで銘柄リストを返す。
    """
    tickers = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) >= 2:
                    tickers.append({
                        "code": parts[0].strip(),
                        "name": parts[1].strip(),
                        "sector": parts[2].strip() if len(parts) >= 3 else "",
                    })
    except FileNotFoundError:
        st.warning(f"銘柄リストファイルが見つかりません: {filepath}")
    return tickers
