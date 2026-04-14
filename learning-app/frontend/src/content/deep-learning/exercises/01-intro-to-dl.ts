import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-01-01",
    title: "PyTorchの基本操作",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `import torch

# 問題1: 値が [1.0, 2.0, 3.0, 4.0, 5.0] のテンソルを作成してください
x = # ここにコードを書く

# 問題2: xの各要素を2乗したテンソルを作成してください
x_squared = # ここにコードを書く

# 問題3: xの全要素の合計を計算してください
x_sum = # ここにコードを書く

print(f"テンソル: {x}")
print(f"2乗: {x_squared}")
print(f"合計: {x_sum}")
`,
    solutionCode: `import torch

# 問題1: 値が [1.0, 2.0, 3.0, 4.0, 5.0] のテンソルを作成してください
x = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])

# 問題2: xの各要素を2乗したテンソルを作成してください
x_squared = x ** 2

# 問題3: xの全要素の合計を計算してください
x_sum = x.sum()

print(f"テンソル: {x}")
print(f"2乗: {x_squared}")
print(f"合計: {x_sum}")
`,
    hints: [
      "torch.tensor() でリストからテンソルを作成できます",
      "べき乗は ** 演算子を使います",
      ".sum() メソッドで全要素の合計を計算できます",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "テンソル: tensor([1., 2., 3., 4., 5.])",
      },
      {
        id: "tc2",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "2乗: tensor([ 1.,  4.,  9., 16., 25.])",
      },
      {
        id: "tc3",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "合計: 15.0",
      },
    ],
  },
  {
    id: "dl-01-02",
    title: "テンソルの情報確認",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `import torch

# 3x4の行列（全て1.0）を作成してください
matrix = # ここにコードを書く

# 行列の形状、次元数、要素数を出力してください
print(f"形状: {matrix.shape}")
print(f"次元数: {matrix.ndim}")
print(f"要素数: {matrix.numel()}")
print(f"データ型: {matrix.dtype}")
`,
    solutionCode: `import torch

# 3x4の行列（全て1.0）を作成してください
matrix = torch.ones(3, 4)

# 行列の形状、次元数、要素数を出力してください
print(f"形状: {matrix.shape}")
print(f"次元数: {matrix.ndim}")
print(f"要素数: {matrix.numel()}")
print(f"データ型: {matrix.dtype}")
`,
    hints: [
      "torch.ones() で全要素が1のテンソルを作成できます",
      "引数に行数と列数を指定します",
    ],
    testCases: [
      {
        id: "tc4",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "形状: torch.Size([3, 4])",
      },
      {
        id: "tc5",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "次元数: 2",
      },
      {
        id: "tc6",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "要素数: 12",
      },
    ],
  },
];
