export const content = `
# チャットボット構築

## チャットボットの基本概念

LLMを使ったチャットボットは、会話の文脈を管理しながらユーザーと対話するアプリケーションです。このレッスンでは、チャットボットの設計と実装に必要な知識を学びます。

## 会話履歴の管理

チャットボットの核心は**会話履歴の管理**です。

\`\`\`python
class ChatHistory:
    def __init__(self, system_prompt=""):
        self.messages = []
        if system_prompt:
            self.messages.append({
                "role": "system",
                "content": system_prompt
            })

    def add_user_message(self, content):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content):
        self.messages.append({"role": "assistant", "content": content})

    def get_messages(self):
        return self.messages.copy()
\`\`\`

## メッセージフォーマット

OpenAI APIの会話形式：

\`\`\`python
messages = [
    {"role": "system", "content": "あなたは料理の専門家です。"},
    {"role": "user", "content": "カレーの作り方を教えて"},
    {"role": "assistant", "content": "カレーの基本的な作り方をご説明します..."},
    {"role": "user", "content": "辛さを調整するには？"},
    # ← AIは会話の流れを理解して回答
]
\`\`\`

## コンテキストウィンドウの管理

会話が長くなるとトークン制限に達します。

\`\`\`python
def manage_context(messages, max_tokens=4000):
    """コンテキストウィンドウを管理する"""
    total_tokens = estimate_tokens(messages)

    while total_tokens > max_tokens and len(messages) > 2:
        # システムプロンプトは保持、古いメッセージから削除
        if messages[1]["role"] != "system":
            messages.pop(1)
        else:
            messages.pop(2)
        total_tokens = estimate_tokens(messages)

    return messages

def estimate_tokens(messages):
    """メッセージのトークン数を推定"""
    total = 0
    for msg in messages:
        # 日本語は1文字あたり約1.5トークン
        total += int(len(msg["content"]) * 1.5)
    return total
\`\`\`

## 会話の要約

長い会話を要約してコンテキストを圧縮する手法です。

\`\`\`python
def create_summary_prompt(messages):
    """会話を要約するプロンプトを生成"""
    conversation = ""
    for msg in messages:
        role = "ユーザー" if msg["role"] == "user" else "アシスタント"
        conversation += f"{role}: {msg['content']}\\n"

    return f"""
以下の会話を簡潔に要約してください。
重要なポイントと決定事項を含めてください。

{conversation}

要約:"""
\`\`\`

## システムプロンプトの設計

チャットボットの性格と能力を定義します。

\`\`\`python
system_prompts = {
    "customer_support": """あなたはECサイトのカスタマーサポートです。
以下のルールに従ってください：
- 丁寧な敬語を使う
- 問い合わせ内容を正確に把握する
- 解決できない場合は人間のオペレーターに引き継ぐ旨を伝える
- 個人情報は聞かない""",

    "code_assistant": """あなたはプログラミングアシスタントです。
以下のルールに従ってください：
- コードは必ず実行可能な形で提供する
- エラーの原因と解決策を明確に説明する
- ベストプラクティスを推奨する
- セキュリティ上の注意点があれば警告する""",

    "tutor": """あなたは優しい家庭教師です。
以下のルールに従ってください：
- 生徒の理解度に合わせて説明する
- すぐに答えを教えず、ヒントを出す
- 正解したら褒める
- 間違いを恐れない雰囲気を作る"""
}
\`\`\`

## エラーハンドリングとフォールバック

\`\`\`python
def safe_chat_response(user_input, chat_history):
    """安全なチャット応答処理"""
    # 入力バリデーション
    if not user_input or len(user_input.strip()) == 0:
        return "メッセージを入力してください。"

    if len(user_input) > 5000:
        return "メッセージが長すぎます。短くしてお送りください。"

    # 不適切なコンテンツのフィルタリング
    # （実際にはモデレーションAPIを使用）

    try:
        response = get_ai_response(chat_history)
        return response
    except RateLimitError:
        return "現在混み合っています。しばらくしてからお試しください。"
    except Exception:
        return "エラーが発生しました。再度お試しください。"
\`\`\`

## 機能の拡張

### ストリーミング応答
リアルタイムで文字を表示して、ユーザー体験を向上させます。

### ツール呼び出し（Function Calling）
外部APIやデータベースと連携して、より高機能なボットを実現します。

### メモリシステム
過去の会話から重要な情報を長期的に記憶します。

## まとめ

チャットボットの構築には、会話履歴の管理、コンテキストウィンドウの制御、適切なシステムプロンプトの設計が重要です。エラーハンドリングとユーザー体験にも配慮することで、実用的なチャットボットを作ることができます。
`;
