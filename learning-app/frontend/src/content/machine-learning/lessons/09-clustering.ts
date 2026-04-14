export const content = `
# クラスタリング

## クラスタリングとは

クラスタリングは教師なし学習の代表的な手法で、ラベルなしのデータを類似度に基づいてグループ（クラスタ）に分割します。

## K-Means クラスタリング

最もよく使われるクラスタリングアルゴリズムです。

### アルゴリズムの流れ

1. K個の初期重心をランダムに配置
2. 各データ点を最も近い重心のクラスタに割り当て
3. 各クラスタの重心を再計算
4. 収束するまで2-3を繰り返す

### 実装

\`\`\`python
from sklearn.cluster import KMeans
from sklearn.datasets import make_blobs
import numpy as np

# データ生成
X, y_true = make_blobs(n_samples=300, centers=3, random_state=42)

# K-Meansクラスタリング
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
y_pred = kmeans.fit_predict(X)

# 結果の確認
print(f"クラスタの重心:\\n{kmeans.cluster_centers_}")
print(f"慣性（SSE）: {kmeans.inertia_:.2f}")
\`\`\`

### 最適なクラスタ数の決定

#### エルボー法

\`\`\`python
inertias = []
K_range = range(1, 11)
for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X)
    inertias.append(km.inertia_)

# inertias をプロットして「肘」の位置を探す
\`\`\`

#### シルエットスコア

\`\`\`python
from sklearn.metrics import silhouette_score

for k in range(2, 11):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    score = silhouette_score(X, labels)
    print(f"k={k}: シルエットスコア = {score:.3f}")
\`\`\`

## 階層的クラスタリング

\`\`\`python
from sklearn.cluster import AgglomerativeClustering

agg = AgglomerativeClustering(n_clusters=3)
labels = agg.fit_predict(X)
\`\`\`

## DBSCAN

密度ベースのクラスタリングで、任意の形状のクラスタを発見できます。

\`\`\`python
from sklearn.cluster import DBSCAN

dbscan = DBSCAN(eps=0.5, min_samples=5)
labels = dbscan.fit_predict(X)

# ノイズ点は -1 でラベル付けされる
n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
print(f"クラスタ数: {n_clusters}")
\`\`\`

## 各アルゴリズムの比較

| 手法 | クラスタ形状 | K の指定 | ノイズ耐性 |
|------|------------|---------|----------|
| K-Means | 球状 | 必要 | 低い |
| 階層的 | 任意 | 必要 | 中程度 |
| DBSCAN | 任意 | 不要 | 高い |

## まとめ

クラスタリングは教師なし学習の重要な手法です。データの性質に応じて適切なアルゴリズムを選択し、シルエットスコアなどで結果を評価しましょう。
`;
