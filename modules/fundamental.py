import streamlit as st
import yfinance as yf
import requests


@st.cache_data(ttl=3600)
def fetch_fundamental_yfinance(ticker: str) -> dict:
    """yfinance から基本的なファンダメンタル指標を取得する（1時間キャッシュ）。"""
    try:
        info = yf.Ticker(ticker).info
        return {
            "per": info.get("trailingPE"),
            "pbr": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),        # 小数 (0.15 = 15%)
            "dividend_yield": info.get("dividendYield"),  # 小数
            "market_cap": info.get("marketCap"),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "revenue_growth": info.get("revenueGrowth"),   # 小数
            "operating_margins": info.get("operatingMargins"),  # 小数
            "eps_trailing": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "forward_pe": info.get("forwardPE"),
            "beta": info.get("beta"),
            "currency": info.get("currency", "JPY"),
        }
    except Exception:
        return {}


def _get_jquants_access_token(refresh_token: str) -> str:
    """J-Quants リフレッシュトークンからアクセストークンを取得する。"""
    resp = requests.post(
        "https://api.jquants.com/v1/token/auth_refresh",
        params={"refreshtoken": refresh_token},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["idToken"]


@st.cache_data(ttl=3600)
def fetch_financial_statements_jquants(ticker: str) -> list[dict]:
    """
    J-Quants API から財務諸表データを取得する（直近4期分、1時間キャッシュ）。
    JQUANTS_REFRESH_TOKEN が secrets に未設定の場合は空リストを返す。
    """
    try:
        refresh_token = st.secrets.get("JQUANTS_REFRESH_TOKEN", "")
        if not refresh_token or len(refresh_token) < 10:
            return []

        code = ticker.replace(".T", "").strip().zfill(4)
        access_token = _get_jquants_access_token(refresh_token)

        resp = requests.get(
            "https://api.jquants.com/v1/fins/statements",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"code": code},
            timeout=15,
        )
        resp.raise_for_status()
        statements = resp.json().get("statements", [])

        # 年次決算を優先、なければ全件から直近4件
        annual = [s for s in statements if "Annual" in s.get("TypeOfDocument", "")]
        source = annual if annual else statements
        return sorted(
            source,
            key=lambda x: x.get("CurrentPeriodEndDate", ""),
            reverse=True,
        )[:4]

    except Exception:
        return []


def format_fundamental_text(fund: dict, jquants: list[dict]) -> str:
    """ファンダメンタルデータを AI プロンプト用テキストに変換する。"""
    lines = []

    per = fund.get("per")
    if per is not None:
        lines.append(f"PER: {per:.1f}倍")

    pbr = fund.get("pbr")
    if pbr is not None:
        lines.append(f"PBR: {pbr:.2f}倍")

    roe = fund.get("roe")
    if roe is not None:
        lines.append(f"ROE: {roe * 100:.1f}%")

    div_yield = fund.get("dividend_yield")
    if div_yield is not None:
        lines.append(f"配当利回り: {div_yield * 100:.2f}%")

    rev_growth = fund.get("revenue_growth")
    if rev_growth is not None:
        lines.append(f"売上高成長率（前年比）: {rev_growth * 100:.1f}%")

    op_margin = fund.get("operating_margins")
    if op_margin is not None:
        lines.append(f"営業利益率: {op_margin * 100:.1f}%")

    eps_t = fund.get("eps_trailing")
    eps_f = fund.get("eps_forward")
    if eps_t is not None:
        lines.append(f"EPS（実績）: {eps_t:.1f}円")
    if eps_f is not None:
        lines.append(f"EPS（予想）: {eps_f:.1f}円")

    beta = fund.get("beta")
    if beta is not None:
        lines.append(f"ベータ: {beta:.2f}")

    mktcap = fund.get("market_cap")
    if mktcap:
        if mktcap >= 1e12:
            lines.append(f"時価総額: ¥{mktcap / 1e12:.2f}兆円")
        else:
            lines.append(f"時価総額: ¥{mktcap / 1e9:.0f}億円")

    sector = fund.get("sector", "")
    industry = fund.get("industry", "")
    if sector:
        lines.append(f"セクター: {sector}" + (f" / {industry}" if industry else ""))

    # J-Quants 財務データ
    if jquants:
        lines.append("\n[財務諸表推移（J-Quants）]")
        for stmt in jquants[:3]:
            period = stmt.get("CurrentPeriodEndDate", "")[:7]
            parts = []
            net_sales = stmt.get("NetSales")
            op_profit = stmt.get("OperatingProfit")
            net_profit = stmt.get("Profit")
            if net_sales:
                parts.append(f"売上={float(net_sales) / 1e9:.0f}億")
            if op_profit:
                parts.append(f"営業利益={float(op_profit) / 1e9:.0f}億")
            if net_profit:
                parts.append(f"純利益={float(net_profit) / 1e9:.0f}億")
            if parts:
                lines.append(f"  {period}: " + " / ".join(parts))

    return "\n".join(lines) if lines else "財務データなし（yfinance で取得できませんでした）"
