import json

import anthropic
import pandas as pd
import streamlit as st

from modules.fundamental import (
    fetch_financial_statements_jquants,
    fetch_fundamental_kabutan,
    fetch_fundamental_yfinance,
    format_fundamental_text,
)
from modules.margin import fetch_margin_data, format_margin_text
from modules.market_context import fetch_market_context_text


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


def _calc_stochastic(df: pd.DataFrame, k: int = 14, d: int = 3) -> dict:
    """ストキャスティクス（%K・%D）を計算して直近値を返す。"""
    if len(df) < k:
        return {}
    low_min = df["Low"].rolling(k).min()
    high_max = df["High"].rolling(k).max()
    denom = (high_max - low_min).replace(0, float("nan"))
    stoch_k = (df["Close"] - low_min) / denom * 100
    stoch_d = stoch_k.rolling(d).mean()
    kv = stoch_k.iloc[-1]
    dv = stoch_d.iloc[-1]
    return {
        "k": round(float(kv), 1) if kv == kv else None,
        "d": round(float(dv), 1) if dv == dv else None,
    }


def _calc_cci(df: pd.DataFrame, period: int = 20) -> float | None:
    """CCI（商品チャンネル指数）の直近値を返す。"""
    if len(df) < period:
        return None
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma_tp = tp.rolling(period).mean()
    mean_dev = tp.rolling(period).apply(lambda x: abs(x - x.mean()).mean())
    cci = (tp - sma_tp) / (0.015 * mean_dev.replace(0, float("nan")))
    val = cci.iloc[-1]
    return round(float(val), 1) if val == val else None


def calc_technical_summary(df: pd.DataFrame) -> dict:
    """価格データからテクニカル指標のサマリーを生成する。"""
    close = df["Close"]
    last = float(close.iloc[-1])

    rsi = _calc_rsi(close, 14)
    macd_data = _calc_macd(close)
    stoch_data = _calc_stochastic(df)
    cci = _calc_cci(df)

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

    # ── 過去リターン（騰落率）────────────────────────────────────
    returns = {}
    for label, days in [("1w", 5), ("1m", 21), ("3m", 63), ("6m", 126), ("1y", 252)]:
        if len(close) > days:
            past = float(close.iloc[-(days + 1)])
            if past > 0:
                returns[label] = round((last - past) / past * 100, 1)

    # ── サポート・レジスタンスライン ──────────────────────────────
    support_resistance = {}
    lookback = close.tail(min(len(close), 120))
    if len(lookback) >= 20:
        # 直近120日の安値・高値をサポート・レジスタンスの目安に
        support_resistance["support_1"] = round(float(lookback.min()), 1)
        support_resistance["resistance_1"] = round(float(lookback.max()), 1)
        # 25日移動平均もサポート/レジスタンスとして重要
        if sma25 is not None:
            support_resistance["sma25"] = round(sma25, 1)
        if sma75 is not None:
            support_resistance["sma75"] = round(sma75, 1)
        # 直近20日の安値（短期サポート）
        support_resistance["support_20d"] = round(float(close.tail(20).min()), 1)

    return {
        "current_price": round(last, 1),
        "rsi": rsi,
        "macd": macd_data,
        "stochastic": stoch_data,
        "cci": cci,
        "above_sma25": bool(last > sma25) if sma25 is not None else None,
        "above_sma75": bool(last > sma75) if sma75 is not None else None,
        "pct_from_52w_high": pct_from_high,
        "pct_from_52w_low": pct_from_low,
        "volume_ratio_5d_30d": vol_ratio,
        "bb_sigma": bb_sigma,
        "returns": returns,
        "support_resistance": support_resistance,
    }


# ─── AI 総合分析 ──────────────────────────────────────────────────────────


def _build_prompt(
    ticker: str,
    company_name: str,
    tech: dict,
    fund_text: str,
    news_titles: tuple[str, ...],
    margin_text: str = "",
    market_text: str = "",
    market_news_text: str = "",
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

    stoch = tech.get("stochastic", {})
    sk = stoch.get("k")
    sd = stoch.get("d")
    if sk is not None:
        if sk > 80:
            stoch_str = f"%K={sk}・%D={sd}（買われ過ぎ圏）"
        elif sk < 20:
            stoch_str = f"%K={sk}・%D={sd}（売られ過ぎ圏）"
        else:
            stoch_str = f"%K={sk}・%D={sd}（中立圏）"
    else:
        stoch_str = "N/A"

    cci = tech.get("cci")
    if cci is not None:
        if cci > 100:
            cci_str = f"{cci}（買われ過ぎ圏）"
        elif cci < -100:
            cci_str = f"{cci}（売られ過ぎ圏）"
        else:
            cci_str = f"{cci}（中立圏）"
    else:
        cci_str = "N/A"

    above25 = tech.get("above_sma25")
    above75 = tech.get("above_sma75")

    margin_section = f"\n## 信用取引情報\n{margin_text}" if margin_text else ""
    market_section = f"\n{market_text}" if market_text else ""

    # ── 過去リターン ──────────────────────────────────────────
    returns = tech.get("returns", {})
    returns_lines = []
    for label, name in [("1w", "1週間"), ("1m", "1ヶ月"), ("3m", "3ヶ月"), ("6m", "6ヶ月"), ("1y", "1年")]:
        val = returns.get(label)
        if val is not None:
            returns_lines.append(f"  {name}: {val:+.1f}%")
    returns_text = "\n".join(returns_lines) if returns_lines else "  データ不足"

    # ── サポート・レジスタンス ─────────────────────────────────
    sr = tech.get("support_resistance", {})
    sr_lines = []
    if sr.get("resistance_1"):
        sr_lines.append(f"  直近120日高値（レジスタンス）: ¥{sr['resistance_1']:,.0f}")
    if sr.get("sma25"):
        sr_lines.append(f"  SMA25: ¥{sr['sma25']:,.0f}")
    if sr.get("sma75"):
        sr_lines.append(f"  SMA75: ¥{sr['sma75']:,.0f}")
    if sr.get("support_20d"):
        sr_lines.append(f"  直近20日安値（短期サポート）: ¥{sr['support_20d']:,.0f}")
    if sr.get("support_1"):
        sr_lines.append(f"  直近120日安値（サポート）: ¥{sr['support_1']:,.0f}")
    sr_text = "\n".join(sr_lines) if sr_lines else "  データ不足"

    return f"""あなたはCFA資格を持つ日本株の上級アナリストです。
以下のデータをもとに、プロのアナリストとして段階的に深く分析してください。

## ★★★ 最重要ルール: データの正確性 ★★★
- 分析に使用する数値は、**必ず下記の提供データをそのまま引用すること**
- あなた自身の訓練データや記憶にある数値（株価・PER・配当等）は一切使用禁止
- 提供データに含まれない情報については推測で数値を補わず、「データなし」と明記すること
- ニュース見出しに含まれる数値よりも、構造化データ（テクニカル・ファンダメンタル）の数値を優先すること

## 銘柄
{company_name} ({ticker})

## テクニカル指標
- 現在値: ¥{tech.get('current_price', 'N/A'):,}
- RSI(14): {rsi_str}
- MACD: {macd_str}
- ストキャスティクス(14,3): {stoch_str}
- CCI(20): {cci_str}
- SMA25より: {'上方' if above25 else '下方' if above25 is False else 'N/A'}
- SMA75より: {'上方' if above75 else '下方' if above75 is False else 'N/A'}
- 52週高値比: {tech.get('pct_from_52w_high', 'N/A')}%
- 52週安値比: +{tech.get('pct_from_52w_low', 'N/A')}%
- 出来高比(5日/30日): {tech.get('volume_ratio_5d_30d', 'N/A')}倍
- ボリンジャー位置: {tech.get('bb_sigma', 'N/A')}σ

## 過去リターン（騰落率）
{returns_text}

## サポート・レジスタンスライン
{sr_text}

## ファンダメンタル
{fund_text}{margin_section}{market_section}

## この銘柄のニュース（直近30日）
{news_text}

{market_news_text}

## 分析手順（この順番で段階的に思考してください）

### Step 1: テクニカル分析
- RSI・MACD・ストキャスティクス・CCIの各指標が示す方向性は一致しているか？
- 過去リターンからモメンタム（上昇/下降トレンド）の強さを判断
- サポート/レジスタンスラインとの距離感は？ブレイクアウトの可能性は？
- 出来高は価格変動を裏付けているか？
- 複数の指標が矛盾する場合、どの指標を重視すべきか理由とともに判断

### Step 2: ファンダメンタル分析
- PER・PBRは同業他社や市場平均と比較してどうか？（日本市場平均: PER約15倍, PBR約1.3倍）
- ROE 8%以上か？ 資本効率は改善傾向か？
- 売上・利益の成長トレンドはどうか？
- 配当利回りと配当性向のバランスは持続可能か？
- FCFはプラスで安定しているか？

### Step 3: マーケット環境の影響
- 現在のVIX水準やイールドカーブは、この銘柄にとって有利か不利か？
- 為替（ドル円）の動向はこの銘柄の業績にどう影響するか？
- セクター指標（SOX、ラッセル2000等）との関連性は？

### Step 4: ニュース・カタリスト分析
- 直近のニュースにポジティブ/ネガティブなカタリストはあるか？
- 決算発表が近い場合、市場の期待値は？

### Step 5: 総合判断
- Step 1〜4を統合し、リスク/リワード比を考慮して最終判断を下す
- 強気/弱気の根拠を具体的な数値で裏付ける

## 出力形式
上記の思考プロセスを踏まえた上で、最終的に以下のJSON **のみ** を出力してください。
思考過程やコードブロック外のテキストは不要です。結論のみをJSONに凝縮してください。
各detailフィールドには、上記Stepの分析結果を反映した深い洞察を書いてください。
**detailフィールド内で数値を引用する場合は、必ず上記の提供データの数値をそのまま使ってください。**

```json
{{
  "technical_score": 0〜100の整数（50=中立。指標の一致度・モメンタム・サポレジ距離を総合判断）,
  "fundamental_score": 0〜100の整数（50=中立。同業比較・成長性・財務健全性を総合判断）,
  "news_score": 0〜100の整数（50=中立。カタリストの有無と影響度）,
  "overall_score": 0〜100の整数（テク40%+ファンダ35%+ニュース15%+マーケット環境10%で加重）,
  "judgment": "強気買い" | "買い" | "中立" | "売り" | "強気売り",
  "technical_detail": "テクニカル分析の詳細（5〜6文。提供データの指標値を正確に引用し、一致/乖離、モメンタム、サポレジ、出来高の裏付けを解説）",
  "fundamental_detail": "ファンダメンタル分析の詳細（5〜6文。提供データのPER/PBR/ROE等を正確に引用し、同業比較、成長性、配当持続性を解説）",
  "news_detail": "ニュース・カタリスト分析（3〜4文。マーケット環境の影響も含む）",
  "overall_detail": "総合判断の根拠（5〜6文。リスク/リワード比、エントリーポイントの妥当性、時間軸を含む）",
  "opportunities": ["具体的な上昇要因1（提供データの数値を引用）", "具体的な上昇要因2", "具体的な上昇要因3"],
  "risks": ["具体的なリスク1（提供データの数値を引用）", "具体的なリスク2", "具体的なリスク3"]
}}
```"""


def _parse_json(text: str) -> dict:
    """LLM の応答テキストから JSON を抽出してパースする。

    Chain of Thought で思考テキストが混在する場合でも、
    ```json ... ``` ブロックや裸の { ... } を確実に抽出する。
    """
    import re as _re

    text = text.strip()

    # 1. ```json ... ``` ブロックを優先的に探す
    if "```" in text:
        for part in text.split("```"):
            part = part.strip().lstrip("json").strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue

    # 2. テキスト中の最初の { ... } ブロックを抽出
    match = _re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 3. フォールバック: そのままパース
    return json.loads(text)


# ─── プロバイダー別 LLM 呼び出し ─────────────────────────────────────────


def _call_claude(prompt: str, api_key: str, model: str = "claude-haiku-4-5-20251001") -> str:
    """Claude (Anthropic) を呼び出す。"""
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _call_openai(prompt: str, api_key: str) -> str:
    """ChatGPT (OpenAI) を呼び出す。"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _call_gemini(prompt: str, api_key: str) -> str:
    """Gemini (Google) を REST API で直接呼び出す（SDK の文字コード問題を回避）。"""
    import json as _json
    import requests as _req

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 4096,
        },
    }
    resp = _req.post(
        url,
        params={"key": api_key},
        headers={"Content-Type": "application/json; charset=utf-8"},
        data=_json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _get_gemini_key() -> str:
    """secrets から Gemini API キーを取得。"""
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


def get_light_llm_provider() -> str:
    """現在の軽量LLMプロバイダー名を返す。"""
    return "Gemini" if _get_gemini_key() else "Claude"


def call_light_llm(prompt: str) -> str:
    """軽量タスク用。Gemini 無料枠を優先、なければ Claude Haiku。"""
    gemini_key = _get_gemini_key()
    if gemini_key:
        return _call_gemini(prompt, gemini_key)

    # フォールバック: Claude Haiku
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        key = ""
    if key:
        return _call_claude(prompt, key)
    raise ValueError("GEMINI_API_KEY も ANTHROPIC_API_KEY も設定されていません")


def _classify_error(err_str: str, provider: str) -> str:
    """エラー文字列から分かりやすいメッセージを生成する。"""
    s = err_str.lower()
    if "credit balance is too low" in s or "upgrade or purchase credits" in s:
        return (
            "💳 APIクレジットが不足しています。\n"
            "Anthropic コンソール（Plans & Billing）でクレジットを追加してください。"
        )
    if "quota" in s or "rate limit" in s or "resource_exhausted" in s:
        return "⏱️ APIレート制限またはクォータ超過です。しばらく待ってから再試行してください。"
    if "invalid_api_key" in s or "incorrect api key" in s or "api_key_invalid" in s:
        return f"🔑 APIキーが無効です（{provider}）。入力した API キーを確認してください。"
    if "authentication" in s or "unauthorized" in s:
        return f"🔑 認証エラーです（{provider}）。APIキーを確認してください。\n\n詳細: {err_str[:300]}"
    if "permission" in s and "denied" in s:
        return f"🔑 権限エラーです（{provider}）。APIキーの権限を確認してください。\n\n詳細: {err_str[:300]}"
    return f"分析エラー ({provider}): {err_str[:500]}"


@st.cache_data(ttl=3600 * 4)
def get_comprehensive_analysis(
    ticker: str,
    company_name: str,
    tech_json: str,            # calc_technical_summary の結果を JSON 化したもの
    fund_text: str,            # format_fundamental_text の結果
    news_titles: tuple[str, ...],
    margin_text: str = "",     # format_margin_text の結果（信用残・貸借倍率）
    market_text: str = "",     # fetch_market_context_text の結果（マーケット環境）
    provider: str = "claude",  # "claude" | "openai" | "gemini"
    api_key: str = "",         # ユーザー入力キー（空なら secrets から Claude キーを使用）
) -> dict:
    """
    指定されたプロバイダーの LLM で銘柄の総合AI分析を行う（4時間キャッシュ）。

    Returns:
        technical_score, fundamental_score, news_score, overall_score (0-100),
        judgment, technical_detail, fundamental_detail, news_detail,
        overall_detail, opportunities, risks, error (bool)
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
        "error": False,
    }

    _provider_labels = {
        "claude": "Claude (Anthropic)",
        "openai": "ChatGPT (OpenAI)",
        "gemini": "Gemini (Google)",
    }
    label = _provider_labels.get(provider, provider)

    def _is_valid_key(k: str, prefix: str) -> bool:
        return bool(k) and k.isascii() and k.startswith(prefix)

    try:
        tech = json.loads(tech_json)
        # 市場全体のニュースを取得してプロンプトに含める
        try:
            from modules.market_news import format_news_for_prompt
            _mkt_news = format_news_for_prompt(max_per_cat=5)
        except Exception:
            _mkt_news = ""
        prompt = _build_prompt(ticker, company_name, tech, fund_text, news_titles,
                               margin_text, market_text, _mkt_news)

        if provider == "claude":
            # Claude は secrets の共用キー or ユーザー入力キーを使用
            key = api_key.strip()
            if not key:
                try:
                    key = st.secrets.get("ANTHROPIC_API_KEY", "")
                except Exception:
                    key = ""
            if not key or len(key) < 20:
                return {
                    **_default,
                    "overall_detail": "Anthropic API キーが設定されていません。サイドバーにキーを入力するか、secrets.toml を確認してください。",
                    "error": True,
                }
            text = _call_claude(prompt, key, model="claude-haiku-4-5-20251001")

        elif provider == "openai":
            key = api_key.strip()
            if not _is_valid_key(key, "sk-"):
                return {
                    **_default,
                    "overall_detail": "🔑 OpenAI API キーが無効です（'sk-' で始まるキーを入力してください）。",
                    "error": True,
                }
            text = _call_openai(prompt, key)

        elif provider == "gemini":
            key = api_key.strip()
            if not _is_valid_key(key, "AIza"):
                return {
                    **_default,
                    "overall_detail": "🔑 Gemini API キーが無効です（'AIza' で始まるキーを入力してください）。",
                    "error": True,
                }
            text = _call_gemini(prompt, key)

        else:
            return {
                **_default,
                "overall_detail": f"不明なプロバイダー: {provider}",
                "error": True,
            }

        result = _parse_json(text)

        # 数値フィールドを int に正規化
        for k in ("technical_score", "fundamental_score", "news_score", "overall_score"):
            result[k] = int(result.get(k, 50))

        result["error"] = False
        result["provider"] = label
        return result

    except Exception as e:
        detail = _classify_error(str(e), label)
        return {**_default, "overall_detail": detail, "error": True}


# ─── AI チャット ──────────────────────────────────────────────────────────


def build_chat_system_prompt(
    ticker: str,
    company_name: str,
    tech_json: str,
    fund_text: str,
    margin_text: str = "",
    news_titles: tuple[str, ...] = (),
) -> str:
    """チャット用のシステムプロンプトを生成する（銘柄コンテキスト付き）。

    毎回最新のマーケット環境・市場ニュースを取得してプロンプトに含める。
    """
    try:
        tech = json.loads(tech_json) if tech_json else {}
    except Exception:
        tech = {}

    market_text = fetch_market_context_text()
    margin_section = f"\n\n## 信用取引情報\n{margin_text}" if margin_text else ""
    market_section = f"\n\n{market_text}" if market_text else ""

    # 銘柄別ニュース
    stock_news = ""
    if news_titles:
        stock_news = "\n\n## この銘柄の最新ニュース\n" + "\n".join(f"- {t}" for t in news_titles[:15])

    # 市場全体のニュース
    market_news = ""
    try:
        from modules.market_news import format_news_for_prompt
        market_news = "\n\n" + format_news_for_prompt(max_per_cat=3)
    except Exception:
        pass

    return f"""あなたは日本株の専門アナリストアシスタントです。
ユーザーから {company_name}（{ticker}）についての質問を受けています。
以下のデータを参考に、具体的で分かりやすい日本語で回答してください。

## ★ データの正確性ルール
- 数値を引用する場合は、下記の提供データの数値をそのまま使うこと
- あなたの訓練データや記憶にある数値は使用禁止

## 銘柄情報
銘柄: {company_name}（{ticker}）

## テクニカルデータ（最新値）
{json.dumps(tech, ensure_ascii=False, indent=2)}

## ファンダメンタルデータ
{fund_text}{margin_section}{market_section}{stock_news}{market_news}

回答は簡潔で具体的にしてください。不明な点は正直に不明と答えてください。"""


def get_chat_response(
    messages: list[dict],
    system_prompt: str,
    provider: str = "claude",
    api_key: str = "",
) -> str:
    """
    チャット形式で LLM に問い合わせる（キャッシュなし、マルチターン対応）。

    Args:
        messages: [{"role": "user"|"assistant", "content": str}, ...]
        system_prompt: 銘柄コンテキスト付きシステムプロンプト
        provider: "claude" | "openai" | "gemini"
        api_key: ユーザー入力 API キー

    Returns:
        AI の応答テキスト（エラー時はエラーメッセージ）
    """
    _provider_labels = {
        "claude": "Claude (Anthropic)",
        "openai": "ChatGPT (OpenAI)",
        "gemini": "Gemini (Google)",
    }
    label = _provider_labels.get(provider, provider)

    def _ok(k: str, prefix: str) -> bool:
        return bool(k) and k.isascii() and k.startswith(prefix)

    try:
        if provider == "claude":
            key = api_key.strip()
            if not key:
                try:
                    key = st.secrets.get("ANTHROPIC_API_KEY", "")
                except Exception:
                    key = ""
            if not key or len(key) < 20:
                return "❌ Anthropic API キーが設定されていません。サイドバーで API キーを入力してください。"
            client = anthropic.Anthropic(api_key=key)
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                temperature=0,
                system=system_prompt,
                messages=messages,
            )
            return response.content[0].text

        elif provider == "openai":
            from openai import OpenAI
            key = api_key.strip()
            if not _ok(key, "sk-"):
                return "❌ OpenAI API キーが無効です（'sk-' で始まるキーを入力してください）。サイドバーで API キーを確認してください。"
            client = OpenAI(api_key=key)
            openai_messages = [{"role": "system", "content": system_prompt}] + messages
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1000,
                temperature=0,
                messages=openai_messages,
            )
            return response.choices[0].message.content

        elif provider == "gemini":
            import json as _json
            import requests as _req
            key = api_key.strip()
            if not _ok(key, "AIza"):
                return "❌ Gemini API キーが無効です（'AIza' で始まるキーを入力してください）。サイドバーで API キーを確認してください。"
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": 1000,
                },
            }
            resp = _req.post(
                url,
                params={"key": key},
                headers={"Content-Type": "application/json; charset=utf-8"},
                data=_json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

        else:
            return f"❌ 不明なプロバイダー: {provider}"

    except Exception as e:
        return f"❌ {_classify_error(str(e), label)}"


def _format_earnings_for_prompt(ticker: str) -> str:
    """直近の四半期決算イベントをAIプロンプト用テキストに変換する。"""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        # 決算日一覧
        dates = t.get_earnings_dates(limit=12)
        if dates is None or dates.empty:
            return ""

        lines = ["[直近の決算発表]"]
        for idx, row in dates.head(6).iterrows():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
            eps_actual = row.get("Reported EPS")
            eps_est = row.get("EPS Estimate")
            surprise = row.get("Surprise(%)")

            parts = [date_str]
            if eps_est is not None and eps_est == eps_est:  # NaN check
                parts.append(f"EPS予想={eps_est:.2f}")
            if eps_actual is not None and eps_actual == eps_actual:
                parts.append(f"EPS実績={eps_actual:.2f}")
            if surprise is not None and surprise == surprise:
                beat = "超過" if surprise > 0 else "未達"
                parts.append(f"サプライズ={surprise:+.1f}%({beat})")

            if len(parts) > 1:  # 日付以外にデータがある場合のみ
                lines.append(f"  {' / '.join(parts)}")

        # 四半期財務諸表（yfinance）
        try:
            q_stmt = t.quarterly_income_stmt
            if q_stmt is not None and not q_stmt.empty:
                lines.append("[四半期業績推移]")
                for col in q_stmt.columns[:4]:  # 直近4四半期
                    period = col.strftime("%Y-%m") if hasattr(col, "strftime") else str(col)[:7]
                    parts = []
                    rev = q_stmt.at["Total Revenue", col] if "Total Revenue" in q_stmt.index else None
                    op = q_stmt.at["Operating Income", col] if "Operating Income" in q_stmt.index else None
                    net = q_stmt.at["Net Income", col] if "Net Income" in q_stmt.index else None
                    if rev is not None and rev == rev:
                        parts.append(f"売上={float(rev) / 1e9:.0f}億")
                    if op is not None and op == op:
                        parts.append(f"営業益={float(op) / 1e9:.0f}億")
                    if net is not None and net == net:
                        parts.append(f"純益={float(net) / 1e9:.0f}億")
                    if parts:
                        lines.append(f"  {period}: {' / '.join(parts)}")
        except Exception:
            pass

        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception:
        return ""


def prepare_analysis_inputs(
    ticker: str,
    company_name: str,
    df: pd.DataFrame,
    news_events: list[dict],
) -> tuple[str, str, tuple[str, ...], str, str]:
    """
    分析に必要な入力データをまとめて準備する。
    Returns: (tech_json, fund_text, news_titles, margin_text, market_text)
    """
    tech_summary = calc_technical_summary(df)
    tech_json = json.dumps(tech_summary, ensure_ascii=False)

    fund_data = fetch_fundamental_yfinance(ticker)
    jquants_data = fetch_financial_statements_jquants(ticker)
    kabutan_data = fetch_fundamental_kabutan(ticker)
    fund_text = format_fundamental_text(fund_data, jquants_data, kabutan=kabutan_data)

    # 四半期決算データを追加
    earnings_text = _format_earnings_for_prompt(ticker)
    if earnings_text:
        fund_text = fund_text + "\n\n" + earnings_text

    news_titles = tuple(
        item["title"]
        for ev in news_events
        for item in ev.get("all_items", [{"title": ev.get("title", "")}])
        if item.get("title")
    )[:20]

    margin_data = fetch_margin_data(ticker)
    margin_text = format_margin_text(margin_data)

    market_text = fetch_market_context_text()

    return tech_json, fund_text, news_titles, margin_text, market_text
