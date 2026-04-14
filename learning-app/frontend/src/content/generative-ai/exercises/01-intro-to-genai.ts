import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "genai-01-token-counter",
    title: "トークン数を推定する関数を作ろう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# テキストのトークン数を推定する関数を作成してください。
# ルール:
# - 英単語（アルファベットの連続）は1トークン
# - 日本語の文字は1文字あたり1.5トークン（切り上げ）
# - 数字の連続は1トークン
# - スペースや句読点は0.5トークン（切り上げ）
import math

def estimate_tokens(text: str) -> int:
    """テキストのトークン数を推定する"""
    # ここにコードを書いてください
    pass

# テスト
print(estimate_tokens("Hello World"))
print(estimate_tokens("生成AIは素晴らしい"))
print(estimate_tokens("Python 3.12"))
`,
    solutionCode: `import math

def estimate_tokens(text: str) -> int:
    """テキストのトークン数を推定する"""
    tokens = 0
    i = 0
    while i < len(text):
        char = text[i]
        # 英字: 連続する英字を1トークンとカウント
        if char.isascii() and char.isalpha():
            while i < len(text) and text[i].isascii() and text[i].isalpha():
                i += 1
            tokens += 1
        # 数字: 連続する数字を1トークンとカウント
        elif char.isdigit() or (char == '.' and i + 1 < len(text) and text[i + 1].isdigit()):
            while i < len(text) and (text[i].isdigit() or text[i] == '.'):
                i += 1
            tokens += 1
        # 日本語文字
        elif not char.isascii():
            tokens += 1.5
            i += 1
        # スペースや句読点
        else:
            tokens += 0.5
            i += 1
    return math.ceil(tokens)

# テスト
print(estimate_tokens("Hello World"))
print(estimate_tokens("生成AIは素晴らしい"))
print(estimate_tokens("Python 3.12"))
`,
    hints: [
      "文字列を1文字ずつ走査しましょう",
      "isascii()とisalpha()で英字を判定できます",
      "日本語文字はnot char.isascii()で判定できます",
      "math.ceil()で切り上げができます",
    ],
    testCases: [
      {
        id: "tc1",
        description: "英語テキスト 'Hello World' のトークン推定",
        type: "stdout",
        expected: "3",
      },
    ],
  },
  {
    id: "genai-01-ai-category",
    title: "AI技術を分類する辞書を作ろう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# AI技術をカテゴリ別に分類する辞書を作成してください。
# 以下の技術を適切なカテゴリに分類してください:
# 技術リスト: "ChatGPT", "DALL-E", "Stable Diffusion", "Claude",
#            "GitHub Copilot", "Whisper", "Midjourney", "GPT-4",
#            "Codex", "Gemini"
#
# カテゴリ:
# - "テキスト生成": テキストを生成するAI
# - "画像生成": 画像を生成するAI
# - "コード生成": コードを生成するAI
# - "音声処理": 音声を処理するAI

def classify_ai_technologies():
    """AI技術をカテゴリ別に分類した辞書を返す"""
    # ここにコードを書いてください
    pass

result = classify_ai_technologies()
for category, techs in sorted(result.items()):
    print(f"{category}: {', '.join(sorted(techs))}")
`,
    solutionCode: `def classify_ai_technologies():
    """AI技術をカテゴリ別に分類した辞書を返す"""
    return {
        "テキスト生成": ["ChatGPT", "Claude", "GPT-4", "Gemini"],
        "画像生成": ["DALL-E", "Stable Diffusion", "Midjourney"],
        "コード生成": ["GitHub Copilot", "Codex"],
        "音声処理": ["Whisper"],
    }

result = classify_ai_technologies()
for category, techs in sorted(result.items()):
    print(f"{category}: {', '.join(sorted(techs))}")
`,
    hints: [
      "辞書のキーはカテゴリ名、値は技術名のリストです",
      "ChatGPT、Claude、GPT-4、Geminiはテキスト生成です",
      "DALL-E、Stable Diffusion、Midjourneyは画像生成です",
      "GitHub CopilotとCodexはコード生成です",
    ],
    testCases: [
      {
        id: "tc2",
        description: "AI技術が正しく分類されていること",
        type: "custom",
        checkCode: `
result = classify_ai_technologies()
assert isinstance(result, dict), "辞書を返してください"
assert len(result) == 4, "4つのカテゴリが必要です"
assert "テキスト生成" in result, "テキスト生成カテゴリがありません"
assert "ChatGPT" in result["テキスト生成"], "ChatGPTはテキスト生成です"
assert "DALL-E" in result["画像生成"], "DALL-Eは画像生成です"
assert "Whisper" in result["音声処理"], "Whisperは音声処理です"
print("PASS")
`,
      },
    ],
  },
];
