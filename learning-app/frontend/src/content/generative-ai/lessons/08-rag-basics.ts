export const content = `
# RAG基礎（Retrieval-Augmented Generation）

## RAGとは

RAG（Retrieval-Augmented Generation）は、外部の知識ベースから関連情報を検索（Retrieval）し、その情報を基にLLMが回答を生成（Generation）する手法です。LLMの知識の限界を補い、最新かつ正確な情報に基づいた回答を実現します。

## なぜRAGが必要か

LLMには以下の制限があります：

1. **知識のカットオフ**: 学習後の情報を知らない
2. **ハルシネーション**: 事実でない情報を生成する
3. **専門知識の不足**: 特定分野の深い知識が足りない
4. **情報の更新不可**: モデルの再学習なしに知識を更新できない

RAGはこれらの問題を**検索で解決**します。

## RAGのアーキテクチャ

\`\`\`
ユーザーの質問
    ↓
[1. 検索（Retrieval）]
    ↓ クエリをエンベディング化
    ↓ ベクトルDBで類似文書を検索
    ↓ 関連文書を取得
    ↓
[2. 拡張（Augmentation）]
    ↓ 質問 + 関連文書 を組み合わせてプロンプト作成
    ↓
[3. 生成（Generation）]
    ↓ LLMが拡張されたプロンプトで回答生成
    ↓
回答
\`\`\`

## RAGの実装ステップ

### ステップ1: 文書の準備（インデクシング）

\`\`\`python
# 文書をチャンクに分割
def split_into_chunks(text, chunk_size=500, overlap=50):
    """テキストをオーバーラップ付きでチャンクに分割"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks

document = "長い文書のテキスト..."
chunks = split_into_chunks(document)
# 各チャンクをエンベディング化してベクトルDBに保存
\`\`\`

### ステップ2: 検索

\`\`\`python
def retrieve_relevant_docs(query, vector_db, top_k=3):
    """クエリに関連する文書を検索"""
    query_embedding = get_embedding(query)  # クエリをベクトル化
    results = vector_db.search(query_embedding, top_k=top_k)
    return results
\`\`\`

### ステップ3: プロンプトの構築

\`\`\`python
def build_rag_prompt(query, retrieved_docs):
    """検索結果を含むプロンプトを構築"""
    context = "\\n\\n".join([doc["text"] for doc in retrieved_docs])

    prompt = f"""以下のコンテキスト情報を基に質問に回答してください。
コンテキストに含まれない情報は「情報がありません」と回答してください。

### コンテキスト ###
{context}
### コンテキスト終わり ###

質問: {query}

回答:"""
    return prompt
\`\`\`

## チャンク分割戦略

| 戦略 | 説明 | 適した場面 |
|------|------|-----------|
| 固定長分割 | 一定の文字数で分割 | 汎用的 |
| 段落分割 | 段落単位で分割 | 構造化文書 |
| セマンティック分割 | 意味の区切りで分割 | 高品質な検索 |
| 再帰的分割 | 階層的に分割 | 長い文書 |

## チャンクサイズの選択

\`\`\`python
# チャンクサイズの影響
chunk_configs = {
    "小さいチャンク (200文字)": {
        "pros": "精度が高い、ノイズが少ない",
        "cons": "文脈が不足する可能性"
    },
    "中くらいのチャンク (500文字)": {
        "pros": "バランスが良い",
        "cons": "汎用的だが最適ではない場合も"
    },
    "大きいチャンク (1000文字)": {
        "pros": "十分な文脈を含む",
        "cons": "ノイズが増える、トークン消費大"
    }
}
\`\`\`

## RAGの評価

RAGシステムの品質は以下の指標で評価します：

1. **Recall**: 正解文書が検索結果に含まれる割合
2. **Precision**: 検索結果のうち関連する文書の割合
3. **Answer Quality**: 最終的な回答の品質
4. **Faithfulness**: 回答がコンテキストに忠実かどうか

## RAGの改善テクニック

1. **ハイブリッド検索**: ベクトル検索 + キーワード検索の組み合わせ
2. **リランキング**: 検索結果を再評価して順位を調整
3. **クエリ拡張**: 元の質問を言い換えて検索精度を向上
4. **メタデータフィルタリング**: 日付やカテゴリで絞り込み

## まとめ

RAGは、LLMの能力と外部知識を組み合わせた強力なアーキテクチャです。文書のチャンク分割、エンベディング、検索、プロンプト構築の各ステップを適切に設計することで、正確で信頼性の高いAIアプリケーションを構築できます。
`;
