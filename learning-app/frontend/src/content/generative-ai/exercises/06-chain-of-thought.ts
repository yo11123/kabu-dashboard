import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "genai-06-cot-prompt-builder",
    title: "Chain of Thoughtプロンプトを構築しよう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# Chain of Thought (CoT) プロンプトを構築する関数を作成してください。
# 問題を分析し、推論ステップを含むプロンプトを生成します。

def build_cot_prompt(question: str, thinking_steps: list = None) -> str:
    """
    CoTプロンプトを構築する。

    thinking_stepsが指定された場合（Few-shot CoT）:
    ---
    問題: {question}

    以下のステップで考えてみましょう。

    ステップ1: {step1}
    ステップ2: {step2}
    ...

    答え:
    ---

    thinking_stepsが未指定の場合（Zero-shot CoT）:
    ---
    問題: {question}

    ステップバイステップで考えてみましょう。

    答え:
    ---
    """
    # ここにコードを書いてください
    pass

def build_self_consistency_prompts(question: str, num_paths: int = 3) -> list:
    """
    Self-Consistency用に複数の異なるCoTプロンプトを生成する。
    各プロンプトは異なるアプローチを指示する。

    アプローチリスト（num_pathsの数だけ使用）:
    - "直感的に考える"
    - "数学的に考える"
    - "具体例を使って考える"
    - "逆から考える"
    - "図を描いて考える"

    形式:
    ---
    問題: {question}

    {approach}アプローチでステップバイステップに解いてください。

    推論:
    ---
    """
    # ここにコードを書いてください
    pass

# テスト
print("=== Zero-shot CoT ===")
prompt1 = build_cot_prompt("100円の商品を3つ買い、500円払いました。おつりはいくらですか？")
print(prompt1)

print("\\n=== Few-shot CoT ===")
prompt2 = build_cot_prompt(
    "200円の商品を2つ買い、1000円払いました。おつりはいくらですか？",
    thinking_steps=[
        "商品の合計金額を計算する: 200円 × 2 = 400円",
        "おつりを計算する: 1000円 - 400円 = 600円"
    ]
)
print(prompt2)

print("\\n=== Self-Consistency ===")
prompts = build_self_consistency_prompts("12の約数をすべて求めてください", num_paths=3)
for i, p in enumerate(prompts):
    print(f"--- パス{i+1} ---")
    print(p)
`,
    solutionCode: `def build_cot_prompt(question: str, thinking_steps: list = None) -> str:
    """CoTプロンプトを構築する"""
    parts = [f"問題: {question}"]

    if thinking_steps:
        parts.append("以下のステップで考えてみましょう。")
        for i, step in enumerate(thinking_steps, 1):
            parts.append(f"ステップ{i}: {step}")
    else:
        parts.append("ステップバイステップで考えてみましょう。")

    parts.append("答え:")

    return "\\n\\n".join(parts)

def build_self_consistency_prompts(question: str, num_paths: int = 3) -> list:
    """Self-Consistency用に複数の異なるCoTプロンプトを生成する"""
    approaches = [
        "直感的に考える",
        "数学的に考える",
        "具体例を使って考える",
        "逆から考える",
        "図を描いて考える",
    ]

    prompts = []
    for i in range(min(num_paths, len(approaches))):
        prompt = f"問題: {question}\\n\\n{approaches[i]}アプローチでステップバイステップに解いてください。\\n\\n推論:"
        prompts.append(prompt)

    return prompts

# テスト
print("=== Zero-shot CoT ===")
prompt1 = build_cot_prompt("100円の商品を3つ買い、500円払いました。おつりはいくらですか？")
print(prompt1)

print("\\n=== Few-shot CoT ===")
prompt2 = build_cot_prompt(
    "200円の商品を2つ買い、1000円払いました。おつりはいくらですか？",
    thinking_steps=[
        "商品の合計金額を計算する: 200円 × 2 = 400円",
        "おつりを計算する: 1000円 - 400円 = 600円"
    ]
)
print(prompt2)

print("\\n=== Self-Consistency ===")
prompts = build_self_consistency_prompts("12の約数をすべて求めてください", num_paths=3)
for i, p in enumerate(prompts):
    print(f"--- パス{i+1} ---")
    print(p)
`,
    hints: [
      "thinking_stepsがNoneかどうかで分岐しましょう",
      "enumerate()でステップ番号を付けられます",
      "Self-Consistencyではアプローチリストからnum_paths個を使います",
      "各パーツは'\\n\\n'で結合します",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
# Zero-shot CoT
p1 = build_cot_prompt("テスト問題")
assert "問題: テスト問題" in p1, "問題が含まれていません"
assert "ステップバイステップ" in p1, "Zero-shotの指示がありません"
assert "答え:" in p1, "答えプレースホルダーがありません"

# Few-shot CoT
p2 = build_cot_prompt("テスト", ["ステップA", "ステップB"])
assert "ステップ1: ステップA" in p2, "ステップ1が正しくありません"
assert "ステップ2: ステップB" in p2, "ステップ2が正しくありません"

# Self-Consistency
prompts = build_self_consistency_prompts("問題X", 3)
assert len(prompts) == 3, f"3つのプロンプトが必要です: {len(prompts)}"
assert all("問題X" in p for p in prompts), "各プロンプトに問題が含まれていません"
assert all("推論:" in p for p in prompts), "各プロンプトに推論が含まれていません"
print("PASS")
`,
      },
    ],
  },
  {
    id: "genai-06-step-parser",
    title: "推論ステップをパースしよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# LLMが返したCoT推論のテキストをパースして、
# 各ステップと最終回答を抽出する関数を作成してください。

def parse_cot_response(response: str) -> dict:
    """
    CoT推論のレスポンスをパースする。

    入力例:
    "ステップ1: まず合計を計算します。100 × 3 = 300
     ステップ2: おつりを計算します。500 - 300 = 200
     答え: 200円"

    戻り値:
    {
        "steps": [
            {"number": 1, "content": "まず合計を計算します。100 × 3 = 300"},
            {"number": 2, "content": "おつりを計算します。500 - 300 = 200"}
        ],
        "answer": "200円",
        "num_steps": 2
    }

    「ステップN:」で始まる行をステップとして抽出。
    「答え:」で始まる行を最終回答として抽出。
    どちらも見つからない場合は空リスト/空文字列とする。
    """
    # ここにコードを書いてください
    pass

# テスト
response1 = """ステップ1: 商品の合計を計算します。100円 × 3 = 300円
ステップ2: おつりを計算します。500円 - 300円 = 200円
答え: 200円"""

result1 = parse_cot_response(response1)
print(f"ステップ数: {result1['num_steps']}")
for step in result1["steps"]:
    print(f"  ステップ{step['number']}: {step['content']}")
print(f"答え: {result1['answer']}")

print()

response2 = """まず最初に考えると、12を割り切れる数を探します。
ステップ1: 1と12
ステップ2: 2と6
ステップ3: 3と4
答え: 1, 2, 3, 4, 6, 12"""

result2 = parse_cot_response(response2)
print(f"ステップ数: {result2['num_steps']}")
print(f"答え: {result2['answer']}")
`,
    solutionCode: `def parse_cot_response(response: str) -> dict:
    """CoT推論のレスポンスをパースする"""
    steps = []
    answer = ""

    lines = response.strip().split("\\n")

    for line in lines:
        line = line.strip()

        # ステップの検出
        if line.startswith("ステップ"):
            # "ステップN: 内容" の形式をパース
            colon_idx = line.index(":")
            step_part = line[:colon_idx]
            content = line[colon_idx + 1:].strip()

            # ステップ番号を抽出
            number = int("".join(c for c in step_part if c.isdigit()))
            steps.append({"number": number, "content": content})

        # 答えの検出
        elif line.startswith("答え:") or line.startswith("答え："):
            answer = line.split(":", 1)[-1].split("：", 1)[-1].strip()

    return {
        "steps": steps,
        "answer": answer,
        "num_steps": len(steps)
    }

# テスト
response1 = """ステップ1: 商品の合計を計算します。100円 × 3 = 300円
ステップ2: おつりを計算します。500円 - 300円 = 200円
答え: 200円"""

result1 = parse_cot_response(response1)
print(f"ステップ数: {result1['num_steps']}")
for step in result1["steps"]:
    print(f"  ステップ{step['number']}: {step['content']}")
print(f"答え: {result1['answer']}")

print()

response2 = """まず最初に考えると、12を割り切れる数を探します。
ステップ1: 1と12
ステップ2: 2と6
ステップ3: 3と4
答え: 1, 2, 3, 4, 6, 12"""

result2 = parse_cot_response(response2)
print(f"ステップ数: {result2['num_steps']}")
print(f"答え: {result2['answer']}")
`,
    hints: [
      "テキストを行ごとに分割して処理しましょう",
      "startswith()で行の種類を判定できます",
      "ステップ番号はisdigit()で数字を抽出します",
      "コロンの位置はindex(':')で見つけられます",
    ],
    testCases: [
      {
        id: "tc2",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
r = parse_cot_response("ステップ1: A\\nステップ2: B\\n答え: C")
assert r["num_steps"] == 2, f"ステップ数が正しくありません: {r['num_steps']}"
assert r["steps"][0]["number"] == 1, "ステップ1の番号が正しくありません"
assert r["steps"][0]["content"] == "A", "ステップ1の内容が正しくありません"
assert r["steps"][1]["content"] == "B", "ステップ2の内容が正しくありません"
assert r["answer"] == "C", f"答えが正しくありません: {r['answer']}"

r2 = parse_cot_response("関係ないテキスト")
assert r2["num_steps"] == 0, "ステップがない場合は0"
assert r2["answer"] == "", "答えがない場合は空文字列"
print("PASS")
`,
      },
    ],
  },
];
