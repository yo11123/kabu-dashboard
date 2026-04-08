"""
YouTube動画分析モジュール
youtube-transcript-api で字幕を取得し、Gemini API（無料枠）で株式分析向けに要約する。
"""
import re
import json
from datetime import date


def _redact_keys(text: str) -> str:
    """エラーメッセージからAPIキーを除去する。"""
    return re.sub(r'(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|AIza[a-zA-Z0-9_-]{20,})', '[REDACTED]', text)

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


# ─── 字幕取得（3段階フォールバック）──────────────────────────────────

def _get_transcript_youtube_api(video_id: str, languages: list[str]) -> str:
    """方法1: youtube-transcript-api（ローカル環境向け）。"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return ""
    api = YouTubeTranscriptApi()
    try:
        result = api.fetch(video_id, languages=languages)
        text = " ".join(s.text for s in result.snippets)
        if text.strip():
            return text
    except Exception:
        pass
    try:
        transcript_list = api.list(video_id)
        for lang in languages:
            for t in transcript_list:
                if t.language_code == lang:
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
        pass
    return ""


def _get_transcript_supadata(video_id: str, api_key: str) -> str:
    """方法2: Supadata API（クラウド環境対応、月100件無料）。"""
    if not api_key:
        return ""
    try:
        from supadata import Supadata
        client = Supadata(api_key=api_key)
        url = f"https://www.youtube.com/watch?v={video_id}"
        result = client.transcript(url=url, lang="ja", text=True)
        if hasattr(result, "text") and result.text:
            return result.text
        if hasattr(result, "content") and result.content:
            return " ".join(c.text for c in result.content if hasattr(c, "text"))
        if isinstance(result, str):
            return result
    except Exception:
        pass
    return ""


def _analyze_with_notebooklm(video_id: str) -> dict | None:
    """方法3: NotebookLMでYouTube動画を分析（最も高品質）。

    NotebookLMにYouTube URLを渡して分析し、結果をチャットで取得する。
    認証が必要（事前に notebooklm auth login でブラウザ認証が必要）。
    """
    try:
        import asyncio
        from notebooklm.client import NotebookLMClient

        async def _run():
            async with NotebookLMClient.from_storage() as client:
                # ノートブック作成
                nb = await client.notebooks.create(f"YouTube分析_{video_id}")
                nb_id = nb.id

                # YouTube URLをソースとして追加
                url = f"https://www.youtube.com/watch?v={video_id}"
                await client.sources.add_url(nb_id, url, wait=True)

                # NotebookLMに分析を依頼
                prompt = (
                    "この動画の内容を株式投資の観点から分析してください。\n"
                    "以下を含めてください:\n"
                    "1. 動画の主題\n"
                    "2. 市場全体の見通し（強気/弱気/中立と理由）\n"
                    "3. 言及されている銘柄（銘柄名、買い/売り/中立、理由）\n"
                    "4. 重要なポイント（3-5個）\n"
                    "5. リスク要因\n"
                    "6. カタリスト（今後の材料）\n"
                    "7. セクター別の見通し\n"
                )
                result = await client.chat.ask(nb_id, prompt)
                answer = result.answer if hasattr(result, "answer") else str(result)

                # ノートブック削除（掃除）
                try:
                    await client.notebooks.delete(nb_id)
                except Exception:
                    pass

                return answer

        # asyncio のイベントループ処理
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    answer = pool.submit(lambda: asyncio.run(_run())).result(timeout=120)
            else:
                answer = loop.run_until_complete(_run())
        except RuntimeError:
            answer = asyncio.run(_run())

        return answer

    except ImportError:
        return None
    except FileNotFoundError:
        # 認証ファイルがない
        return None
    except Exception:
        return None


def get_transcript(video_id: str, languages: list[str] | None = None, silent: bool = False) -> str:
    """YouTube 動画の字幕テキストを取得する（3段階フォールバック）。

    1. youtube-transcript-api（ローカル環境向け）
    2. Supadata API（クラウド環境対応）
    3. 空文字を返す（呼び出し元でGemini直接分析 or NotebookLMにフォールバック）
    """
    if languages is None:
        languages = ["ja", "en"]

    # 方法1: youtube-transcript-api
    text = _get_transcript_youtube_api(video_id, languages)
    if text:
        return text

    # 方法2: Supadata API
    supadata_key = ""
    try:
        supadata_key = st.secrets.get("SUPADATA_API_KEY", "")
    except Exception:
        pass
    if supadata_key:
        text = _get_transcript_supadata(video_id, supadata_key)
        if text:
            return text

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

## 出力ルール（厳守）
- 下記のJSON形式**のみ**を出力すること。前後に説明文やコードブロック記号(```)を付けないこと
- 全てのキーを必ず含めること（該当なしの場合は空配列 [] や空文字 "" を使う）
- key_pointsは必ず3〜5個にすること
- mentioned_tickersの銘柄コードは4桁の証券コード（例: 7203）を使うこと。不明なら銘柄名で可
- market_outlookは「強気: 理由」「弱気: 理由」「中立: 理由」のいずれかで始めること
- confidenceは「高」「中」「低」の3択のみ

## 出力形式（JSONのみ）
{
  "title_summary": "動画の主題を1行で",
  "market_outlook": "強気/弱気/中立: 具体的な理由",
  "mentioned_tickers": [
    {"ticker": "4桁コードまたは名前", "direction": "買い/売り/中立", "reason": "理由"}
  ],
  "key_points": ["要点1", "要点2", "要点3"],
  "risk_factors": ["リスク1", "リスク2"],
  "catalysts": ["カタリスト1", "カタリスト2"],
  "sector_outlook": {"セクター名": "見通し"},
  "confidence": "高/中/低"
}

注意:
- 株式に無関係な内容の場合は、key_pointsに動画の要点のみ入れてください
- mentioned_tickersの銘柄コードは可能なら4桁の証券コード（例: 7203）にしてください
- 具体的な数値や根拠があればそのまま含めてください
"""


def _parse_gemini_json(text: str) -> dict:
    """Geminiの応答からJSONを抽出する。複数のパース戦略を試みる。"""
    text = text.strip()

    # 戦略1: ```json ... ``` コードブロックを除去
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if code_block:
        text = code_block.group(1).strip()

    # 戦略2: 最も外側の {} を見つける（ネスト対応）
    start = text.find("{")
    if start != -1:
        depth = 0
        end = start
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        candidate = text[start:end]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # 戦略3: 制御文字を除去して再試行
            cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", candidate)
            # 末尾カンマを除去（JSON非準拠だがGeminiが出すことがある）
            cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    # 戦略4: JSONがなければテキスト応答をkey_pointsとして構造化
    if len(text) > 20:
        lines = [l.strip("- ・●").strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
        if lines:
            return {
                "title_summary": lines[0][:100],
                "market_outlook": "中立: テキスト応答のため詳細不明",
                "mentioned_tickers": [],
                "key_points": lines[:5],
                "risk_factors": [],
                "catalysts": [],
                "sector_outlook": {},
                "confidence": "低",
            }

    return {"error": "JSON解析失敗", "raw": text[:500]}


def summarize_with_gemini(transcript_or_video_id: str, api_key: str, *, is_video_id: bool = False) -> dict:
    """Gemini API で動画を株式分析向けに要約する。

    is_video_id=True の場合、YouTube URLを直接Geminiに渡して分析する（字幕API不要）。
    is_video_id=False の場合、字幕テキストを渡して分析する。
    """
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        temperature=0,
        top_p=0.1,
        top_k=1,
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
            return {"error": f"Gemini動画分析エラー: {_redact_keys(str(e)[:200])}"}

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
        return {"error": f"Gemini API エラー: {_redact_keys(str(e)[:200])}"}


# ─── 複数動画の一括分析 ──────────────────────────────────────────────────

def _notebooklm_answer_to_summary(answer: str) -> dict:
    """NotebookLMのテキスト応答を構造化dictに変換する。"""
    lines = [l.strip() for l in answer.split("\n") if l.strip()]
    key_points = []
    tickers = []
    outlook = ""
    risks = []
    catalysts = []

    for line in lines:
        lower = line.lower()
        # 市場見通し検出
        if any(w in line for w in ["見通し", "市場全体", "マーケット", "強気", "弱気"]) and not outlook:
            outlook = line.strip("- ・●#*").strip()
        # リスク検出
        elif any(w in line for w in ["リスク", "懸念", "注意", "不安"]):
            risks.append(line.strip("- ・●#*").strip())
        # カタリスト検出
        elif any(w in line for w in ["カタリスト", "材料", "イベント", "注目"]):
            catalysts.append(line.strip("- ・●#*").strip())
        # 銘柄検出（4桁数字 or 銘柄名っぽいもの）
        elif re.search(r"\d{4}", line) and any(w in line for w in ["買い", "売り", "注目", "推奨"]):
            code_match = re.search(r"(\d{4})", line)
            direction = "買い" if any(w in line for w in ["買い", "推奨", "注目"]) else ("売り" if "売り" in line else "中立")
            tickers.append({"ticker": code_match.group(1) if code_match else "不明", "direction": direction, "reason": line.strip("- ・●#*").strip()[:100]})
        # その他は要点
        elif len(line) > 10 and not line.startswith("#"):
            key_points.append(line.strip("- ・●#*").strip())

    return {
        "title_summary": key_points[0][:100] if key_points else "NotebookLM分析",
        "market_outlook": outlook or "中立: 詳細は要点を参照",
        "mentioned_tickers": tickers[:10],
        "key_points": key_points[:7],
        "risk_factors": risks[:5],
        "catalysts": catalysts[:5],
        "sector_outlook": {},
        "confidence": "高",
        "_source": "NotebookLM",
    }


def _fetch_related_news(summary: dict) -> list[dict]:
    """分析結果から関連ニュースを検索する。"""
    try:
        from modules.market_news import fetch_rss
    except ImportError:
        return []

    # 検索クエリを構築（銘柄名 + キーワード）
    queries = set()
    for t in summary.get("mentioned_tickers", [])[:5]:
        ticker_name = t.get("ticker", "")
        if ticker_name and len(ticker_name) >= 2:
            queries.add(ticker_name)

    # 要点からキーワード抽出
    for kp in summary.get("key_points", [])[:3]:
        # 重要そうな固有名詞を抽出（カタカナ語、英数字）
        names = re.findall(r"[ァ-ヶー]{3,}|[A-Za-z]{3,}", kp)
        for n in names[:2]:
            queries.add(n)

    # 市場見通しのキーワード
    outlook = summary.get("market_outlook", "")
    if "停戦" in outlook or "戦争" in outlook:
        queries.add("停戦 株式")
    if "利上げ" in outlook or "金利" in outlook:
        queries.add("金利 日銀")

    if not queries:
        queries = {"日本株 市場"}

    all_news = []
    seen_titles = set()
    for q in list(queries)[:5]:
        try:
            items = fetch_rss(f"{q} 株", max_items=5)
            for item in items:
                t = item.get("title", "")
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    all_news.append(item)
        except Exception:
            continue

    return all_news[:15]


_DEEP_ANALYSIS_PROMPT = """あなたは日本株市場の上級アナリストです。

以下の3つの情報源を統合して、投資判断に役立つ深い分析を行ってください:
1. YouTube動画の分析結果（NotebookLMまたは字幕から）
2. 関連する最新ニュース
3. あなた自身の市場知識

## 出力ルール（厳守）
- 下記JSON形式のみを出力すること
- 全キーを必ず含めること
- 動画の分析結果とニュースの両方を踏まえた統合分析をすること
- 動画とニュースで矛盾がある場合は両方の見解を併記すること

## 出力形式
{
  "title_summary": "動画＋ニュースを踏まえた総合テーマ（1行）",
  "market_outlook": "強気/弱気/中立: 動画とニュースを踏まえた理由",
  "mentioned_tickers": [
    {"ticker": "4桁コードまたは名前", "direction": "買い/売り/中立", "reason": "動画＋ニュースからの根拠"}
  ],
  "key_points": ["動画からの要点1", "ニュースからの要点2", "統合分析3"],
  "risk_factors": ["リスク1", "リスク2"],
  "catalysts": ["カタリスト1", "カタリスト2"],
  "sector_outlook": {"セクター名": "見通し"},
  "confidence": "高/中/低",
  "news_context": "関連ニュースの要約（2-3行）",
  "integrated_view": "動画の見解とニュースを統合した投資判断（3-5行）"
}
"""


def _deep_analyze_with_gemini(
    base_summary: dict,
    news_items: list[dict],
    api_key: str,
    video_title: str = "",
) -> dict:
    """NotebookLM/字幕分析結果 + ニュースをGeminiで深掘り分析する。"""
    # 入力テキスト構築
    parts = [f"## 動画分析結果: {video_title}\n"]
    parts.append(json.dumps(base_summary, ensure_ascii=False, indent=2))

    if news_items:
        parts.append("\n## 関連する最新ニュース\n")
        for item in news_items[:10]:
            title = item.get("title", "")
            pub = item.get("publisher", "")
            d = item.get("date", "")
            parts.append(f"- [{d}] {title} ({pub})")

    combined = "\n".join(parts)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"以下のYouTube動画分析と関連ニュースを統合して深い分析をしてください:\n\n{combined}",
            config=types.GenerateContentConfig(
                system_instruction=_DEEP_ANALYSIS_PROMPT,
                temperature=0,
                top_p=0.1,
                top_k=1,
                max_output_tokens=3000,
            ),
        )
        result = _parse_gemini_json(response.text)
        if "error" not in result:
            result["_source"] = base_summary.get("_source", "Gemini")
            return result
    except Exception:
        pass

    # 深掘り失敗時はベースの分析結果をそのまま返す
    return base_summary


def analyze_videos(urls: list[str], api_key: str, progress_bar=None) -> list[dict]:
    """複数のYouTube動画を一括分析する。

    分析フロー:
    1. NotebookLMで動画を分析（最優先）
    2. 失敗時: 字幕取得(youtube-transcript-api/Supadata) → Gemini分析
    3. 失敗時: Geminiに直接YouTube URLを渡す
    4. 一次分析結果から関連ニュースを検索
    5. 一次分析＋ニュースをGeminiで統合的に深掘り分析
    """
    results = []
    for i, url in enumerate(urls):
        video_id = extract_video_id(url)
        if not video_id:
            results.append({"url": url, "error": "無効なURL"})
            continue

        title = get_video_title(video_id)
        transcript = ""
        base_summary = None
        source_method = ""

        # ── STEP 1: NotebookLM分析（最優先）──
        nlm_answer = _analyze_with_notebooklm(video_id)
        if nlm_answer:
            base_summary = _notebooklm_answer_to_summary(nlm_answer)
            source_method = "NotebookLM"

        # ── STEP 2: 字幕取得 → Gemini分析 ──
        if base_summary is None or (isinstance(base_summary, dict) and "error" in base_summary):
            try:
                transcript = get_transcript(video_id)
            except Exception:
                pass
            if transcript:
                base_summary = summarize_with_gemini(transcript, api_key, is_video_id=False)
                source_method = "字幕+Gemini"

        # ── STEP 3: Gemini直接動画分析 ──
        if base_summary is None or (isinstance(base_summary, dict) and "error" in base_summary):
            gemini_result = summarize_with_gemini(video_id, api_key, is_video_id=True)
            if not (isinstance(gemini_result, dict) and "error" in gemini_result):
                base_summary = gemini_result
                source_method = "Gemini直接分析"

        if base_summary is None:
            base_summary = {"error": "全ての分析方法が失敗しました"}

        # ── STEP 4: 関連ニュース検索 ──
        news_items = []
        if isinstance(base_summary, dict) and "error" not in base_summary:
            news_items = _fetch_related_news(base_summary)

        # ── STEP 5: Geminiで深掘り統合分析 ──
        final_summary = base_summary
        if isinstance(base_summary, dict) and "error" not in base_summary and api_key:
            final_summary = _deep_analyze_with_gemini(base_summary, news_items, api_key, title)
            if source_method:
                source_method += " → Gemini深掘り"

        results.append({
            "url": url,
            "video_id": video_id,
            "title": title,
            "summary": final_summary,
            "date": date.today().isoformat(),
            "transcript_length": len(transcript),
            "source_method": source_method,
            "news_count": len(news_items),
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
                temperature=0,
                top_p=0.1,
                top_k=1,
                max_output_tokens=4096,
            ),
        )
        return response.text.strip()
    except Exception as e:
        return f"レポート生成エラー: {_redact_keys(str(e)[:200])}"


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
                temperature=0.1,
                top_p=0.2,
                top_k=3,
                max_output_tokens=2048,
            ),
        )
        return response.text.strip()
    except Exception as e:
        return f"エラー: {_redact_keys(str(e)[:200])}"


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
