import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "genai-07-cosine-similarity",
    title: "コサイン類似度を実装しよう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `import math

# コサイン類似度を計算し、テキスト間の類似度を比較する機能を実装してください。

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """
    2つのベクトルのコサイン類似度を計算する。
    cosine_similarity = dot(a, b) / (|a| * |b|)

    vec_aとvec_bの長さが異なる場合はValueErrorを発生させる。
    ゼロベクトルの場合は0.0を返す。
    """
    # ここにコードを書いてください
    pass

def find_most_similar(query_vec: list, candidates: dict) -> list:
    """
    クエリベクトルに最も類似した候補を返す。
    candidates: {"名前": [ベクトル], ...}
    戻り値: [("名前", 類似度), ...] を類似度の降順でソート
    """
    # ここにコードを書いてください
    pass

# テスト: 簡易エンベディング（手動で作った小さなベクトル）
# 実際のエンベディングは1536次元ですが、ここでは5次元で簡略化
embeddings = {
    "Python入門": [0.9, 0.8, 0.1, 0.2, 0.1],
    "JavaScript基礎": [0.8, 0.7, 0.2, 0.1, 0.1],
    "料理レシピ": [0.1, 0.1, 0.9, 0.8, 0.7],
    "お菓子の作り方": [0.1, 0.2, 0.8, 0.9, 0.8],
    "機械学習入門": [0.9, 0.7, 0.1, 0.3, 0.2],
}

query = [0.85, 0.75, 0.15, 0.25, 0.1]  # プログラミング系のクエリ
print("クエリ: プログラミング系")
results = find_most_similar(query, embeddings)
for name, sim in results:
    print(f"  {name}: {sim:.4f}")

print()
query2 = [0.1, 0.15, 0.85, 0.85, 0.75]  # 料理系のクエリ
print("クエリ: 料理系")
results2 = find_most_similar(query2, embeddings)
for name, sim in results2:
    print(f"  {name}: {sim:.4f}")
`,
    solutionCode: `import math

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """2つのベクトルのコサイン類似度を計算する"""
    if len(vec_a) != len(vec_b):
        raise ValueError("ベクトルの長さが異なります")

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)

def find_most_similar(query_vec: list, candidates: dict) -> list:
    """クエリベクトルに最も類似した候補を返す"""
    similarities = []
    for name, vec in candidates.items():
        sim = cosine_similarity(query_vec, vec)
        similarities.append((name, sim))

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities

# テスト
embeddings = {
    "Python入門": [0.9, 0.8, 0.1, 0.2, 0.1],
    "JavaScript基礎": [0.8, 0.7, 0.2, 0.1, 0.1],
    "料理レシピ": [0.1, 0.1, 0.9, 0.8, 0.7],
    "お菓子の作り方": [0.1, 0.2, 0.8, 0.9, 0.8],
    "機械学習入門": [0.9, 0.7, 0.1, 0.3, 0.2],
}

query = [0.85, 0.75, 0.15, 0.25, 0.1]
print("クエリ: プログラミング系")
results = find_most_similar(query, embeddings)
for name, sim in results:
    print(f"  {name}: {sim:.4f}")

print()
query2 = [0.1, 0.15, 0.85, 0.85, 0.75]
print("クエリ: 料理系")
results2 = find_most_similar(query2, embeddings)
for name, sim in results2:
    print(f"  {name}: {sim:.4f}")
`,
    hints: [
      "内積: sum(a * b for a, b in zip(vec_a, vec_b))",
      "ノルム: math.sqrt(sum(x * x for x in vec))",
      "ゼロ除算に注意しましょう",
      "sorted()のkey引数とreverse=Trueで降順ソートできます",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
# 同じベクトルの類似度は1.0
assert abs(cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 0.001
# 直交ベクトルの類似度は0.0
assert abs(cosine_similarity([1, 0, 0], [0, 1, 0]) - 0.0) < 0.001
# 反対ベクトルの類似度は-1.0
assert abs(cosine_similarity([1, 0], [-1, 0]) - (-1.0)) < 0.001
# ゼロベクトル
assert cosine_similarity([0, 0], [1, 1]) == 0.0
# 長さ不一致
try:
    cosine_similarity([1], [1, 2])
    assert False, "ValueErrorが発生するべき"
except ValueError:
    pass
# find_most_similar
results = find_most_similar([1, 0], {"A": [1, 0], "B": [0, 1]})
assert results[0][0] == "A", "最も類似した候補がAであるべき"
print("PASS")
`,
      },
    ],
  },
  {
    id: "genai-07-semantic-search",
    title: "簡易セマンティック検索エンジンを作ろう",
    difficulty: "hard",
    executionTarget: "pyodide",
    starterCode: `import math

# 簡易的なセマンティック検索エンジンを作成してください。
# 文字のバイグラム（2文字組み合わせ）をベクトル化して検索します。

class SimpleSemanticSearch:
    def __init__(self):
        self.documents = {}  # {doc_id: {"text": str, "vector": dict}}
        self.vocabulary = set()  # 全バイグラムの集合

    def _text_to_bigrams(self, text: str) -> dict:
        """テキストをバイグラムの出現頻度辞書に変換する"""
        # 例: "ABC" → {"AB": 1, "BC": 1}
        # 例: "ABAB" → {"AB": 2, "BA": 1}
        # ここにコードを書いてください
        pass

    def _cosine_sim(self, vec1: dict, vec2: dict) -> float:
        """2つのスパースベクトル（辞書形式）のコサイン類似度"""
        # 共通キーの内積を計算
        # ここにコードを書いてください
        pass

    def add_document(self, doc_id: str, text: str):
        """文書を追加する"""
        # ここにコードを書いてください
        pass

    def search(self, query: str, top_k: int = 3) -> list:
        """
        クエリに類似した文書を検索する。
        戻り値: [{"doc_id": str, "text": str, "score": float}, ...]
        """
        # ここにコードを書いてください
        pass

# テスト
engine = SimpleSemanticSearch()
engine.add_document("doc1", "Pythonプログラミング入門")
engine.add_document("doc2", "Pythonでデータ分析")
engine.add_document("doc3", "JavaScriptでWeb開発")
engine.add_document("doc4", "機械学習とPython")
engine.add_document("doc5", "料理の基本レシピ集")
engine.add_document("doc6", "お菓子作りの入門")

print("検索: 'Python入門'")
results = engine.search("Python入門", top_k=3)
for r in results:
    print(f"  [{r['doc_id']}] {r['text']} (スコア: {r['score']:.4f})")

print()
print("検索: '料理入門'")
results = engine.search("料理入門", top_k=3)
for r in results:
    print(f"  [{r['doc_id']}] {r['text']} (スコア: {r['score']:.4f})")
`,
    solutionCode: `import math

class SimpleSemanticSearch:
    def __init__(self):
        self.documents = {}
        self.vocabulary = set()

    def _text_to_bigrams(self, text: str) -> dict:
        """テキストをバイグラムの出現頻度辞書に変換する"""
        bigrams = {}
        for i in range(len(text) - 1):
            bg = text[i:i+2]
            bigrams[bg] = bigrams.get(bg, 0) + 1
        return bigrams

    def _cosine_sim(self, vec1: dict, vec2: dict) -> float:
        """2つのスパースベクトル（辞書形式）のコサイン類似度"""
        # 共通キーの内積
        common_keys = set(vec1.keys()) & set(vec2.keys())
        dot_product = sum(vec1[k] * vec2[k] for k in common_keys)

        norm1 = math.sqrt(sum(v * v for v in vec1.values()))
        norm2 = math.sqrt(sum(v * v for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def add_document(self, doc_id: str, text: str):
        """文書を追加する"""
        vector = self._text_to_bigrams(text)
        self.documents[doc_id] = {"text": text, "vector": vector}
        self.vocabulary.update(vector.keys())

    def search(self, query: str, top_k: int = 3) -> list:
        """クエリに類似した文書を検索する"""
        query_vector = self._text_to_bigrams(query)
        results = []

        for doc_id, doc in self.documents.items():
            score = self._cosine_sim(query_vector, doc["vector"])
            results.append({
                "doc_id": doc_id,
                "text": doc["text"],
                "score": score
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

# テスト
engine = SimpleSemanticSearch()
engine.add_document("doc1", "Pythonプログラミング入門")
engine.add_document("doc2", "Pythonでデータ分析")
engine.add_document("doc3", "JavaScriptでWeb開発")
engine.add_document("doc4", "機械学習とPython")
engine.add_document("doc5", "料理の基本レシピ集")
engine.add_document("doc6", "お菓子作りの入門")

print("検索: 'Python入門'")
results = engine.search("Python入門", top_k=3)
for r in results:
    print(f"  [{r['doc_id']}] {r['text']} (スコア: {r['score']:.4f})")

print()
print("検索: '料理入門'")
results = engine.search("料理入門", top_k=3)
for r in results:
    print(f"  [{r['doc_id']}] {r['text']} (スコア: {r['score']:.4f})")
`,
    hints: [
      "バイグラム: text[i:i+2]で2文字ずつ取り出し、出現回数をカウント",
      "スパースベクトルのコサイン類似度: 共通キーのみ内積を計算",
      "dict.get(key, 0)でデフォルト値0を返せます",
      "検索結果はscoreの降順でソートしてtop_k個を返します",
    ],
    testCases: [
      {
        id: "tc2",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
e = SimpleSemanticSearch()
e.add_document("a", "Python学習")
e.add_document("b", "料理レシピ")
results = e.search("Python", top_k=2)
assert len(results) == 2, "2件の結果が必要です"
assert results[0]["doc_id"] == "a", "Pythonに最も類似するのはdoc a"
assert results[0]["score"] > results[1]["score"], "スコア順が正しくありません"
assert "text" in results[0], "textフィールドが必要です"
assert "score" in results[0], "scoreフィールドが必要です"
print("PASS")
`,
      },
    ],
  },
];
