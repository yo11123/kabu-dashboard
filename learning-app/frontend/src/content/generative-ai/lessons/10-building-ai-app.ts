export const content = `
# AIアプリ構築

## AIアプリケーション開発の全体像

このレッスンでは、これまで学んだ技術を統合して、実用的なAIアプリケーションを構築する方法を学びます。設計からデプロイまでの全プロセスをカバーします。

## アプリケーションアーキテクチャ

### 基本的な構成

\`\`\`
フロントエンド（UI）
    ↕ API
バックエンド（サーバー）
    ↕
LLM API（OpenAI等）
    ↕
データストア（ベクトルDB等）
\`\`\`

### 主要コンポーネント

\`\`\`python
app_architecture = {
    "frontend": {
        "role": "ユーザーインターフェース",
        "tech": ["React", "Next.js", "Streamlit"]
    },
    "backend": {
        "role": "ビジネスロジック・API管理",
        "tech": ["FastAPI", "Flask", "Express"]
    },
    "llm_service": {
        "role": "AI推論",
        "tech": ["OpenAI API", "Claude API", "ローカルLLM"]
    },
    "data_store": {
        "role": "データ管理",
        "tech": ["PostgreSQL", "Pinecone", "Redis"]
    }
}
\`\`\`

## プロンプト管理システム

\`\`\`python
class PromptManager:
    def __init__(self):
        self.templates = {}
        self.version = "1.0"

    def register_template(self, name, template, variables):
        self.templates[name] = {
            "template": template,
            "variables": variables,
            "version": self.version
        }

    def render(self, name, **kwargs):
        entry = self.templates[name]
        template = entry["template"]
        for var in entry["variables"]:
            if var not in kwargs:
                raise ValueError(f"変数 '{var}' が不足しています")
        return template.format(**kwargs)

# 使用例
pm = PromptManager()
pm.register_template(
    "summarize",
    "以下のテキストを{length}文で要約してください:\\n\\n{text}",
    ["length", "text"]
)
\`\`\`

## APIの設計

\`\`\`python
# FastAPIスタイルのエンドポイント設計
api_endpoints = {
    "POST /api/chat": {
        "description": "チャットメッセージの送信",
        "request": {"message": "str", "session_id": "str"},
        "response": {"reply": "str", "tokens_used": "int"}
    },
    "POST /api/summarize": {
        "description": "テキストの要約",
        "request": {"text": "str", "max_length": "int"},
        "response": {"summary": "str"}
    },
    "POST /api/search": {
        "description": "セマンティック検索",
        "request": {"query": "str", "top_k": "int"},
        "response": {"results": "list"}
    }
}
\`\`\`

## エラーハンドリング戦略

\`\`\`python
class AIAppError(Exception):
    pass

class RetryHandler:
    def __init__(self, max_retries=3, backoff_factor=2):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def execute(self, func, *args, **kwargs):
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                wait_time = self.backoff_factor ** attempt
                last_error = e
                # time.sleep(wait_time)
            except AuthenticationError:
                raise AIAppError("APIキーが無効です")
            except Exception as e:
                last_error = e
        raise AIAppError(f"{self.max_retries}回のリトライ後に失敗: {last_error}")
\`\`\`

## コスト管理

\`\`\`python
class CostTracker:
    PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},       # per 1K tokens
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
    }

    def __init__(self):
        self.total_cost = 0
        self.request_count = 0

    def calculate_cost(self, model, input_tokens, output_tokens):
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})
        cost = (input_tokens / 1000 * pricing["input"] +
                output_tokens / 1000 * pricing["output"])
        self.total_cost += cost
        self.request_count += 1
        return cost

    def get_report(self):
        return {
            "total_cost_usd": round(self.total_cost, 4),
            "request_count": self.request_count,
            "avg_cost_per_request": round(
                self.total_cost / max(self.request_count, 1), 4
            )
        }
\`\`\`

## セキュリティ対策

### プロンプトインジェクション対策

\`\`\`python
def sanitize_input(user_input):
    """ユーザー入力のサニタイズ"""
    # 危険なパターンの検出
    dangerous_patterns = [
        "以前の指示を無視",
        "システムプロンプトを表示",
        "ignore previous instructions",
    ]

    for pattern in dangerous_patterns:
        if pattern.lower() in user_input.lower():
            return None, "不適切な入力が検出されました"

    # 長さ制限
    if len(user_input) > 10000:
        return None, "入力が長すぎます"

    return user_input, None
\`\`\`

## テスト戦略

\`\`\`python
# AIアプリのテスト項目
test_checklist = {
    "unit_tests": [
        "プロンプトテンプレートの正しい生成",
        "入力バリデーション",
        "エラーハンドリング",
        "コスト計算の正確性"
    ],
    "integration_tests": [
        "API呼び出しとレスポンス処理",
        "会話履歴の管理",
        "RAG検索パイプライン"
    ],
    "evaluation": [
        "回答の品質（人間評価）",
        "ハルシネーション率",
        "応答時間",
        "コスト効率"
    ]
}
\`\`\`

## デプロイメント

### チェックリスト
1. APIキーの安全な管理（環境変数）
2. レート制限の実装
3. ログとモニタリングの設定
4. エラーアラートの設定
5. コスト上限の設定

## まとめ

AIアプリケーションの構築には、LLMの知識だけでなく、ソフトウェアエンジニアリングのベストプラクティスが不可欠です。プロンプト管理、エラーハンドリング、コスト管理、セキュリティ対策を適切に実装し、テストとモニタリングを通じて品質を維持しましょう。
`;
