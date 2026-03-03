import json

import anthropic
import pandas as pd
import streamlit as st

from modules.fundamental import (
    fetch_financial_statements_jquants,
    fetch_fundamental_yfinance,
    format_fundamental_text,
)


# ─── テクニカル指標計算 ──────────────────────────────────────────────────


def _calc_rsi(close: pd.Series, period: int = 14) -> float | None:
    """RSI を計算して直近値を返す。"""
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    loss = loss.replace(0, float("nan"))
    rsi = 100 - 100 / (1 + gain / loss)
    val = rsi.iloc[-1]
    return round(float(val), 1) if val == val else None  # NaN check


def _calc_macd(close: pd.Series) -> dict:
    """MACD を計算して直近のシグナル状態を返す。"""
    if len(close) < 35:
        return {}
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal
    return {
        "macd": round(float(macd_line.iloc[-1]), 2),
        "signal": round(float(signal.iloc[-1]), 2),
        "histogram": round(float(hist.iloc[-1]), 2),
        "bullish_cross": bool(hist.iloc[-1] > 0 and hist.iloc[-2] <= 0),
        "bearish_cross": bool(hist.iloc[-1] < 0 and hist.iloc[-2] >= 0),
    }


def calc_technical_summary(df: pd.DataFrame) -> dict:
    """価格データからテクニカル指標のサマリーを生成する。"""
    close = df["Close"]
    last = float(close.iloc[-1])

    rsi = _calc_rsi(close, 14)
    macd_data = _calc_macd(close)

    sma25 = float(close.rolling(25).mean().iloc[-1]) if len(close) >= 25 else None
    sma75 = float(close.rolling(75).mean().iloc[-1]) if len(close) >= 75 else None

    # 52週高値安値比
    last_year = close.tail(252)
    high52w = float(last_year.max())
    low52w = float(last_year.min())
    pct_from_high = round((last - high52w) / high52w * 100, 1)
    pct_from_low = round((last - low52w) / low52w * 100, 1)

    # 出来高比（5日平均 / 30日平均）
    vol_ratio = None
    if "Volume" in df.columns:
        vol_5 = float(df["Volume"].tail(5).mean())
        vol_30 = float(df["Volume"].tail(30).mean())
        if vol_30 > 0:
            vol_ratio = round(vol_5 / vol_30, 2)

    # ボリンジャーバンド σ 位置
    bb_sigma = None
    if len(close) >= 20:
        bb_mid = float(close.rolling(20).mean().iloc[-1])
        bb_std = float(close.rolling(20).std().iloc[-1])
        if bb_std > 0:
            bb_sigma = round((last - bb_mid) / bb_std, 2)

    return {
        "current_price": round(last, 1),
        "rsi": rsi,
        "macd": macd_data,
        "above_sma25": bool(last > sma25) if sma25 is not None else None,
        "above_sma75": bool(last > sma75) if sma75 is not None else None,
        "pct_from_52w_high": pct_from_high,
        "pct_from_52w_low": pct_from_low,
        "volume_ratio_5d_30d": vol_ratio,
        "bb_sigma": bb_sigma,
    }


# ─── AI 総合分析 ──────────────────────────────────────────────────────────


def _build_prompt(
    ticker: str,
    company_name: str,
    tech: dict,
    fund_text: str,
    news_titles: tuple[str, ...],
) -> str:
    """分析用プロンプトを生成する。"""
    news_text = (
        "\n".join(f"- {t}" for t in news_titles[:10])
        if news_titles
        else "直近のニュースなし"
    )

    macd = tech.get("macd", {})
    if macd.get("bullish_cross"):
        macd_str = f"ゴールデンクロス直後（ヒストグラム=+{macd.get('histogram')}）"
    elif macd.get("bearish_cross"):
        macd_str = f"デッドクロス直後（ヒストグラム={macd.get('histogram')}）"
    elif (macd.get("histogram") or 0) > 0:
        macd_str = f"買いシグナル圏（ヒストグラム=+{macd.get('histogram')}）"
    elif (macd.get("histogram") or 0) < 0:
        macd_str = f"売りシグナル圏（ヒストグラム={macd.get('histogram')}）"
    else:
        macd_str = "データ不足"

    rsi = tech.get("rsi")
    if rsi is None:
        rsi_str = "N/A"
    elif rsi > 70:
        rsi_str = f"{rsi}（買われ過ぎ圏）"
    elif rsi < 30:
        rsi_str = f"{rsi}（売られ過ぎ圏）"
    else:
        rsi_str = f"{rsi}（中立圏）"

    above25 = tech.get("above_sma25")
    above75 = tech.get("above_sma75")

    return f"""あなたは日本株の総合アナリストです。以下のデータをもとに銘柄を多角的に分析し、JSONのみで回答してください。

## 銘柄
{company_name} ({ticker})

## テクニカル指標
- 現在値: ¥{tech.get('current_price', 'N/A'):,}
- RSI(14): {rsi_str}
- MACD: {macd_str}
- SMA25より: {'上方' if above25 else '下方' if above25 is False else 'N/A'}
- SMA75より: {'上方' if above75 else '下方' if above75 is False else 'N/A'}
- 52週高値比: {tech.get('pct_from_52w_high', 'N/A')}%
- 52週安値比: +{tech.get('pct_from_52w_low', 'N/A')}%
- 出来高比(5日/30日): {tech.get('volume_ratio_5d_30d', 'N/A')}倍
- ボリンジャー位置: {tech.get('bb_sigma', 'N/A')}σ

## ファンダメンタル
{fund_text}

## 最近のニュース（直近30日）
{news_text}

## 回答形式（このJSONのみ返答してください）
{{
  "technical_score": 0〜100の整数（テクニカル的強さ。50=中立、高=強気シグナル多数）,
  "fundamental_score": 0〜100の整数（ファンダの良さ。50=中立。データ不足時も50）,
  "news_score": 0〜100の整数（ニュースのポジティブ度。50=中立）,
  "overall_score": 0〜100の整数（3要素の総合評価）,
  "judgment": "強気買い" | "買い" | "中立" | "売り" | "強気売り",
  "technical_detail": "テクニカルの解説（3〜4文、具体的な数値を引用）",
  "fundamental_detail": "ファンダの解説（3〜4文、データ不足の場合はその旨も記載）",
  "news_detail": "ニュースの解説（2〜3文）",
  "overall_detail": "総合判断の根拠（3〜4文）",
  "opportunities": ["上昇要因または強み1", "上昇要因または強み2"],
  "risks": ["リスクまたは注意点1", "リスクまたは注意点2"]
}}"""


def _parse_json(text: str) -> dict:
    """Claude の応答テキストから JSON を抽出してパースする。"""
    text = text.strip()
    if "```" in text:
        for part in text.split("```"):
            part = part.strip().lstrip("json").strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue
    return json.loads(text)


@st.cache_data(ttl=86400)
def get_comprehensive_analysis(
    ticker: str,
    company_name: str,
    tech_json: str,           # calc_technical_summary の結果を JSON 化したもの
    fund_text: str,           # format_fundamental_text の結果
    news_titles: tuple[str, ...],
) -> dict:
    """
    Claude を使って銘柄の総合AI分析を行う（24時間キャッシュ）。

    Returns:
        technical_score, fundamental_score, news_score, overall_score (0-100),
        judgment, technical_detail, fundamental_detail, news_detail,
        overall_detail, opportunities, risks
    """
    _default = {
        "technical_score": 50,
        "fundamental_score": 50,
        "news_score": 50,
        "overall_score": 50,
        "judgment": "中立",
        "technical_detail": "",
        "fundamental_detail": "",
        "news_detail": "",
        "overall_detail": "",
        "opportunities": [],
        "risks": [],
    }

    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key or len(api_key) < 20:
            return {
                **_default,
                "overall_detail": "ANTHROPIC_API_KEY が設定されていません。.streamlit/secrets.toml を確認してください。",
                "error": True,
            }

        tech = json.loads(tech_json)
        prompt = _build_prompt(ticker, company_name, tech, fund_text, news_titles)

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(response.content[0].text)

        # 数値フィールドを int に正規化
        for key in ("technical_score", "fundamental_score", "news_score", "overall_score"):
            result[key] = int(result.get(key, 50))

        return result

    except Exception as e:
        err_str = str(e)
        if "credit balance is too low" in err_str or "upgrade or purchase credits" in err_str:
            detail = (
                "💳 APIクレジットが不足しています。\n"
                "Anthropic コンソール（Plans & Billing）でクレジットを追加してください。"
            )
        elif "invalid_api_key" in err_str or "authentication" in err_str.lower():
            detail = "🔑 APIキーが無効です。secrets.toml の ANTHROPIC_API_KEY を確認してください。"
        else:
            detail = f"分析エラー ({type(e).__name__}): {err_str[:300]}"
        return {**_default, "overall_detail": detail, "error": True}


def prepare_analysis_inputs(
    ticker: str,
    company_name: str,
    df: pd.DataFrame,
    news_events: list[dict],
) -> tuple[str, str, tuple[str, ...]]:
    """
    分析に必要な入力データをまとめて準備する。
    Returns: (tech_json, fund_text, news_titles)
    """
    tech_summary = calc_technical_summary(df)
    tech_json = json.dumps(tech_summary, ensure_ascii=False)

    fund_data = fetch_fundamental_yfinance(ticker)
    jquants_data = fetch_financial_statements_jquants(ticker)
    fund_text = format_fundamental_text(fund_data, jquants_data)

    news_titles = tuple(
        item["title"]
        for ev in news_events
        for item in ev.get("all_items", [{"title": ev.get("title", "")}])
        if item.get("title")
    )[:20]

    return tech_json, fund_text, news_titles
