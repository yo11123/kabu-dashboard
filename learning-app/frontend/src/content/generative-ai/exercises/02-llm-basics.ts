import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "genai-02-temperature-sampling",
    title: "Temperature サンプリングをシミュレーションしよう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# LLMのTemperatureパラメータによるサンプリングをシミュレーションします。
# 各単語の確率が与えられた時、temperatureを適用して
# 確率分布を調整する関数を作成してください。
#
# Temperature の計算:
# 1. 各logit（対数確率）をtemperatureで割る
# 2. softmax関数で確率に変換する
#
# softmax(x_i) = exp(x_i) / sum(exp(x_j) for all j)
import math

def apply_temperature(logits: dict, temperature: float) -> dict:
    """
    logits: {"単語": logit値} の辞書
    temperature: 温度パラメータ (> 0)
    戻り値: {"単語": 確率} の辞書（確率の合計は1.0）
    """
    # ここにコードを書いてください
    pass

# テスト
logits = {"東京": 2.0, "大阪": 1.0, "京都": 0.5, "福岡": 0.1}

print("=== Temperature 0.5 (より決定的) ===")
probs = apply_temperature(logits, 0.5)
for word, prob in sorted(probs.items(), key=lambda x: -x[1]):
    print(f"  {word}: {prob:.4f}")

print("\\n=== Temperature 1.0 (標準) ===")
probs = apply_temperature(logits, 1.0)
for word, prob in sorted(probs.items(), key=lambda x: -x[1]):
    print(f"  {word}: {prob:.4f}")

print("\\n=== Temperature 2.0 (よりランダム) ===")
probs = apply_temperature(logits, 2.0)
for word, prob in sorted(probs.items(), key=lambda x: -x[1]):
    print(f"  {word}: {prob:.4f}")
`,
    solutionCode: `import math

def apply_temperature(logits: dict, temperature: float) -> dict:
    """
    logits: {"単語": logit値} の辞書
    temperature: 温度パラメータ (> 0)
    戻り値: {"単語": 確率} の辞書（確率の合計は1.0）
    """
    # temperatureでlogitsを割る
    scaled = {word: logit / temperature for word, logit in logits.items()}

    # オーバーフロー防止のため最大値を引く
    max_val = max(scaled.values())
    exp_vals = {word: math.exp(val - max_val) for word, val in scaled.items()}

    # softmax: 合計で割って確率にする
    total = sum(exp_vals.values())
    probs = {word: val / total for word, val in exp_vals.items()}

    return probs

# テスト
logits = {"東京": 2.0, "大阪": 1.0, "京都": 0.5, "福岡": 0.1}

print("=== Temperature 0.5 (より決定的) ===")
probs = apply_temperature(logits, 0.5)
for word, prob in sorted(probs.items(), key=lambda x: -x[1]):
    print(f"  {word}: {prob:.4f}")

print("\\n=== Temperature 1.0 (標準) ===")
probs = apply_temperature(logits, 1.0)
for word, prob in sorted(probs.items(), key=lambda x: -x[1]):
    print(f"  {word}: {prob:.4f}")

print("\\n=== Temperature 2.0 (よりランダム) ===")
probs = apply_temperature(logits, 2.0)
for word, prob in sorted(probs.items(), key=lambda x: -x[1]):
    print(f"  {word}: {prob:.4f}")
`,
    hints: [
      "まず各logitをtemperatureで割りましょう",
      "softmax関数: exp(x_i) / sum(exp(x_j))",
      "オーバーフロー防止のため、最大値を引いてからexpを計算すると安全です",
      "最終的な確率の合計が1.0になることを確認しましょう",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
logits = {"A": 2.0, "B": 1.0, "C": 0.0}
probs = apply_temperature(logits, 1.0)
assert isinstance(probs, dict), "辞書を返してください"
assert abs(sum(probs.values()) - 1.0) < 0.001, "確率の合計が1.0ではありません"
assert probs["A"] > probs["B"] > probs["C"], "確率の順序が正しくありません"

# temperature低いと差が大きくなる
probs_low = apply_temperature(logits, 0.1)
assert probs_low["A"] > 0.95, "低いtemperatureでは最大値がほぼ1.0になるべきです"
print("PASS")
`,
      },
    ],
  },
  {
    id: "genai-02-context-window",
    title: "コンテキストウィンドウを管理しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# コンテキストウィンドウ内に収まるようにメッセージを管理する関数を作成してください。
# メッセージのトークン数を推定し、制限を超えた場合は古いメッセージから削除します。
# ただし、systemメッセージ（最初のメッセージ）は常に保持してください。

def estimate_message_tokens(message: dict) -> int:
    """メッセージのトークン数を推定（1文字=1トークンで簡略化）"""
    return len(message["content"])

def trim_messages(messages: list, max_tokens: int) -> list:
    """
    メッセージリストをmax_tokens以内に収める。
    - systemメッセージ（先頭）は常に保持
    - 古いメッセージから削除
    - 戻り値は新しいメッセージリスト
    """
    # ここにコードを書いてください
    pass

# テスト
messages = [
    {"role": "system", "content": "あなたはアシスタントです"},
    {"role": "user", "content": "こんにちは"},
    {"role": "assistant", "content": "こんにちは！何かお手伝いできますか？"},
    {"role": "user", "content": "Pythonについて教えてください"},
    {"role": "assistant", "content": "Pythonは汎用プログラミング言語です。初心者にも学びやすく、データサイエンスやWeb開発で広く使われています。"},
    {"role": "user", "content": "リストの使い方は？"},
]

result = trim_messages(messages, 50)
print(f"元のメッセージ数: {len(messages)}")
print(f"トリム後のメッセージ数: {len(result)}")
print(f"先頭のロール: {result[0]['role']}")
print(f"最後のメッセージ: {result[-1]['content']}")
`,
    solutionCode: `def estimate_message_tokens(message: dict) -> int:
    """メッセージのトークン数を推定（1文字=1トークンで簡略化）"""
    return len(message["content"])

def trim_messages(messages: list, max_tokens: int) -> list:
    """
    メッセージリストをmax_tokens以内に収める。
    - systemメッセージ（先頭）は常に保持
    - 古いメッセージから削除
    - 戻り値は新しいメッセージリスト
    """
    result = messages.copy()

    # 合計トークン数を計算
    total_tokens = sum(estimate_message_tokens(m) for m in result)

    # max_tokensを超えている間、古いメッセージから削除
    while total_tokens > max_tokens and len(result) > 2:
        # インデックス1のメッセージを削除（0はsystem）
        removed = result.pop(1)
        total_tokens -= estimate_message_tokens(removed)

    return result

# テスト
messages = [
    {"role": "system", "content": "あなたはアシスタントです"},
    {"role": "user", "content": "こんにちは"},
    {"role": "assistant", "content": "こんにちは！何かお手伝いできますか？"},
    {"role": "user", "content": "Pythonについて教えてください"},
    {"role": "assistant", "content": "Pythonは汎用プログラミング言語です。初心者にも学びやすく、データサイエンスやWeb開発で広く使われています。"},
    {"role": "user", "content": "リストの使い方は？"},
]

result = trim_messages(messages, 50)
print(f"元のメッセージ数: {len(messages)}")
print(f"トリム後のメッセージ数: {len(result)}")
print(f"先頭のロール: {result[0]['role']}")
print(f"最後のメッセージ: {result[-1]['content']}")
`,
    hints: [
      "まずメッセージリストをコピーしましょう（元のリストを変更しないため）",
      "合計トークン数がmax_tokensを超えている間ループします",
      "result.pop(1)でsystemメッセージの次のメッセージを削除できます",
      "最低限systemメッセージと最新のメッセージは残しましょう",
    ],
    testCases: [
      {
        id: "tc2",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
msgs = [
    {"role": "system", "content": "sys"},
    {"role": "user", "content": "aaaaaa"},
    {"role": "assistant", "content": "bbbbbb"},
    {"role": "user", "content": "cc"},
]
result = trim_messages(msgs, 10)
assert result[0]["role"] == "system", "systemメッセージが保持されていません"
assert result[-1]["content"] == "cc", "最新メッセージが保持されていません"
total = sum(estimate_message_tokens(m) for m in result)
assert total <= 10, f"トークン数が制限を超えています: {total}"
print("PASS")
`,
      },
    ],
  },
];
