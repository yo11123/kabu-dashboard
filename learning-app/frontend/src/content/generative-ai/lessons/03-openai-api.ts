export const content = `
# OpenAI API

## OpenAI APIとは

OpenAI APIは、GPTシリーズのモデルをプログラムから利用するためのインターフェースです。REST APIを通じて、テキスト生成、画像生成、音声処理などの機能にアクセスできます。

## APIの基本構造

### エンドポイント
主要なエンドポイントは以下の通りです：

| エンドポイント | 用途 |
|--------------|------|
| /v1/chat/completions | チャット形式のテキスト生成 |
| /v1/embeddings | テキストのベクトル化 |
| /v1/images/generations | 画像生成 |
| /v1/audio/transcriptions | 音声認識 |

## Chat Completions API

最もよく使われるAPIです。チャット形式でLLMと対話できます。

### リクエスト形式

\`\`\`python
import json

# APIリクエストの構造
request_body = {
    "model": "gpt-4",
    "messages": [
        {"role": "system", "content": "あなたは親切なアシスタントです。"},
        {"role": "user", "content": "Pythonの特徴を3つ教えてください。"}
    ],
    "temperature": 0.7,
    "max_tokens": 500
}

print(json.dumps(request_body, ensure_ascii=False, indent=2))
\`\`\`

### メッセージロール

- **system**: AIの振る舞いを設定する
- **user**: ユーザーからの入力
- **assistant**: AIの応答

### レスポンス形式

\`\`\`python
# APIレスポンスの構造
response = {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1677858242,
    "model": "gpt-4",
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Pythonの特徴は..."
            },
            "finish_reason": "stop",
            "index": 0
        }
    ],
    "usage": {
        "prompt_tokens": 30,
        "completion_tokens": 150,
        "total_tokens": 180
    }
}
\`\`\`

## 主要なパラメータ

### temperature
出力のランダム性を制御します（0.0〜2.0）。

### max_tokens
生成するトークンの最大数を指定します。

### top_p
確率の上位p%のトークンからサンプリングします。

### frequency_penalty
同じ単語の繰り返しを抑制します（-2.0〜2.0）。

### presence_penalty
新しいトピックへの移行を促進します（-2.0〜2.0）。

## トークン数とコスト

APIの利用はトークン数に基づいて課金されます。

\`\`\`python
# トークン数の見積もり
# 日本語: 1文字 ≒ 1〜3トークン
# 英語: 1単語 ≒ 1トークン

text = "東京タワーは東京都港区にある電波塔です"
estimated_tokens = len(text) * 1.5  # 日本語の大まかな見積もり
print(f"推定トークン数: {estimated_tokens:.0f}")
\`\`\`

## エラーハンドリング

APIを使う際は適切なエラーハンドリングが重要です。

\`\`\`python
# よくあるエラーコード
error_codes = {
    401: "認証エラー - APIキーが無効",
    429: "レート制限 - リクエストが多すぎる",
    500: "サーバーエラー - OpenAI側の問題",
    503: "サービス利用不可 - メンテナンス中"
}

for code, desc in error_codes.items():
    print(f"HTTP {code}: {desc}")
\`\`\`

## ベストプラクティス

1. **APIキーの安全管理**: 環境変数を使用し、コードに直接書かない
2. **レート制限の考慮**: リトライロジックを実装する
3. **コスト管理**: max_tokensを適切に設定する
4. **エラーハンドリング**: 適切な例外処理を行う

## まとめ

OpenAI APIはシンプルなREST APIで、テキスト生成をプログラムに組み込むことができます。メッセージロール、パラメータの意味、コスト管理を理解することで、効率的にAPIを活用できます。
`;
