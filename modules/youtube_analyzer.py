"""
YouTube動画分析モジュール
youtube-transcript-api で字幕を取得し、Gemini API（無料枠）で株式分析向けに要約する。
"""
import re
import json
from datetime import date

import streamlit as st
from google import genai
from google.genai import types

from modules.persistence import _file_load, _file_save, _sync_to_gist

_YT_HISTORY_KEY = "youtube_summaries"


# ─── YouTube URL → Video ID ──────────────────────────────────────────────

def extract_video_id(url: str) -> str | None:
    """YouTube URL から video ID を抽出する。"""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    # 直接 ID が渡された場合
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url.strip()):
        return url.strip()
    return None


# ─── 字幕取得 ────────────────────────────────────────────────────────────

def get_transcript(video_id: str, languages: list[str] | None = None, silent: bool = False) -> str:
    """YouTube 動画の字幕テキストを取得する。

    silent=True の場合、エラー時に st.warning を表示しない（フォールバック前提）。
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return ""

    if languages is None:
        languages = ["ja", "en"]

    api = YouTubeTranscriptApi()

    # 方法1: 指定言語で直接取得
    try:
        result = api.fetch(video_id, languages=languages)
        text = " ".join(s.text for s in result.snippets)
        if text.strip():
            return text
    except Exception:
        pass

    # 方法2: 利用可能な字幕を列挙して手動字幕を優先
    try:
        transcript_list = api.list(video_id)
        for lang in languages:
            for t in transcript_list:
                if t.language_code == lang and not t.is_generated:
                    result = api.fetch(video_id, languages=[lang])
                    text = " ".join(s.text for s in result.snippets)
                    if text.strip():
                        return text

        for lang in languages:
            for t in transcript_list:
                if t.language_code == lang and t.is_generated:
                    result = api.fetch(video_id, languages=[lang])
                    text = " ".join(s.text for s in result.snippets)
                    if text.strip():
                        return text

        for t in transcript_list:
            try:
                result = api.fetch(video_id, languages=[t.language_code])
                text = " ".join(s.text for s in result.snippets)
                if text.strip():
                    return text
            except Exception:
                continue

    except Exception:
        pass  # フォールバック（Gemini直接分析）に任せる

    return ""


# ─── 動画タイトル取得 ─────────────────────────────────────────────────────

def get_video_title(video_id: str) -> str:
    """YouTube 動画のタイトルを取得する（oembed API 使用）。"""
    import requests
    try:
        resp = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("title", "")
    except Exception:
        pass
    return ""


# ─── Gemini 要約 ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """あなたは株式投資の専門アナリストです。
YouTube動画の字幕テキストから、投資に役立つ情報を抽出・要約してください。

以下のJSON形式で出力してください（JSONのみ、他のテキストは不要）:
{
  "title_summary": "動画の主題を1行で",
  "market_outlook": "市場全体の見通し（強気/弱気/中立 + 理由）",
  "mentioned_tickers": [
    {"ticker": "銘柄コードまたは名前", "direction": "買い/売り/中立", "reason": "理由"}
  ],
  "key_points": ["要点1", "要点2", "要点3"],
  "risk_factors": ["リスク1", "リスク2"],
  "catalysts": ["カタリスト1", "カタリスト2"],
  "sector_outlook": {"セクター名": "見通し"},
  "confidence": "高/中/低（情報の信頼度）"
}

注意:
- 株式に無関係な内容の場合は、key_pointsに動画の要点のみ入れてください
- mentioned_tickersの銘柄コードは可能なら4桁の証券コード（例: 7203）にしてください
- 具体的な数値や根拠があればそのまま含めてください
"""


def _parse_gemini_json(text: str) -> dict:
    """Geminiの応答からJSONを抽出する。"""
    text = text.strip()
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {"error": "JSON解析失敗", "raw": text[:500]}


def summarize_with_gemini(transcript_or_video_id: str, api_key: str, *, is_video_id: bool = False) -> dict:
    """Gemini API で動画を株式分析向けに要約する。

    is_video_id=True の場合、YouTube URLを直接Geminiに渡して分析する（字幕API不要）。
    is_video_id=False の場合、字幕テキストを渡して分析する。
    """
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        temperature=0.1,
        max_output_tokens=2048,
    )

    # ── 方法1: YouTube URLを直接Geminiに渡す（クラウド対応）──
    if is_video_id:
        video_url = f"https://www.youtube.com/watch?v={transcript_or_video_id}"
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(parts=[
                        types.Part.from_uri(file_uri=video_url, mime_type="video/mp4"),
                        types.Part.from_text(text="この動画を分析してください。"),
                    ]),
                ],
                config=config,
            )
            return _parse_gemini_json(response.text)
        except Exception as e:
            return {"error": f"Gemini動画分析エラー: {str(e)[:200]}"}

    # ── 方法2: 字幕テキストで分析（フォールバック）──
    transcript = transcript_or_video_id
    if not transcript.strip():
        return {"error": "字幕テキストが空です"}

    max_chars = 100000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n...(以下省略)"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"以下のYouTube動画の字幕テキストを分析してください:\n\n{transcript}",
            config=config,
        )
        return _parse_gemini_json(response.text)
    except Exception as e:
        return {"error": f"Gemini API エラー: {str(e)[:200]}"}


# ─── 複数動画の一括分析 ──────────────────────────────────────────────────

def analyze_videos(urls: list[str], api_key: str, progress_bar=None) -> list[dict]:
    """複数のYouTube動画を一括分析する。"""
    results = []
    for i, url in enumerate(urls):
        video_id = extract_video_id(url)
        if not video_id:
            results.append({"url": url, "error": "無効なURL"})
            continue

        title = get_video_title(video_id)

        # 字幕取得を試みる → 失敗したらGeminiに直接YouTube URLを渡す
        transcript = ""
        try:
            transcript = get_transcript(video_id)
        except Exception:
            pass

        if transcript:
            summary = summarize_with_gemini(transcript, api_key, is_video_id=False)
        else:
            # Gemini に YouTube URL を直接渡して分析（クラウド環境対応）
            summary = summarize_with_gemini(video_id, api_key, is_video_id=True)
        results.append({
            "url": url,
            "video_id": video_id,
            "title": title,
            "summary": summary,
            "date": date.today().isoformat(),
            "transcript_length": len(transcript),
        })

        if progress_bar:
            progress_bar.progress((i + 1) / len(urls))

    return results


# ─── 永続化 ──────────────────────────────────────────────────────────────

def save_youtube_summaries(results: list[dict]) -> None:
    """YouTube分析結果を保存する。"""
    history = _file_load(_YT_HISTORY_KEY, [])
    if not isinstance(history, list):
        history = []

    for r in results:
        if "error" in r and "summary" not in r:
            continue
        # 同じ動画の古い結果を除外
        history = [h for h in history if h.get("video_id") != r.get("video_id")]
        history.insert(0, r)

    # 最大100件保持
    history = history[:100]
    _file_save(_YT_HISTORY_KEY, history)
    _sync_to_gist()


def load_youtube_summaries() -> list[dict]:
    """保存済みのYouTube分析結果を読み込む。"""
    history = _file_load(_YT_HISTORY_KEY, [])
    return history if isinstance(history, list) else []


# ─── 統合レポート生成 ────────────────────────────────────────────

_REPORT_PROMPT = """あなたは株式投資の専門アナリストです。
複数のYouTube動画の分析結果を統合し、包括的なマーケットレポートを作成してください。

以下の形式で出力してください（Markdown形式）:

# 今週のマーケットレポート

## 市場全体の見通し
（複数動画の見解を統合し、コンセンサスと相違点を整理）

## 注目銘柄
（複数動画で共通して言及された銘柄を重視。言及回数が多いほど信頼度が高い）
| 銘柄 | 方向 | 根拠 | 言及動画数 |

## セクター動向
（各セクターの見通しを統合）

## リスク要因
（共通して指摘されているリスクを重要度順に）

## カタリスト
（今後のイベントや材料）

## まとめ
（全体を2-3行で総括）

注意:
- 動画ごとに意見が異なる場合は、両方の見解を併記してください
- 複数の動画で同じ意見がある場合は、そのコンセンサスを強調してください
- 具体的な数値や根拠があれば含めてください
"""


def generate_integrated_report(summaries: list[dict], api_key: str) -> str:
    """複数の動画分析結果を統合してマーケットレポートを生成する。"""
    if not summaries:
        return "分析結果がありません。"

    # 各動画の要約を文章にまとめる
    parts = []
    for s in summaries:
        title = s.get("title", "不明")
        summary = s.get("summary", {})
        if not isinstance(summary, dict) or "error" in summary:
            continue
        part = f"### 動画: {title}\n"
        if summary.get("market_outlook"):
            part += f"- 市場見通し: {summary['market_outlook']}\n"
        if summary.get("key_points"):
            for kp in summary["key_points"]:
                part += f"- {kp}\n"
        if summary.get("mentioned_tickers"):
            for t in summary["mentioned_tickers"]:
                part += f"- 銘柄: {t.get('ticker', '?')} ({t.get('direction', '?')}) - {t.get('reason', '')}\n"
        if summary.get("catalysts"):
            for c in summary["catalysts"]:
                part += f"- カタリスト: {c}\n"
        if summary.get("risk_factors"):
            for r in summary["risk_factors"]:
                part += f"- リスク: {r}\n"
        if summary.get("sector_outlook"):
            for k, v in summary["sector_outlook"].items():
                part += f"- セクター {k}: {v}\n"
        parts.append(part)

    if not parts:
        return "有効な分析結果がありません。"

    combined = "\n\n".join(parts)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"以下の{len(parts)}本のYouTube動画分析結果を統合してレポートを作成してください:\n\n{combined}",
            config=types.GenerateContentConfig(
                system_instruction=_REPORT_PROMPT,
                temperature=0.2,
                max_output_tokens=4096,
            ),
        )
        return response.text.strip()
    except Exception as e:
        return f"レポート生成エラー: {str(e)[:200]}"


# ─── 動画Q&A ────────────────────────────────────────────────────

_QA_SYSTEM = """あなたは株式投資の専門アナリストです。
ユーザーが提供したYouTube動画の字幕テキストと分析結果を元に、質問に回答してください。

ルール:
- 動画の内容に基づいて回答してください
- 動画で言及されていない内容については「この動画では言及されていません」と明記してください
- 具体的な数値や銘柄コードがあればそのまま引用してください
- 回答は簡潔に、箇条書きを活用してください
"""


def chat_with_videos(
    question: str,
    selected_summaries: list[dict],
    api_key: str,
    chat_history: list[dict] | None = None,
) -> str:
    """動画の内容についてQ&Aチャットする。"""
    # コンテキスト構築
    context_parts = []
    for s in selected_summaries:
        title = s.get("title", "不明")
        summary = s.get("summary", {})
        # 字幕テキストがあればそれも含める（より詳細な回答のため）
        transcript_info = f"（字幕 {s.get('transcript_length', 0):,} 文字）" if s.get("transcript_length") else ""
        context_parts.append(f"## {title} {transcript_info}")
        if isinstance(summary, dict) and "error" not in summary:
            context_parts.append(json.dumps(summary, ensure_ascii=False, indent=2))

    context = "\n\n".join(context_parts)

    # 会話履歴の構築
    messages = f"以下のYouTube動画の分析結果を参考に質問に回答してください:\n\n{context}\n\n"
    if chat_history:
        for msg in chat_history[-6:]:  # 直近6ターンまで
            role = "ユーザー" if msg["role"] == "user" else "アシスタント"
            messages += f"{role}: {msg['content']}\n\n"
    messages += f"ユーザー: {question}"

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=_QA_SYSTEM,
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )
        return response.text.strip()
    except Exception as e:
        return f"エラー: {str(e)[:200]}"


# ─── レポート永続化 ──────────────────────────────────────────────

def save_report(report_text: str, video_titles: list[str]) -> None:
    """統合レポートを保存する。"""
    history = _file_load("youtube_reports", [])
    if not isinstance(history, list):
        history = []

    entry = {
        "date": date.today().isoformat(),
        "report": report_text,
        "video_count": len(video_titles),
        "video_titles": video_titles[:10],
    }
    history.insert(0, entry)
    history = history[:20]  # 最大20件
    _file_save("youtube_reports", history)
    _sync_to_gist()


def load_reports() -> list[dict]:
    """保存済みの統合レポートを読み込む。"""
    history = _file_load("youtube_reports", [])
    return history if isinstance(history, list) else []


def get_market_insights_from_youtube() -> str:
    """保存済みのYouTube分析から最新の市場インサイトをテキストで返す（AI分析用）。"""
    summaries = load_youtube_summaries()
    if not summaries:
        return ""

    today = date.today().isoformat()
    # 直近7日分のみ
    recent = [s for s in summaries if s.get("date", "") >= str(date.today().replace(day=max(1, date.today().day - 7)))]
    if not recent:
        recent = summaries[:3]

    lines = ["## YouTube動画分析からのインサイト\n"]
    for s in recent[:5]:
        summary = s.get("summary", {})
        if isinstance(summary, dict) and "error" not in summary:
            lines.append(f"### {s.get('title', '不明な動画')} ({s.get('date', '')})")
            if summary.get("market_outlook"):
                lines.append(f"- 市場見通し: {summary['market_outlook']}")
            if summary.get("key_points"):
                for kp in summary["key_points"][:3]:
                    lines.append(f"- {kp}")
            if summary.get("mentioned_tickers"):
                tickers = ", ".join(
                    f"{t['ticker']}({t.get('direction', '?')})" for t in summary["mentioned_tickers"][:5]
                )
                lines.append(f"- 言及銘柄: {tickers}")
            lines.append("")

    return "\n".join(lines)
