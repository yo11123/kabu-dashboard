import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-03-01",
    title: "欠損値の処理",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# 欠損値を含むDataFrameを作成し、適切に処理してください
# 1. 欠損値の数を列ごとに表示
# 2. '年齢'列の欠損値を平均値で補完
# 3. '収入'列の欠損値を中央値で補完
# 4. 補完後のDataFrameを表示

import pandas as pd
import numpy as np

df = pd.DataFrame({
    '年齢': [25, np.nan, 35, 40, np.nan, 30],
    '収入': [300, 450, np.nan, 600, 500, np.nan],
    '部署': ['A', 'B', 'A', 'B', 'A', 'B']
})

# ここにコードを書いてください
`,
    solutionCode: `import pandas as pd
import numpy as np

df = pd.DataFrame({
    '年齢': [25, np.nan, 35, 40, np.nan, 30],
    '収入': [300, 450, np.nan, 600, 500, np.nan],
    '部署': ['A', 'B', 'A', 'B', 'A', 'B']
})

print("=== 欠損値の数 ===")
print(df.isnull().sum())

df['年齢'] = df['年齢'].fillna(df['年齢'].mean())
df['収入'] = df['収入'].fillna(df['収入'].median())

print("\\n=== 補完後のデータ ===")
print(df.to_string(index=False))
`,
    hints: [
      "df.isnull().sum() で各列の欠損値数を確認できます",
      "df['列名'].fillna(値) で欠損値を特定の値で補完できます",
      "df['列名'].mean() で平均値、df['列名'].median() で中央値を取得できます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "=== 欠損値の数 ===",
      },
    ],
  },
  {
    id: "ml-03-02",
    title: "特徴量のスケーリング",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# StandardScalerとMinMaxScalerを使ってデータをスケーリングしてください
# 1. サンプルデータを作成
# 2. StandardScalerで標準化し、平均と標準偏差を表示
# 3. MinMaxScalerで正規化し、最小値と最大値を表示

import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler

np.random.seed(42)
X = np.random.rand(5, 2) * [100, 1000]  # スケールが異なる2つの特徴量

print(f"元のデータ:\\n{X.round(2)}")

# ここにコードを書いてください
`,
    solutionCode: `import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler

np.random.seed(42)
X = np.random.rand(5, 2) * [100, 1000]

print(f"元のデータ:\\n{X.round(2)}")

# StandardScaler
ss = StandardScaler()
X_standard = ss.fit_transform(X)
print(f"\\n=== StandardScaler ===")
print(f"平均: {X_standard.mean(axis=0).round(2)}")
print(f"標準偏差: {X_standard.std(axis=0).round(2)}")

# MinMaxScaler
mms = MinMaxScaler()
X_minmax = mms.fit_transform(X)
print(f"\\n=== MinMaxScaler ===")
print(f"最小値: {X_minmax.min(axis=0).round(2)}")
print(f"最大値: {X_minmax.max(axis=0).round(2)}")
`,
    hints: [
      "StandardScaler() を作成し、fit_transform(X) でスケーリングします",
      "MinMaxScaler() を作成し、fit_transform(X) で正規化します",
      "mean(axis=0) で列ごとの平均を計算できます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "=== StandardScaler ===",
      },
    ],
  },
];
