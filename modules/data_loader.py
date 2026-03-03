import io
import time

import requests
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


_JPX_URL = (
    "https://www.jpx.co.jp/markets/statistics-equities/misc/"
    "tvdivq0000001vg2-att/data_j.xls"
)
_JPX_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html",
}


def _read_jpx_excel(raw: bytes) -> pd.DataFrame:
    """
    .xls / .xlsx 両形式、header 行の位置ずれにも対応して DataFrame を返す。
    """
    for engine in ("xlrd", "openpyxl"):
        for skiprows in (0, 1, 2):
            try:
                df = pd.read_excel(
                    io.BytesIO(raw), header=skiprows, engine=engine
                )
                # 最初の列に 4 桁数字が含まれていれば正しいシートとみなす
                if len(df) > 10:
                    sample = str(df.iloc[0, 0]).replace(".0", "").strip()
                    if sample.isdigit() and len(sample) == 4:
                        return df
            except Exception:
                continue
    raise ValueError("Excel エンジン xlrd/openpyxl いずれでも読み込めませんでした")


def _detect_col(headers: list[str], keywords: list[str], default: int) -> int:
    """列ヘッダー名からキーワードに一致する列インデックスを返す。"""
    for i, h in enumerate(headers):
        if any(k in h for k in keywords):
            return i
    return default


def _fetch_tse_raw() -> list[dict]:
    """
    JPX から全上場銘柄を取得してパースする。失敗時は例外を raise する。
    （@st.cache_data の外側に置き、成功したときのみキャッシュさせる）
    """
    resp = requests.get(_JPX_URL, headers=_JPX_HEADERS, timeout=20)
    resp.raise_for_status()

    df = _read_jpx_excel(resp.content)

    # 列名からコード・銘柄名・市場区分・業種区分の列を自動検出
    headers = [str(c).strip() for c in df.columns]
    code_ci   = _detect_col(headers, ["コード", "code", "Code"],          0)
    name_ci   = _detect_col(headers, ["銘柄名", "name", "Name"],          1)
    market_ci = _detect_col(headers, ["市場", "Market", "market"],        2)
    sector_ci = _detect_col(headers, ["33業種区分", "業種区分", "業種"], 4)

    result = []
    for _, row in df.iterrows():
        try:
            code_raw = str(row.iloc[code_ci]).replace(".0", "").strip()
            if not code_raw.isdigit() or not (1 <= len(code_raw) <= 6):
                continue
            code = code_raw.zfill(4)
            name = str(row.iloc[name_ci]).strip()
            market = str(row.iloc[market_ci]).strip() if len(row) > market_ci else ""
            sector = str(row.iloc[sector_ci]).strip() if len(row) > sector_ci else ""
            if name and name not in ("nan", "None", ""):
                result.append({
                    "code": f"{code}.T",
                    "name": name,
                    "market": market,
                    "sector": sector,
                })
        except Exception:
            continue

    if not result:
        # サイドバーのエラー詳細に表示するため、実際の列名と先頭行を含める
        first_row = [str(v) for v in df.iloc[0].tolist()[:6]] if len(df) > 0 else []
        raise ValueError(
            f"パース結果 0 件 | "
            f"列名: {headers[:6]} | "
            f"1行目: {first_row}"
        )

    return sorted(result, key=lambda x: x["code"])


@st.cache_data(ttl=86400)
def _load_tse_cached() -> list[dict]:
    """
    成功時のみ 24h キャッシュ。
    _fetch_tse_raw() が raise すると @st.cache_data はその結果を保存しない。
    次回呼び出し時に再試行される。
    """
    return _fetch_tse_raw()


def clear_tse_cache() -> None:
    """東証全銘柄キャッシュをクリアする（再取得ボタン用）。"""
    _load_tse_cached.clear()


def load_all_tse_stocks() -> tuple[list[dict], str]:
    """
    東証全上場銘柄を返す。
    Returns:
        (stocks, error_message)
        成功: (list[dict], "")
        失敗: ([], "エラー内容")
    """
    try:
        return _load_tse_cached(), ""
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


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
