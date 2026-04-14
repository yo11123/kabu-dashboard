import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "genai-05-few-shot-builder",
    title: "Few-shotプロンプトビルダーを作ろう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# Few-shotプロンプトを構築するクラスを作成してください。
# 例（shot）を追加し、最終的なプロンプトを生成する機能を持ちます。

class FewShotBuilder:
    def __init__(self, task_description: str, input_label: str = "入力", output_label: str = "出力"):
        """
        task_description: タスクの説明
        input_label: 入力のラベル名
        output_label: 出力のラベル名
        """
        self.task_description = task_description
        self.input_label = input_label
        self.output_label = output_label
        self.examples = []

    def add_example(self, input_text: str, output_text: str) -> 'FewShotBuilder':
        """例を追加する（メソッドチェーン対応）"""
        # ここにコードを書いてください
        pass

    def build(self, query: str) -> str:
        """
        Few-shotプロンプトを生成する。
        形式:
        {task_description}

        {input_label}: {example1_input}
        {output_label}: {example1_output}

        {input_label}: {example2_input}
        {output_label}: {example2_output}

        {input_label}: {query}
        {output_label}:
        """
        # ここにコードを書いてください
        pass

    def get_shot_count(self) -> int:
        """現在の例の数を返す"""
        # ここにコードを書いてください
        pass

# テスト: 感情分析のFew-shotプロンプト
builder = FewShotBuilder(
    "以下のテキストの感情を「ポジティブ」「ネガティブ」「ニュートラル」のいずれかに分類してください。",
    input_label="テキスト",
    output_label="感情"
)

prompt = (builder
    .add_example("この映画は最高でした！", "ポジティブ")
    .add_example("サービスが最悪だった", "ネガティブ")
    .add_example("普通の品質でした", "ニュートラル")
    .build("新しいレストランがとても美味しかった"))

print(f"例の数: {builder.get_shot_count()}")
print("---")
print(prompt)
`,
    solutionCode: `class FewShotBuilder:
    def __init__(self, task_description: str, input_label: str = "入力", output_label: str = "出力"):
        self.task_description = task_description
        self.input_label = input_label
        self.output_label = output_label
        self.examples = []

    def add_example(self, input_text: str, output_text: str) -> 'FewShotBuilder':
        """例を追加する（メソッドチェーン対応）"""
        self.examples.append({"input": input_text, "output": output_text})
        return self

    def build(self, query: str) -> str:
        """Few-shotプロンプトを生成する"""
        parts = [self.task_description]

        for ex in self.examples:
            parts.append(f"{self.input_label}: {ex['input']}\\n{self.output_label}: {ex['output']}")

        parts.append(f"{self.input_label}: {query}\\n{self.output_label}:")

        return "\\n\\n".join(parts)

    def get_shot_count(self) -> int:
        """現在の例の数を返す"""
        return len(self.examples)

# テスト: 感情分析のFew-shotプロンプト
builder = FewShotBuilder(
    "以下のテキストの感情を「ポジティブ」「ネガティブ」「ニュートラル」のいずれかに分類してください。",
    input_label="テキスト",
    output_label="感情"
)

prompt = (builder
    .add_example("この映画は最高でした！", "ポジティブ")
    .add_example("サービスが最悪だった", "ネガティブ")
    .add_example("普通の品質でした", "ニュートラル")
    .build("新しいレストランがとても美味しかった"))

print(f"例の数: {builder.get_shot_count()}")
print("---")
print(prompt)
`,
    hints: [
      "add_example()ではselfを返すことでメソッドチェーンが可能になります",
      "build()ではタスク説明、例、クエリを順番に組み立てます",
      "各セクションは空行（\\n\\n）で区切ります",
      "最後のクエリの出力ラベルの後にはコロンだけ付けます",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
b = FewShotBuilder("分類してください", "IN", "OUT")
b.add_example("a", "1").add_example("b", "2")
assert b.get_shot_count() == 2, "例の数が正しくありません"
prompt = b.build("c")
assert "分類してください" in prompt, "タスク説明が含まれていません"
assert "IN: a\\nOUT: 1" in prompt, "例1のフォーマットが正しくありません"
assert "IN: b\\nOUT: 2" in prompt, "例2のフォーマットが正しくありません"
assert prompt.endswith("IN: c\\nOUT:"), f"クエリ部分が正しくありません: '{prompt[-20:]}'"
print("PASS")
`,
      },
    ],
  },
  {
    id: "genai-05-mock-classifier",
    title: "Few-shotベースのモック分類器を作ろう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# Few-shotの例を使って、簡単なキーワードベースの分類器を作成してください。
# LLMの代わりに、キーワードマッチングで分類を行います。

class MockFewShotClassifier:
    def __init__(self):
        self.examples = []

    def add_example(self, text: str, label: str):
        """学習例を追加する"""
        self.examples.append({"text": text, "label": label})

    def _extract_keywords(self, text: str) -> set:
        """テキストからキーワード（文字のバイグラム）を抽出する"""
        # 2文字ずつのバイグラムを抽出
        # 例: "美味しい" → {"美味", "味し", "しい"}
        # ここにコードを書いてください
        pass

    def _similarity(self, text1: str, text2: str) -> float:
        """2つのテキストのJaccard類似度を計算する"""
        # Jaccard類似度 = 共通要素数 / 全要素数
        # ここにコードを書いてください
        pass

    def classify(self, text: str) -> dict:
        """
        テキストを分類する。各例との類似度を計算し、
        最も類似度の高い例のラベルを返す。
        戻り値: {"label": 分類ラベル, "confidence": 最大類似度, "scores": 全ラベルのスコア辞書}
        """
        # ここにコードを書いてください
        pass

# テスト
classifier = MockFewShotClassifier()
classifier.add_example("この映画は面白くて最高でした", "ポジティブ")
classifier.add_example("素晴らしい料理で大満足です", "ポジティブ")
classifier.add_example("サービスが悪くて不満です", "ネガティブ")
classifier.add_example("対応が遅くて困りました", "ネガティブ")
classifier.add_example("普通のサービスでした", "ニュートラル")

test_texts = [
    "この料理は最高に美味しかった",
    "対応が悪くて不満だった",
    "普通の映画でした",
]

for text in test_texts:
    result = classifier.classify(text)
    print(f"テキスト: {text}")
    print(f"  分類: {result['label']} (信頼度: {result['confidence']:.3f})")
    print()
`,
    solutionCode: `class MockFewShotClassifier:
    def __init__(self):
        self.examples = []

    def add_example(self, text: str, label: str):
        """学習例を追加する"""
        self.examples.append({"text": text, "label": label})

    def _extract_keywords(self, text: str) -> set:
        """テキストからキーワード（文字のバイグラム）を抽出する"""
        bigrams = set()
        for i in range(len(text) - 1):
            bigrams.add(text[i:i+2])
        return bigrams

    def _similarity(self, text1: str, text2: str) -> float:
        """2つのテキストのJaccard類似度を計算する"""
        set1 = self._extract_keywords(text1)
        set2 = self._extract_keywords(text2)
        if not set1 and not set2:
            return 0.0
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union) if union else 0.0

    def classify(self, text: str) -> dict:
        """テキストを分類する"""
        # 各例との類似度を計算
        label_scores = {}
        for ex in self.examples:
            sim = self._similarity(text, ex["text"])
            label = ex["label"]
            if label not in label_scores or sim > label_scores[label]:
                label_scores[label] = sim

        # 最大類似度のラベルを選択
        best_label = max(label_scores, key=label_scores.get)
        best_score = label_scores[best_label]

        return {
            "label": best_label,
            "confidence": best_score,
            "scores": label_scores
        }

# テスト
classifier = MockFewShotClassifier()
classifier.add_example("この映画は面白くて最高でした", "ポジティブ")
classifier.add_example("素晴らしい料理で大満足です", "ポジティブ")
classifier.add_example("サービスが悪くて不満です", "ネガティブ")
classifier.add_example("対応が遅くて困りました", "ネガティブ")
classifier.add_example("普通のサービスでした", "ニュートラル")

test_texts = [
    "この料理は最高に美味しかった",
    "対応が悪くて不満だった",
    "普通の映画でした",
]

for text in test_texts:
    result = classifier.classify(text)
    print(f"テキスト: {text}")
    print(f"  分類: {result['label']} (信頼度: {result['confidence']:.3f})")
    print()
`,
    hints: [
      "バイグラム: text[i:i+2]で2文字ずつ取り出します",
      "Jaccard類似度: len(A & B) / len(A | B)",
      "各ラベルについて最大類似度を保持しましょう",
      "max()のkey引数でdict.getを使うと最大値のキーが取れます",
    ],
    testCases: [
      {
        id: "tc2",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
c = MockFewShotClassifier()
c.add_example("嬉しい楽しい", "positive")
c.add_example("悲しい辛い", "negative")
r = c.classify("嬉しい気持ち")
assert r["label"] == "positive", f"分類が正しくありません: {r['label']}"
assert "confidence" in r, "confidenceが必要です"
assert "scores" in r, "scoresが必要です"
assert isinstance(r["scores"], dict), "scoresは辞書であるべきです"
r2 = c.classify("悲しい気持ち")
assert r2["label"] == "negative", f"分類が正しくありません: {r2['label']}"
print("PASS")
`,
      },
    ],
  },
];
