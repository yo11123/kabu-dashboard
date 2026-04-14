import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-02-01",
    title: "NumPyで配列操作と統計量計算",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `# NumPyを使って以下を行ってください
# 1. 1から10までの配列を作成
# 2. 配列の平均値、標準偏差、最大値、最小値を表示
# 3. 配列の各要素を2乗した新しい配列を作成して表示

import numpy as np

# ここにコードを書いてください
`,
    solutionCode: `import numpy as np

arr = np.arange(1, 11)
print(f"配列: {arr}")
print(f"平均値: {np.mean(arr):.1f}")
print(f"標準偏差: {np.std(arr):.2f}")
print(f"最大値: {np.max(arr)}")
print(f"最小値: {np.min(arr)}")
squared = arr ** 2
print(f"2乗: {squared}")
`,
    hints: [
      "np.arange(1, 11) で1から10までの配列を作成できます",
      "np.mean(), np.std(), np.max(), np.min() で統計量を計算します",
      "arr ** 2 で各要素を2乗できます",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "平均値: 5.5",
      },
    ],
  },
  {
    id: "ml-02-02",
    title: "PandasでDataFrame操作",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# PandasでDataFrameを作成し操作してください
# 1. 以下のデータでDataFrameを作成
#    名前: ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve']
#    年齢: [25, 30, 35, 28, 32]
#    得点: [85, 92, 78, 95, 88]
# 2. 得点が80以上のレコードをフィルタリング
# 3. 年齢の平均値を表示
# 4. 得点で降順にソートして表示

import pandas as pd

# ここにコードを書いてください
`,
    solutionCode: `import pandas as pd

df = pd.DataFrame({
    '名前': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
    '年齢': [25, 30, 35, 28, 32],
    '得点': [85, 92, 78, 95, 88]
})

print("=== 得点80以上 ===")
high_scores = df[df['得点'] >= 80]
print(high_scores.to_string(index=False))

print(f"\\n年齢の平均値: {df['年齢'].mean():.1f}")

print("\\n=== 得点で降順ソート ===")
sorted_df = df.sort_values('得点', ascending=False)
print(sorted_df.to_string(index=False))
`,
    hints: [
      "pd.DataFrame() に辞書を渡してDataFrameを作成します",
      "df[df['得点'] >= 80] で条件フィルタリングができます",
      "df.sort_values('得点', ascending=False) で降順ソートできます",
    ],
    testCases: [
      {
        id: "tc2",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "年齢の平均値: 30.0",
      },
    ],
  },
];
