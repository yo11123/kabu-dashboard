import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-09-01",
    title: "K-Meansクラスタリングの実装",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# K-Meansクラスタリングを実装してください
# 1. make_blobs で3つのクラスタを持つデータを生成
# 2. KMeans(n_clusters=3, random_state=42, n_init=10) でクラスタリング
# 3. クラスタの重心を表示
# 4. 慣性（inertia）を表示
# 5. シルエットスコアを表示

from sklearn.cluster import KMeans
from sklearn.datasets import make_blobs
from sklearn.metrics import silhouette_score
import numpy as np

X, y_true = make_blobs(n_samples=300, centers=3, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.cluster import KMeans
from sklearn.datasets import make_blobs
from sklearn.metrics import silhouette_score
import numpy as np

X, y_true = make_blobs(n_samples=300, centers=3, random_state=42)

kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
y_pred = kmeans.fit_predict(X)

print("=== クラスタの重心 ===")
for i, center in enumerate(kmeans.cluster_centers_):
    print(f"  クラスタ{i}: [{center[0]:.2f}, {center[1]:.2f}]")

print(f"\\n慣性(SSE): {kmeans.inertia_:.2f}")

score = silhouette_score(X, y_pred)
print(f"シルエットスコア: {score:.3f}")
`,
    hints: [
      "KMeans(n_clusters=3, random_state=42, n_init=10) でモデルを作成します",
      "fit_predict(X) で学習とクラスタ割り当てを同時に行います",
      "silhouette_score(X, labels) でシルエットスコアを計算します",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "=== クラスタの重心 ===",
      },
    ],
  },
  {
    id: "ml-09-02",
    title: "エルボー法で最適なクラスタ数を決定",
    difficulty: "hard",
    executionTarget: "backend",
    starterCode: `# エルボー法とシルエットスコアで最適なクラスタ数を探してください
# 1. make_blobs で4つのクラスタを持つデータを生成
# 2. k=2から8まで KMeans を試す
# 3. 各kの慣性とシルエットスコアを表示
# 4. 最適なk（シルエットスコアが最大）を表示

from sklearn.cluster import KMeans
from sklearn.datasets import make_blobs
from sklearn.metrics import silhouette_score
import numpy as np

X, _ = make_blobs(n_samples=400, centers=4, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.cluster import KMeans
from sklearn.datasets import make_blobs
from sklearn.metrics import silhouette_score
import numpy as np

X, _ = make_blobs(n_samples=400, centers=4, random_state=42)

print("k | 慣性(SSE)    | シルエットスコア")
print("-" * 40)

best_k = 2
best_score = -1

for k in range(2, 9):
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    score = silhouette_score(X, labels)
    print(f"{k} | {kmeans.inertia_:12.2f} | {score:.3f}")

    if score > best_score:
        best_score = score
        best_k = k

print(f"\\n最適なクラスタ数: {best_k} (シルエットスコア: {best_score:.3f})")
`,
    hints: [
      "range(2, 9) でk=2から8までループします",
      "各kでKMeansを実行し、inertia_ とシルエットスコアを記録します",
      "シルエットスコアが最も高いkが最適です",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "最適なクラスタ数:",
      },
    ],
  },
];
