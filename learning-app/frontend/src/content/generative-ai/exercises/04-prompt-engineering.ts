import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "genai-04-prompt-template",
    title: "プロンプトテンプレートエンジンを作ろう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# プロンプトテンプレートを管理するクラスを作成してください。
# テンプレート内の {変数名} を実際の値に置換する機能を持ちます。

class PromptTemplate:
    def __init__(self, template: str):
        """
        template: テンプレート文字列（例: "こんにちは、{name}さん"）
        """
        self.template = template

    def get_variables(self) -> list:
        """テンプレート内の変数名をリストで返す（出現順、重複なし）"""
        # ここにコードを書いてください
        pass

    def format(self, **kwargs) -> str:
        """
        テンプレートの変数を指定された値で置換して返す。
        未指定の変数がある場合はValueErrorを発生させる。
        """
        # ここにコードを書いてください
        pass

    def partial(self, **kwargs) -> 'PromptTemplate':
        """
        一部の変数だけを置換した新しいPromptTemplateを返す。
        未指定の変数はそのまま残す。
        """
        # ここにコードを書いてください
        pass

# テスト
template = PromptTemplate(
    "あなたは{role}です。{language}で{task}を実行してください。"
)

print("変数一覧:", template.get_variables())

result = template.format(role="翻訳家", language="日本語", task="翻訳")
print("完成プロンプト:", result)

partial = template.partial(role="プログラマー")
print("部分適用後の変数:", partial.get_variables())
print("部分適用の結果:", partial.format(language="Python", task="コードレビュー"))
`,
    solutionCode: `import re

class PromptTemplate:
    def __init__(self, template: str):
        self.template = template

    def get_variables(self) -> list:
        """テンプレート内の変数名をリストで返す（出現順、重複なし）"""
        variables = []
        for match in re.finditer(r'\\{(\\w+)\\}', self.template):
            name = match.group(1)
            if name not in variables:
                variables.append(name)
        return variables

    def format(self, **kwargs) -> str:
        """テンプレートの変数を指定された値で置換して返す"""
        variables = self.get_variables()
        missing = [v for v in variables if v not in kwargs]
        if missing:
            raise ValueError(f"未指定の変数があります: {missing}")
        result = self.template
        for key, value in kwargs.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    def partial(self, **kwargs) -> 'PromptTemplate':
        """一部の変数だけを置換した新しいPromptTemplateを返す"""
        result = self.template
        for key, value in kwargs.items():
            result = result.replace("{" + key + "}", str(value))
        return PromptTemplate(result)

# テスト
template = PromptTemplate(
    "あなたは{role}です。{language}で{task}を実行してください。"
)

print("変数一覧:", template.get_variables())

result = template.format(role="翻訳家", language="日本語", task="翻訳")
print("完成プロンプト:", result)

partial = template.partial(role="プログラマー")
print("部分適用後の変数:", partial.get_variables())
print("部分適用の結果:", partial.format(language="Python", task="コードレビュー"))
`,
    hints: [
      "正規表現 r'\\{(\\w+)\\}' で変数を検出できます",
      "format()では未指定の変数がないかチェックしましょう",
      "partial()では指定された変数のみ置換し、新しいPromptTemplateを返します",
      "str.replace()で変数を値に置換できます",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
t = PromptTemplate("{greeting}、{name}さん。{greeting}！")
assert t.get_variables() == ["greeting", "name"], f"変数一覧が正しくありません: {t.get_variables()}"
assert t.format(greeting="こんにちは", name="太郎") == "こんにちは、太郎さん。こんにちは！"
try:
    t.format(greeting="こんにちは")
    assert False, "ValueErrorが発生するべきです"
except ValueError:
    pass
p = t.partial(greeting="やあ")
assert p.get_variables() == ["name"], "partial後の変数が正しくありません"
assert p.format(name="花子") == "やあ、花子さん。やあ！"
print("PASS")
`,
      },
    ],
  },
  {
    id: "genai-04-structured-prompt",
    title: "構造化プロンプトを生成しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# 構造化されたプロンプトを生成する関数を作成してください。
# 以下の要素を組み合わせてプロンプトを構築します。

def build_structured_prompt(
    role: str,
    task: str,
    context: str = "",
    constraints: list = None,
    output_format: str = "",
    examples: list = None
) -> str:
    """
    構造化プロンプトを生成する。

    出力形式:
    ## 役割
    あなたは{role}です。

    ## タスク
    {task}

    ## コンテキスト（contextが指定された場合のみ）
    {context}

    ## 制約条件（constraintsが指定された場合のみ）
    - {constraint1}
    - {constraint2}

    ## 出力形式（output_formatが指定された場合のみ）
    {output_format}

    ## 例（examplesが指定された場合のみ）
    例1: {example1}
    例2: {example2}
    """
    # ここにコードを書いてください
    pass

# テスト
prompt = build_structured_prompt(
    role="データ分析の専門家",
    task="与えられたCSVデータを分析してレポートを作成してください",
    context="売上データの月次分析です",
    constraints=["日本語で回答", "グラフの説明を含める", "3ページ以内"],
    output_format="マークダウン形式のレポート",
    examples=["月別売上推移のグラフ付きレポート"]
)
print(prompt)
`,
    solutionCode: `def build_structured_prompt(
    role: str,
    task: str,
    context: str = "",
    constraints: list = None,
    output_format: str = "",
    examples: list = None
) -> str:
    """構造化プロンプトを生成する"""
    parts = []

    parts.append(f"## 役割\\nあなたは{role}です。")
    parts.append(f"## タスク\\n{task}")

    if context:
        parts.append(f"## コンテキスト\\n{context}")

    if constraints:
        constraint_lines = "\\n".join(f"- {c}" for c in constraints)
        parts.append(f"## 制約条件\\n{constraint_lines}")

    if output_format:
        parts.append(f"## 出力形式\\n{output_format}")

    if examples:
        example_lines = "\\n".join(f"例{i+1}: {ex}" for i, ex in enumerate(examples))
        parts.append(f"## 例\\n{example_lines}")

    return "\\n\\n".join(parts)

# テスト
prompt = build_structured_prompt(
    role="データ分析の専門家",
    task="与えられたCSVデータを分析してレポートを作成してください",
    context="売上データの月次分析です",
    constraints=["日本語で回答", "グラフの説明を含める", "3ページ以内"],
    output_format="マークダウン形式のレポート",
    examples=["月別売上推移のグラフ付きレポート"]
)
print(prompt)
`,
    hints: [
      "各セクションを文字列のリストに追加していきましょう",
      "オプション要素はif文で存在チェックしてから追加します",
      "制約条件は'- 'プレフィックス付きのリスト形式にします",
      "最後に'\\n\\n'.join()で全セクションを結合します",
    ],
    testCases: [
      {
        id: "tc2",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
p = build_structured_prompt(role="翻訳家", task="翻訳して")
assert "## 役割" in p, "役割セクションがありません"
assert "翻訳家" in p, "役割が含まれていません"
assert "## タスク" in p, "タスクセクションがありません"
assert "## コンテキスト" not in p, "空のコンテキストは含めないでください"

p2 = build_structured_prompt(role="X", task="Y", constraints=["A", "B"])
assert "- A" in p2, "制約条件のフォーマットが正しくありません"
assert "- B" in p2, "制約条件のフォーマットが正しくありません"
print("PASS")
`,
      },
    ],
  },
];
