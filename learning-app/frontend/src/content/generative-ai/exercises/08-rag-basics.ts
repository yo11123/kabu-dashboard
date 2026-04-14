import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "genai-08-chunk-splitter",
    title: "テキストチャンク分割器を作ろう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# RAGシステムの重要なコンポーネントであるテキストチャンク分割器を作成してください。
# テキストを指定されたサイズでオーバーラップ付きで分割します。

def split_into_chunks(text: str, chunk_size: int = 100, overlap: int = 20) -> list:
    """
    テキストをチャンクに分割する。

    引数:
        text: 分割するテキスト
        chunk_size: チャンクの最大文字数
        overlap: チャンク間のオーバーラップ文字数

    戻り値: チャンクの辞書リスト
    [
        {"id": 0, "text": "...", "start": 0, "end": 100},
        {"id": 1, "text": "...", "start": 80, "end": 180},
        ...
    ]

    注意:
    - overlapはchunk_sizeより小さくなければならない
    - 最後のチャンクはchunk_sizeより短くてもよい
    - 空のチャンクは含めない
    """
    # ここにコードを書いてください
    pass

def split_by_paragraphs(text: str, max_chunk_size: int = 200) -> list:
    """
    段落単位でテキストを分割する。
    段落は空行（\\n\\n）で区切られる。
    max_chunk_sizeを超える場合は、段落の途中でも分割する。

    戻り値: [{"id": 0, "text": "段落テキスト"}, ...]
    """
    # ここにコードを書いてください
    pass

# テスト
text = "あ" * 250  # 250文字のテスト用テキスト
chunks = split_into_chunks(text, chunk_size=100, overlap=20)
print(f"テキスト長: {len(text)}")
print(f"チャンク数: {len(chunks)}")
for c in chunks:
    print(f"  チャンク{c['id']}: 位置[{c['start']}:{c['end']}] 長さ={len(c['text'])}")

print()

para_text = """第1段落の内容です。ここには重要な情報が含まれています。

第2段落です。別のトピックについて説明します。

第3段落。まとめの内容です。"""

para_chunks = split_by_paragraphs(para_text, max_chunk_size=200)
print(f"段落チャンク数: {len(para_chunks)}")
for c in para_chunks:
    print(f"  チャンク{c['id']}: {c['text'][:30]}...")
`,
    solutionCode: `def split_into_chunks(text: str, chunk_size: int = 100, overlap: int = 20) -> list:
    """テキストをチャンクに分割する"""
    if overlap >= chunk_size:
        raise ValueError("overlapはchunk_sizeより小さくなければなりません")

    chunks = []
    start = 0
    chunk_id = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]

        if chunk_text:  # 空のチャンクは含めない
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "start": start,
                "end": end
            })
            chunk_id += 1

        start += chunk_size - overlap

    return chunks

def split_by_paragraphs(text: str, max_chunk_size: int = 200) -> list:
    """段落単位でテキストを分割する"""
    paragraphs = [p.strip() for p in text.split("\\n\\n") if p.strip()]
    chunks = []
    chunk_id = 0

    for para in paragraphs:
        if len(para) <= max_chunk_size:
            chunks.append({"id": chunk_id, "text": para})
            chunk_id += 1
        else:
            # 段落がmax_chunk_sizeを超える場合は分割
            start = 0
            while start < len(para):
                end = min(start + max_chunk_size, len(para))
                chunk_text = para[start:end]
                if chunk_text.strip():
                    chunks.append({"id": chunk_id, "text": chunk_text})
                    chunk_id += 1
                start = end

    return chunks

# テスト
text = "あ" * 250
chunks = split_into_chunks(text, chunk_size=100, overlap=20)
print(f"テキスト長: {len(text)}")
print(f"チャンク数: {len(chunks)}")
for c in chunks:
    print(f"  チャンク{c['id']}: 位置[{c['start']}:{c['end']}] 長さ={len(c['text'])}")

print()

para_text = """第1段落の内容です。ここには重要な情報が含まれています。

第2段落です。別のトピックについて説明します。

第3段落。まとめの内容です。"""

para_chunks = split_by_paragraphs(para_text, max_chunk_size=200)
print(f"段落チャンク数: {len(para_chunks)}")
for c in para_chunks:
    print(f"  チャンク{c['id']}: {c['text'][:30]}...")
`,
    hints: [
      "whileループでstartを(chunk_size - overlap)ずつ進めます",
      "min(start + chunk_size, len(text))で末尾を超えないようにします",
      "段落分割はtext.split('\\n\\n')で行えます",
      "空の段落は除外しましょう",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
# 固定長分割のテスト
chunks = split_into_chunks("A" * 50, chunk_size=20, overlap=5)
assert len(chunks) >= 3, f"チャンク数が不足: {len(chunks)}"
assert chunks[0]["start"] == 0, "最初のチャンクはstart=0"
assert chunks[0]["end"] == 20, "最初のチャンクはend=20"
assert chunks[1]["start"] == 15, f"2番目のチャンクのstart: {chunks[1]['start']}"
assert all("id" in c and "text" in c and "start" in c and "end" in c for c in chunks)

# 段落分割のテスト
pchunks = split_by_paragraphs("段落1\\n\\n段落2\\n\\n段落3")
assert len(pchunks) == 3, f"段落数: {len(pchunks)}"
assert pchunks[0]["text"] == "段落1"
assert pchunks[2]["text"] == "段落3"
print("PASS")
`,
      },
    ],
  },
  {
    id: "genai-08-rag-pipeline",
    title: "RAGパイプラインを構築しよう",
    difficulty: "hard",
    executionTarget: "pyodide",
    starterCode: `import math
import json

# 簡易的なRAGパイプラインを構築してください。
# 文書の登録、検索、プロンプト生成、モックレスポンスの一連の流れを実装します。

class SimpleRAG:
    def __init__(self, system_prompt: str = ""):
        self.documents = []  # [{"id": int, "text": str, "vector": dict}]
        self.system_prompt = system_prompt or "コンテキスト情報を基に質問に回答してください。コンテキストにない情報は「情報がありません」と答えてください。"

    def _text_to_vector(self, text: str) -> dict:
        """テキストをバイグラムベースのスパースベクトルに変換"""
        vec = {}
        for i in range(len(text) - 1):
            bg = text[i:i+2]
            vec[bg] = vec.get(bg, 0) + 1
        return vec

    def _cosine_similarity(self, v1: dict, v2: dict) -> float:
        """スパースベクトル間のコサイン類似度"""
        common = set(v1.keys()) & set(v2.keys())
        dot = sum(v1[k] * v2[k] for k in common)
        n1 = math.sqrt(sum(x*x for x in v1.values()))
        n2 = math.sqrt(sum(x*x for x in v2.values()))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def add_documents(self, texts: list):
        """複数の文書を追加する"""
        # ここにコードを書いてください
        pass

    def retrieve(self, query: str, top_k: int = 3) -> list:
        """
        クエリに関連する文書を検索する。
        戻り値: [{"id": int, "text": str, "score": float}, ...]
        scoreの降順でtop_k件を返す。
        """
        # ここにコードを書いてください
        pass

    def build_prompt(self, query: str, retrieved_docs: list) -> list:
        """
        RAGプロンプトをOpenAI APIのメッセージ形式で構築する。
        戻り値: [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "コンテキスト:\\n{docs}\\n\\n質問: {query}"}
        ]
        """
        # ここにコードを書いてください
        pass

    def query(self, question: str, top_k: int = 2) -> dict:
        """
        RAGパイプライン全体を実行する。
        1. 関連文書を検索
        2. プロンプトを構築
        3. 結果を返す

        戻り値: {
            "question": str,
            "retrieved_docs": list,
            "prompt": list,
            "num_context_docs": int
        }
        """
        # ここにコードを書いてください
        pass

# テスト
rag = SimpleRAG()
rag.add_documents([
    "Pythonは1991年にGuido van Rossumによって開発されたプログラミング言語です。",
    "Pythonはデータサイエンスや機械学習の分野で広く使われています。",
    "JavaScriptはWebブラウザで動作するプログラミング言語です。",
    "React はFacebookが開発したJavaScriptのUIライブラリです。",
    "機械学習では大量のデータを使ってモデルを訓練します。",
])

result = rag.query("Pythonはどんな言語ですか？", top_k=2)
print(f"質問: {result['question']}")
print(f"検索された文書数: {result['num_context_docs']}")
print("\\n検索結果:")
for doc in result["retrieved_docs"]:
    print(f"  [{doc['id']}] スコア:{doc['score']:.3f} - {doc['text'][:40]}...")
print("\\nプロンプト:")
for msg in result["prompt"]:
    print(f"  [{msg['role']}]: {msg['content'][:80]}...")
`,
    solutionCode: `import math
import json

class SimpleRAG:
    def __init__(self, system_prompt: str = ""):
        self.documents = []
        self.system_prompt = system_prompt or "コンテキスト情報を基に質問に回答してください。コンテキストにない情報は「情報がありません」と答えてください。"

    def _text_to_vector(self, text: str) -> dict:
        """テキストをバイグラムベースのスパースベクトルに変換"""
        vec = {}
        for i in range(len(text) - 1):
            bg = text[i:i+2]
            vec[bg] = vec.get(bg, 0) + 1
        return vec

    def _cosine_similarity(self, v1: dict, v2: dict) -> float:
        """スパースベクトル間のコサイン類似度"""
        common = set(v1.keys()) & set(v2.keys())
        dot = sum(v1[k] * v2[k] for k in common)
        n1 = math.sqrt(sum(x*x for x in v1.values()))
        n2 = math.sqrt(sum(x*x for x in v2.values()))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def add_documents(self, texts: list):
        """複数の文書を追加する"""
        for text in texts:
            doc_id = len(self.documents)
            vector = self._text_to_vector(text)
            self.documents.append({
                "id": doc_id,
                "text": text,
                "vector": vector
            })

    def retrieve(self, query: str, top_k: int = 3) -> list:
        """クエリに関連する文書を検索する"""
        query_vec = self._text_to_vector(query)
        results = []

        for doc in self.documents:
            score = self._cosine_similarity(query_vec, doc["vector"])
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "score": score
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def build_prompt(self, query: str, retrieved_docs: list) -> list:
        """RAGプロンプトをメッセージ形式で構築する"""
        context = "\\n".join(doc["text"] for doc in retrieved_docs)

        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"コンテキスト:\\n{context}\\n\\n質問: {query}"}
        ]

    def query(self, question: str, top_k: int = 2) -> dict:
        """RAGパイプライン全体を実行する"""
        retrieved_docs = self.retrieve(question, top_k)
        prompt = self.build_prompt(question, retrieved_docs)

        return {
            "question": question,
            "retrieved_docs": retrieved_docs,
            "prompt": prompt,
            "num_context_docs": len(retrieved_docs)
        }

# テスト
rag = SimpleRAG()
rag.add_documents([
    "Pythonは1991年にGuido van Rossumによって開発されたプログラミング言語です。",
    "Pythonはデータサイエンスや機械学習の分野で広く使われています。",
    "JavaScriptはWebブラウザで動作するプログラミング言語です。",
    "React はFacebookが開発したJavaScriptのUIライブラリです。",
    "機械学習では大量のデータを使ってモデルを訓練します。",
])

result = rag.query("Pythonはどんな言語ですか？", top_k=2)
print(f"質問: {result['question']}")
print(f"検索された文書数: {result['num_context_docs']}")
print("\\n検索結果:")
for doc in result["retrieved_docs"]:
    print(f"  [{doc['id']}] スコア:{doc['score']:.3f} - {doc['text'][:40]}...")
print("\\nプロンプト:")
for msg in result["prompt"]:
    print(f"  [{msg['role']}]: {msg['content'][:80]}...")
`,
    hints: [
      "add_documents: lenでIDを自動採番し、各テキストをベクトル化して保存",
      "retrieve: クエリをベクトル化し、各文書との類似度を計算してソート",
      "build_prompt: 検索結果のテキストを結合してコンテキストにする",
      "query: retrieve → build_prompt の順に呼び出す",
    ],
    testCases: [
      {
        id: "tc2",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
r = SimpleRAG()
r.add_documents(["Python言語", "Java言語", "料理レシピ"])
assert len(r.documents) == 3, "3つの文書が登録されるべき"

results = r.retrieve("Python", top_k=2)
assert len(results) == 2, "top_k=2で2件返すべき"
assert results[0]["text"] == "Python言語", "Pythonに最も類似するのはPython言語"

qr = r.query("Pythonとは？", top_k=1)
assert "question" in qr, "questionフィールドが必要"
assert "retrieved_docs" in qr, "retrieved_docsフィールドが必要"
assert "prompt" in qr, "promptフィールドが必要"
assert len(qr["prompt"]) == 2, "プロンプトはsystemとuserの2メッセージ"
assert qr["prompt"][0]["role"] == "system"
assert "コンテキスト" in qr["prompt"][1]["content"]
assert qr["num_context_docs"] == 1
print("PASS")
`,
      },
    ],
  },
];
