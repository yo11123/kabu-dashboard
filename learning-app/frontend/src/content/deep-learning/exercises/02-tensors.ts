import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-02-01",
    title: "テンソルの演算と形状操作",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `import torch

# 問題1: 0から11までの整数テンソルを作成し、3x4の行列にreshapeしてください
t = # ここにコードを書く
matrix = # ここにコードを書く
print(f"行列:\\n{matrix}")

# 問題2: matrixの各列の合計を計算してください（dim=0で集約）
col_sum = # ここにコードを書く
print(f"列の合計: {col_sum}")

# 問題3: matrixの各行の平均を計算してください（dim=1で集約、float型に変換が必要）
row_mean = # ここにコードを書く
print(f"行の平均: {row_mean}")
`,
    solutionCode: `import torch

# 問題1: 0から11までの整数テンソルを作成し、3x4の行列にreshapeしてください
t = torch.arange(12)
matrix = t.reshape(3, 4)
print(f"行列:\\n{matrix}")

# 問題2: matrixの各列の合計を計算してください（dim=0で集約）
col_sum = matrix.sum(dim=0)
print(f"列の合計: {col_sum}")

# 問題3: matrixの各行の平均を計算してください（dim=1で集約、float型に変換が必要）
row_mean = matrix.float().mean(dim=1)
print(f"行の平均: {row_mean}")
`,
    hints: [
      "torch.arange(12) で0〜11のテンソルを作成できます",
      ".reshape(行, 列) で形状を変更できます",
      ".sum(dim=0) で列方向に合計を計算します",
      "整数テンソルの平均を取るには .float() で型変換が必要です",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "列の合計: tensor([12, 15, 18, 21])",
      },
      {
        id: "tc2",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "行の平均: tensor([1.5000, 5.5000, 9.5000])",
      },
    ],
  },
  {
    id: "dl-02-02",
    title: "行列演算とインデキシング",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `import torch

# 問題1: 2x3の行列Aと3x2の行列Bを作成し、行列積を計算してください
A = torch.tensor([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
B = torch.tensor([[7.0, 8.0], [9.0, 10.0], [11.0, 12.0]])
C = # ここにコードを書く（行列積）
print(f"行列積:\\n{C}")

# 問題2: 以下の行列から、値が5より大きい要素だけを取り出してください
data = torch.tensor([[1, 8, 3], [6, 2, 9], [4, 7, 5]])
filtered = # ここにコードを書く
print(f"5より大きい要素: {filtered}")

# 問題3: dataの2行目（インデックス1）を取り出してください
row = # ここにコードを書く
print(f"2行目: {row}")
`,
    solutionCode: `import torch

# 問題1: 2x3の行列Aと3x2の行列Bを作成し、行列積を計算してください
A = torch.tensor([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
B = torch.tensor([[7.0, 8.0], [9.0, 10.0], [11.0, 12.0]])
C = A @ B
print(f"行列積:\\n{C}")

# 問題2: 以下の行列から、値が5より大きい要素だけを取り出してください
data = torch.tensor([[1, 8, 3], [6, 2, 9], [4, 7, 5]])
filtered = data[data > 5]
print(f"5より大きい要素: {filtered}")

# 問題3: dataの2行目（インデックス1）を取り出してください
row = data[1]
print(f"2行目: {row}")
`,
    hints: [
      "行列積は @ 演算子または torch.matmul() を使います",
      "条件フィルタは tensor[条件] の形式で使えます",
      "行のインデックスは0から始まります",
    ],
    testCases: [
      {
        id: "tc3",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "行列積:\ntensor([[ 58.,  64.],\n        [139., 154.]])",
      },
      {
        id: "tc4",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "5より大きい要素: tensor([8, 6, 9, 7])",
      },
      {
        id: "tc5",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "2行目: tensor([6, 2, 9])",
      },
    ],
  },
];
