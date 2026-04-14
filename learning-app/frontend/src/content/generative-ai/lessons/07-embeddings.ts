export const content = `
# エンベディング（Embeddings）

## エンベディングとは

エンベディングとは、テキストや画像などのデータを数値ベクトル（数値の配列）に変換する技術です。意味的に近いデータは、ベクトル空間上で近い位置にマッピングされます。

## なぜエンベディングが重要か

コンピュータはテキストを直接理解できません。エンベディングにより：

1. **意味の数値化**: テキストの意味を数値で表現
2. **類似度計算**: テキスト間の類似度を定量的に測定
3. **検索**: 意味に基づいた検索が可能
4. **クラスタリング**: 似た文書の自動グループ化

## ベクトル表現の基本

\`\`\`python
# エンベディングのイメージ
embeddings = {
    "猫": [0.2, 0.8, -0.1, 0.5, ...],      # 1536次元のベクトル
    "犬": [0.3, 0.7, -0.2, 0.4, ...],      # 猫に近い
    "プログラミング": [-0.5, 0.1, 0.9, -0.3, ...],  # 猫から遠い
}
\`\`\`

## コサイン類似度

2つのベクトル間の類似度を測る最も一般的な方法です。

\`\`\`python
import math

def cosine_similarity(vec_a, vec_b):
    """2つのベクトルのコサイン類似度を計算"""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)

# 例
vec1 = [1.0, 0.5, 0.3]
vec2 = [0.9, 0.6, 0.2]
vec3 = [-0.5, 0.1, -0.8]

print(f"vec1とvec2の類似度: {cosine_similarity(vec1, vec2):.4f}")  # 高い
print(f"vec1とvec3の類似度: {cosine_similarity(vec1, vec3):.4f}")  # 低い
\`\`\`

## OpenAI Embeddings API

\`\`\`python
# APIリクエストの構造
request = {
    "model": "text-embedding-3-small",
    "input": "東京タワーは東京都港区にある電波塔です"
}

# レスポンスの構造
response = {
    "data": [
        {
            "embedding": [0.023, -0.015, 0.042, ...],  # 1536次元
            "index": 0
        }
    ],
    "usage": {
        "prompt_tokens": 15,
        "total_tokens": 15
    }
}
\`\`\`

## セマンティック検索

エンベディングを使った意味検索の仕組みです。

\`\`\`python
def semantic_search(query_embedding, document_embeddings, top_k=3):
    """クエリに最も類似した文書を検索"""
    similarities = []

    for doc_id, doc_embedding in document_embeddings.items():
        sim = cosine_similarity(query_embedding, doc_embedding)
        similarities.append((doc_id, sim))

    # 類似度の高い順にソート
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities[:top_k]
\`\`\`

## ベクトルデータベース

大量のエンベディングを効率的に管理・検索するためのデータベースです。

| データベース | 特徴 |
|-------------|------|
| Pinecone | クラウドネイティブ、簡単に使える |
| Chroma | オープンソース、ローカル実行可能 |
| Weaviate | GraphQL対応、柔軟なスキーマ |
| FAISS | Meta開発、高速検索 |

## エンベディングの活用例

### 1. 文書の類似度検索
\`\`\`python
# FAQ検索システム
faq_db = {
    "q1": {"text": "パスワードの変更方法", "embedding": [...]},
    "q2": {"text": "アカウントの削除方法", "embedding": [...]},
    "q3": {"text": "料金プランの確認方法", "embedding": [...]},
}
# ユーザーの質問「パスワードをリセットしたい」→ q1が最も類似
\`\`\`

### 2. テキストのクラスタリング
同じトピックの文書を自動的にグループ化できます。

### 3. 異常検知
通常のパターンから外れた文書を検出できます。

## まとめ

エンベディングは、テキストの意味を数値化する重要な技術です。コサイン類似度を使った類似度計算、セマンティック検索、クラスタリングなど、多くのAIアプリケーションの基盤となっています。次のレッスンでは、エンベディングを活用したRAGシステムについて学びます。
`;
