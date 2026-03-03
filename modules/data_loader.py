import io
import time
import urllib.request

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


@st.cache_data(ttl=86400)
def load_all_tse_stocks() -> list[dict]:
    """
    JPX（日本取引所グループ）から東証全上場銘柄リストを取得する（TTL=24時間）。
    取得失敗時は空リストを返す（呼び出し元が日経225にフォールバック）。

    ソース: https://www.jpx.co.jp/markets/statistics-equities/misc/01.html
    """
    url = (
        "https://www.jpx.co.jp/markets/statistics-equities/misc/"
        "tvdivq0000001vg2-att/data_j.xls"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()

        df = pd.read_excel(io.BytesIO(raw), header=0, engine="xlrd")

        result = []
        for _, row in df.iterrows():
            try:
                # コード列は数値として読み込まれる場合がある（例: 7203.0）
                code_raw = str(row.iloc[0]).replace(".0", "").strip()
                if not code_raw.isdigit() or not (4 <= len(code_raw) <= 5):
                    continue
                code = code_raw.zfill(4)
                name = str(row.iloc[1]).strip()
                market = str(row.iloc[2]).strip() if len(row) > 2 else ""
                sector = str(row.iloc[4]).strip() if len(row) > 4 else ""
                if name and name != "nan":
                    result.append({
                        "code": f"{code}.T",
                        "name": name,
                        "market": market,
                        "sector": sector,
                    })
            except Exception:
                continue

        return sorted(result, key=lambda x: x["code"])

    except Exception:
        return []


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
