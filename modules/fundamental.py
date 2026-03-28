import re

import streamlit as st
import yfinance as yf
import requests
from lxml import html as lhtml


def _parse_kabutan_number(text: str) -> float | None:
    """Kabutan の数値文字列（'12.9倍', '2.70％', '55兆5,984億円' など）を float に変換する。"""
    text = re.sub(r"[,，倍％%兆億円万\s\u3000\xa0]", "", text.strip())
    if not text:
        return None
    # 万・億・兆はすでに除去済み（数値だけ残る）
    try:
        return float(text)
    except ValueError:
        return None


def _parse_market_cap(text: str) -> float | None:
    """'55兆5,984億円' → float (yen) に変換。"""
    text = text.strip().replace(",", "")
    val = 0.0
    m = re.search(r"([\d.]+)兆", text)
    if m:
        val += float(m.group(1)) * 1e12
    m = re.search(r"([\d.]+)億", text)
    if m:
        val += float(m.group(1)) * 1e8
    return val if val > 0 else None


@st.cache_data(ttl=3600)
def fetch_fundamental_kabutan(ticker: str) -> dict:
    """
    Kabutan の財務ページから指標・財務諸表を取得する（1時間キャッシュ）。
    yfinance が取得できない日本株の PER/PBR/配当利回り/時価総額/財務推移を補完する。
    """
    code4 = ticker.replace(".T", "").strip().zfill(4)
    if not code4.isdigit():
        return {}

    try:
        url = f"https://kabutan.jp/stock/finance?code={code4}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        tree = lhtml.fromstring(resp.content)
        tables = tree.xpath("//table")

        result: dict = {}

        # ── table[2]: PER / PBR / 配当利回り / 信用倍率 / 時価総額 ──────────
        # ヘッダー行: ["PER","PBR","利回り","信用倍率"]
        # データ行:  ["12.9倍","1.18倍","2.70％","2.07倍"]
        # 時価総額行: ["時価総額","55兆5,984億円"]
        if len(tables) > 2:
            rows = tables[2].xpath(".//tr")
            if len(rows) >= 2:
                hdr = [c.text_content().strip() for c in rows[0].xpath(".//th|.//td")]
                val = [c.text_content().strip() for c in rows[1].xpath(".//th|.//td")]
                for h, v in zip(hdr, val):
                    if "PER" in h:
                        result["per"] = _parse_kabutan_number(v)
                    elif "PBR" in h:
                        result["pbr"] = _parse_kabutan_number(v)
                    elif "利回り" in h:
                        result["dividend_yield"] = _parse_kabutan_number(v)  # %値
                # 時価総額行
            for row in rows:
                cells = [c.text_content().strip() for c in row.xpath(".//th|.//td")]
                if len(cells) >= 2 and "時価総額" in cells[0]:
                    result["market_cap"] = _parse_market_cap(cells[1])

        # ── table[3]: 財務諸表推移（年次）──────────────────────────────────
        # ヘッダー: 決算期|売上高|営業益|経常益|最終益|修正1株益|修正1株配|発表日
        # 単位: 百万円（EPS・配当は円）
        if len(tables) > 3:
            rows = tables[3].xpath(".//tr")
            financials = []
            for row in rows[1:]:  # ヘッダー行をスキップ
                cells = [c.text_content().strip() for c in row.xpath(".//th|.//td")]
                # 空行スキップ
                if len(cells) < 7 or not cells[0].strip():
                    continue
                period_raw = cells[0]
                # "I　　　2024.03" → "2024.03" を抽出
                m = re.search(r"(\d{4}\.\d{2})", period_raw)
                if not m:
                    continue
                period = m.group(1)

                def _n(s):
                    return _parse_kabutan_number(s)

                sales       = _n(cells[1]) if len(cells) > 1 else None
                op_profit   = _n(cells[2]) if len(cells) > 2 else None
                net_profit  = _n(cells[4]) if len(cells) > 4 else None
                eps         = _n(cells[5]) if len(cells) > 5 else None
                dps         = _n(cells[6]) if len(cells) > 6 else None

                financials.append({
                    "period": period,
                    "sales_m":      sales,       # 百万円
                    "op_profit_m":  op_profit,   # 百万円
                    "net_profit_m": net_profit,  # 百万円
                    "eps":          eps,          # 円
                    "dps":          dps,          # 円（配当/株）
                })

            if financials:
                result["financials"] = financials[:4]  # 直近4期

        return result

    except Exception:
        return {}


@st.cache_data(ttl=3600)
def fetch_fundamental_yfinance(ticker: str) -> dict:
    """yfinance から基本的なファンダメンタル指標を取得する（1時間キャッシュ）。"""
    try:
        info = yf.Ticker(ticker).info
        return {
            "per": info.get("trailingPE"),
            "pbr": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),        # 小数 (0.15 = 15%)
            "roa": info.get("returnOnAssets"),        # 小数
            "dividend_yield": info.get("dividendYield"),  # 小数
            "free_cashflow": info.get("freeCashflow"),   # 円
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


def format_fundamental_text(
    fund: dict,
    jquants: list[dict],
    kabutan: dict | None = None,
) -> str:
    """ファンダメンタルデータを AI プロンプト用テキストに変換する。
    PER/PBR は株価連動で変動するため yfinance（リアルタイム）を優先し、
    yfinance が取得できない場合のみ Kabutan で補完する。
    その他の財務推移データは Kabutan を優先する。
    """
    lines = []
    kb = kabutan or {}

    # ── 株価指標（yfinance 優先 → Kabutan 補完）────────────────────────
    # PER/PBR は株価連動で変動するため、リアルタイム性の高い yfinance を優先
    per = fund.get("per") or kb.get("per")
    if per is not None:
        lines.append(f"PER: {per:.1f}倍")

    pbr = fund.get("pbr") or kb.get("pbr")
    if pbr is not None:
        lines.append(f"PBR: {pbr:.2f}倍")

    roe = fund.get("roe")
    if roe is not None:
        lines.append(f"ROE: {roe * 100:.1f}%")

    roa = fund.get("roa")
    if roa is not None:
        lines.append(f"ROA: {roa * 100:.1f}%")

    # Kabutan の 利回り は % の数値、yfinance は小数
    div_yield_kb = kb.get("dividend_yield")
    div_yield_yf = fund.get("dividend_yield")
    if div_yield_kb is not None:
        lines.append(f"配当利回り: {div_yield_kb:.2f}%")
    elif div_yield_yf is not None:
        lines.append(f"配当利回り: {div_yield_yf * 100:.2f}%")

    mktcap = fund.get("market_cap") or kb.get("market_cap")
    if mktcap:
        if mktcap >= 1e12:
            lines.append(f"時価総額: ¥{mktcap / 1e12:.2f}兆円")
        else:
            lines.append(f"時価総額: ¥{mktcap / 1e9:.0f}億円")

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

    fcf = fund.get("free_cashflow")
    if fcf is not None:
        if abs(fcf) >= 1e12:
            lines.append(f"FCF: ¥{fcf / 1e12:.2f}兆円")
        elif abs(fcf) >= 1e8:
            lines.append(f"FCF: ¥{fcf / 1e8:.0f}億円")
        else:
            lines.append(f"FCF: ¥{fcf:,.0f}")

    beta = fund.get("beta")
    if beta is not None:
        lines.append(f"ベータ: {beta:.2f}")

    sector = fund.get("sector", "")
    industry = fund.get("industry", "")
    if sector:
        lines.append(f"セクター: {sector}" + (f" / {industry}" if industry else ""))

    # ── 財務諸表推移（Kabutan 優先 → J-Quants 補完）──────────────────
    kb_fins = kb.get("financials", [])
    if kb_fins:
        lines.append("\n[財務諸表推移（Kabutan, 単位:百万円）]")
        for f in kb_fins:
            parts = []
            if f.get("sales_m"):
                parts.append(f"売上={f['sales_m'] / 1e4:.0f}億")
            if f.get("op_profit_m"):
                parts.append(f"営業益={f['op_profit_m'] / 1e4:.0f}億")
            if f.get("net_profit_m"):
                parts.append(f"純益={f['net_profit_m'] / 1e4:.0f}億")
            if f.get("eps") is not None:
                parts.append(f"EPS={f['eps']:.1f}円")
            if f.get("dps") is not None:
                parts.append(f"配当={f['dps']:.0f}円")
            if parts:
                lines.append(f"  {f['period']}: " + " / ".join(parts))
    elif jquants:
        lines.append("\n[財務諸表推移（J-Quants）]")
        for stmt in jquants[:4]:
            period = stmt.get("CurrentPeriodEndDate", "")[:7]
            parts = []
            net_sales = stmt.get("NetSales")
            op_profit = stmt.get("OperatingProfit")
            net_profit = stmt.get("Profit")
            if net_sales:
                parts.append(f"売上={float(net_sales) / 1e9:.0f}億")
            if op_profit:
                parts.append(f"営業益={float(op_profit) / 1e9:.0f}億")
            if net_profit:
                parts.append(f"純益={float(net_profit) / 1e9:.0f}億")
            if parts:
                lines.append(f"  {period}: " + " / ".join(parts))

    return "\n".join(lines) if lines else "財務データなし"
