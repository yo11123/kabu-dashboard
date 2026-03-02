import os
import sys
import json
import anthropic
import streamlit as st

# Windows でのコンソールエンコーディング問題を回避する
# anthropic SDK が内部ログを書く際に UnicodeEncodeError が起きるのを防ぐ
os.environ.setdefault("PYTHONUTF8", "1")
if sys.platform == "win32":
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Streamlit がすでに stdout を置き換えている場合は無視


def _get_client() -> anthropic.Anthropic:
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key or "ここに" in api_key or len(api_key) < 20:
        raise ValueError(
            "ANTHROPIC_API_KEY が設定されていません。"
            ".streamlit/secrets.toml に正しいキーを入力してください。"
        )
    return anthropic.Anthropic(api_key=api_key)


def _parse_json_response(text: str) -> dict:
    """Claude の応答テキストから JSON を抽出してパースする。"""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue
    return json.loads(text)


@st.cache_data(ttl=86400)
def get_earnings_analysis(
    ticker: str,
    company_name: str,
    period_end: str,
    revenue: float | None,
    operating_income: float | None,
    eps_actual: float | None,
    eps_estimate: float | None,
    beat: bool | None,
) -> dict:
    """
    Claude claude-haiku-4-5 を使って決算データを分析する（24 時間キャッシュ）。
    """
    if revenue is not None:
        rev_str = f"¥{revenue / 1e12:.2f}兆円" if revenue >= 1e12 else f"¥{revenue / 1e9:.0f}億円"
    else:
        rev_str = "不明"

    if operating_income is not None:
        op_str = f"¥{operating_income / 1e9:.0f}億円" if operating_income >= 0 \
            else f"▲¥{abs(operating_income) / 1e9:.0f}億円（赤字）"
    else:
        op_str = "不明"

    eps_str = f"{eps_actual:.1f}" if eps_actual is not None else "不明"
    eps_est_str = f"{eps_estimate:.1f}" if eps_estimate is not None else "不明"

    if beat is True:
        beat_str = "予想を上回った"
    elif beat is False:
        beat_str = "予想を下回った"
    else:
        beat_str = "比較データなし"

    prompt = (
        f"あなたは日本株の決算アナリストです。以下の決算データを分析し、JSON形式のみで回答してください。\n\n"
        f"企業: {company_name} ({ticker})\n"
        f"決算期末: {period_end}\n"
        f"売上高: {rev_str}\n"
        f"営業利益: {op_str}\n"
        f"EPS実績: {eps_str}円\n"
        f"EPS予想: {eps_est_str}円\n"
        f"EPS比較: {beat_str}\n\n"
        '以下のJSON形式のみで回答してください（前後に余計なテキスト不要）:\n'
        '{\n'
        '  "assessment": "良い" または "悪い" または "中立",\n'
        '  "assessment_detail": "決算の総合評価を2〜3文で説明",\n'
        '  "key_points": ["注目ポイント1", "注目ポイント2", "注目ポイント3"],\n'
        '  "stock_impact": "上昇" または "下落" または "中立",\n'
        '  "reasoning": "株価への影響の根拠を1〜2文で説明"\n'
        '}'
    )

    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json_response(response.content[0].text)
    except ValueError as e:
        return {
            "assessment": "中立",
            "assessment_detail": str(e),
            "key_points": [],
            "stock_impact": "中立",
            "reasoning": "",
        }
    except Exception as e:
        err_type = type(e).__name__
        err_msg = str(e)[:200]
        return {
            "assessment": "中立",
            "assessment_detail": f"AI分析エラー（{err_type}）: {err_msg}",
            "key_points": [],
            "stock_impact": "中立",
            "reasoning": "",
        }


@st.cache_data(ttl=86400)
def get_news_analysis(
    ticker: str,
    company_name: str,
    news_titles: tuple[str, ...],
    news_date: str,
) -> dict:
    """
    Claude claude-haiku-4-5 を使ってニュースを分析する（24 時間キャッシュ）。
    news_titles は tuple（st.cache_data がハッシュ化できるようにするため）。
    """
    headlines = "\n".join(f"- {t}" for t in list(news_titles)[:5])

    prompt = (
        f"あなたは日本株の市場アナリストです。以下のニュースを分析し、JSON形式のみで回答してください。\n\n"
        f"企業: {company_name} ({ticker})\n"
        f"日付: {news_date}\n"
        f"ニュース見出し:\n{headlines}\n\n"
        '以下のJSON形式のみで回答してください（前後に余計なテキスト不要）:\n'
        '{\n'
        '  "summary": "ニュースの要約（日本語、3〜4文）",\n'
        '  "stock_impact": "上昇" または "下落" または "中立",\n'
        '  "confidence": "高" または "中" または "低",\n'
        '  "reasoning": "株価影響の根拠（1〜2文）",\n'
        '  "key_risk": "反対シナリオのリスク（1文）"\n'
        '}'
    )

    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json_response(response.content[0].text)
    except ValueError as e:
        return {
            "summary": str(e),
            "stock_impact": "中立",
            "confidence": "低",
            "reasoning": "",
            "key_risk": "",
        }
    except Exception as e:
        err_type = type(e).__name__
        err_msg = str(e)[:200]
        return {
            "summary": f"AI分析エラー（{err_type}）: {err_msg}",
            "stock_impact": "中立",
            "confidence": "低",
            "reasoning": "",
            "key_risk": "",
        }
