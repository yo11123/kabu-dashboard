import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "genai-03-build-request",
    title: "Chat Completions APIリクエストを構築しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `import json

# OpenAI Chat Completions APIのリクエストボディを構築する関数を作成してください。
# 引数:
#   model: モデル名 (str)
#   system_prompt: システムプロンプト (str)
#   user_message: ユーザーメッセージ (str)
#   temperature: 温度 (float, デフォルト0.7)
#   max_tokens: 最大トークン数 (int, デフォルト500)
# 戻り値: APIリクエストボディの辞書

def build_chat_request(
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float = 0.7,
    max_tokens: int = 500
) -> dict:
    """Chat Completions APIのリクエストボディを構築する"""
    # ここにコードを書いてください
    pass

# テスト
request = build_chat_request(
    model="gpt-4",
    system_prompt="あなたはPythonの専門家です。",
    user_message="リスト内包表記について教えてください。"
)
print(json.dumps(request, ensure_ascii=False, indent=2))
`,
    solutionCode: `import json

def build_chat_request(
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float = 0.7,
    max_tokens: int = 500
) -> dict:
    """Chat Completions APIのリクエストボディを構築する"""
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

# テスト
request = build_chat_request(
    model="gpt-4",
    system_prompt="あなたはPythonの専門家です。",
    user_message="リスト内包表記について教えてください。"
)
print(json.dumps(request, ensure_ascii=False, indent=2))
`,
    hints: [
      "辞書を返す関数を作りましょう",
      "messagesはsystemとuserの2つのメッセージを含むリストです",
      "各メッセージは'role'と'content'キーを持つ辞書です",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
req = build_chat_request("gpt-4", "system msg", "user msg", 0.5, 100)
assert req["model"] == "gpt-4", "modelが正しくありません"
assert len(req["messages"]) == 2, "messagesは2つ必要です"
assert req["messages"][0]["role"] == "system", "最初のメッセージはsystemです"
assert req["messages"][1]["role"] == "user", "2番目のメッセージはuserです"
assert req["temperature"] == 0.5, "temperatureが正しくありません"
assert req["max_tokens"] == 100, "max_tokensが正しくありません"
print("PASS")
`,
      },
    ],
  },
  {
    id: "genai-03-parse-response",
    title: "APIレスポンスをパースしよう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `import json

# OpenAI APIのモックレスポンスをパースして必要な情報を抽出する関数を作成してください。

MOCK_RESPONSE = json.dumps({
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1677858242,
    "model": "gpt-4",
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Pythonのリスト内包表記は、既存のリストから新しいリストを簡潔に作成するための構文です。"
            },
            "finish_reason": "stop",
            "index": 0
        }
    ],
    "usage": {
        "prompt_tokens": 45,
        "completion_tokens": 32,
        "total_tokens": 77
    }
})

def parse_chat_response(response_json: str) -> dict:
    """
    APIレスポンスをパースして以下の情報を返す:
    - content: アシスタントの応答テキスト
    - model: 使用されたモデル名
    - finish_reason: 終了理由
    - prompt_tokens: プロンプトのトークン数
    - completion_tokens: 応答のトークン数
    - total_tokens: 合計トークン数
    - estimated_cost: 推定コスト（USD）
      GPT-4: 入力 $0.03/1Kトークン、出力 $0.06/1Kトークン
    """
    # ここにコードを書いてください
    pass

# テスト
result = parse_chat_response(MOCK_RESPONSE)
for key, value in result.items():
    print(f"{key}: {value}")
`,
    solutionCode: `import json

MOCK_RESPONSE = json.dumps({
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1677858242,
    "model": "gpt-4",
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Pythonのリスト内包表記は、既存のリストから新しいリストを簡潔に作成するための構文です。"
            },
            "finish_reason": "stop",
            "index": 0
        }
    ],
    "usage": {
        "prompt_tokens": 45,
        "completion_tokens": 32,
        "total_tokens": 77
    }
})

def parse_chat_response(response_json: str) -> dict:
    """APIレスポンスをパースして必要な情報を返す"""
    data = json.loads(response_json)

    choice = data["choices"][0]
    usage = data["usage"]

    prompt_tokens = usage["prompt_tokens"]
    completion_tokens = usage["completion_tokens"]

    # GPT-4の料金計算
    estimated_cost = (prompt_tokens / 1000 * 0.03) + (completion_tokens / 1000 * 0.06)

    return {
        "content": choice["message"]["content"],
        "model": data["model"],
        "finish_reason": choice["finish_reason"],
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": usage["total_tokens"],
        "estimated_cost": round(estimated_cost, 6)
    }

# テスト
result = parse_chat_response(MOCK_RESPONSE)
for key, value in result.items():
    print(f"{key}: {value}")
`,
    hints: [
      "json.loads()でJSON文字列を辞書に変換しましょう",
      "応答テキストはchoices[0]['message']['content']にあります",
      "トークン数はusageフィールドにあります",
      "コスト計算: (入力トークン/1000 * 0.03) + (出力トークン/1000 * 0.06)",
    ],
    testCases: [
      {
        id: "tc2",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
result = parse_chat_response(MOCK_RESPONSE)
assert "content" in result, "contentが必要です"
assert result["model"] == "gpt-4", "modelが正しくありません"
assert result["finish_reason"] == "stop", "finish_reasonが正しくありません"
assert result["prompt_tokens"] == 45, "prompt_tokensが正しくありません"
assert result["completion_tokens"] == 32, "completion_tokensが正しくありません"
assert result["total_tokens"] == 77, "total_tokensが正しくありません"
expected_cost = (45 / 1000 * 0.03) + (32 / 1000 * 0.06)
assert abs(result["estimated_cost"] - round(expected_cost, 6)) < 0.0001, "コスト計算が正しくありません"
print("PASS")
`,
      },
    ],
  },
];
