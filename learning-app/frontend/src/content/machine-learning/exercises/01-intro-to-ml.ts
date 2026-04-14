import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-01-01",
    title: "scikit-learnでIrisデータセットを読み込む",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `# scikit-learnからIrisデータセットを読み込み、基本情報を表示してください
# 1. load_iris() でデータを読み込む
# 2. データの形状（shape）を表示
# 3. ターゲットのクラス名を表示
# 4. 特徴量の名前を表示

from sklearn.datasets import load_iris

# ここにコードを書いてください
iris = load_iris()
`,
    solutionCode: `from sklearn.datasets import load_iris

iris = load_iris()
print(f"データの形状: {iris.data.shape}")
print(f"クラス名: {list(iris.target_names)}")
print(f"特徴量名: {list(iris.feature_names)}")
`,
    hints: [
      "load_iris() でデータセットを読み込みます",
      "iris.data.shape でデータの形状を確認できます",
      "iris.target_names でクラス名、iris.feature_names で特徴量名を取得できます",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "データの形状: (150, 4)",
      },
    ],
  },
  {
    id: "ml-01-02",
    title: "データの訓練・テスト分割",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `# Irisデータセットを訓練データとテストデータに分割してください
# - テストデータの割合: 20%
# - random_state=42 を指定
# - 訓練データとテストデータのサンプル数を表示

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

iris = load_iris()
X, y = iris.data, iris.target

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

iris = load_iris()
X, y = iris.data, iris.target

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"訓練データ数: {X_train.shape[0]}")
print(f"テストデータ数: {X_test.shape[0]}")
`,
    hints: [
      "train_test_split に test_size=0.2 と random_state=42 を渡します",
      "戻り値は X_train, X_test, y_train, y_test の4つです",
    ],
    testCases: [
      {
        id: "tc2",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "訓練データ数: 120",
      },
    ],
  },
];
