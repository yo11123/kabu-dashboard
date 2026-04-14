import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-03-01",
    title: "基本的な自動微分",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `import torch

# 問題: x = 3.0 に対して y = x^3 + 2*x^2 - 5*x + 1 の勾配を計算してください
# dy/dx = 3*x^2 + 4*x - 5 なので、x=3のとき dy/dx = 27 + 12 - 5 = 34

# 1. requires_grad=True でテンソルを作成
x = # ここにコードを書く

# 2. yを計算
y = # ここにコードを書く

# 3. 逆伝播で勾配を計算
# ここにコードを書く

print(f"x = {x.item()}")
print(f"y = {y.item()}")
print(f"dy/dx = {x.grad.item()}")
`,
    solutionCode: `import torch

# 問題: x = 3.0 に対して y = x^3 + 2*x^2 - 5*x + 1 の勾配を計算してください
# dy/dx = 3*x^2 + 4*x - 5 なので、x=3のとき dy/dx = 27 + 12 - 5 = 34

# 1. requires_grad=True でテンソルを作成
x = torch.tensor(3.0, requires_grad=True)

# 2. yを計算
y = x ** 3 + 2 * x ** 2 - 5 * x + 1

# 3. 逆伝播で勾配を計算
y.backward()

print(f"x = {x.item()}")
print(f"y = {y.item()}")
print(f"dy/dx = {x.grad.item()}")
`,
    hints: [
      "torch.tensor(値, requires_grad=True) で勾配追跡を有効にします",
      "y.backward() で逆伝播を実行します",
      "計算した勾配は x.grad で取得できます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "x = 3.0",
      },
      {
        type: "stdout",
        expected: "y = 31.0",
      },
      {
        type: "stdout",
        expected: "dy/dx = 34.0",
      },
    ],
  },
  {
    id: "dl-03-02",
    title: "勾配降下法の手動実装",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `import torch

# 問題: 勾配降下法で y = (x - 3)^2 の最小値を求めてください
# 最適解は x = 3.0 です

# 初期値
x = torch.tensor(0.0, requires_grad=True)
learning_rate = 0.1

# 50回の勾配降下を実装してください
for i in range(50):
    # 1. yを計算
    y = # ここにコードを書く

    # 2. 逆伝播
    # ここにコードを書く

    # 3. 勾配降下でxを更新（with torch.no_grad()で囲む）
    # ここにコードを書く

    # 4. 勾配を初期化
    # ここにコードを書く

print(f"最適化後の x = {x.item():.4f}")
print(f"最小値 y = {((x.item() - 3) ** 2):.6f}")
`,
    solutionCode: `import torch

# 問題: 勾配降下法で y = (x - 3)^2 の最小値を求めてください
# 最適解は x = 3.0 です

# 初期値
x = torch.tensor(0.0, requires_grad=True)
learning_rate = 0.1

# 50回の勾配降下を実装してください
for i in range(50):
    # 1. yを計算
    y = (x - 3) ** 2

    # 2. 逆伝播
    y.backward()

    # 3. 勾配降下でxを更新（with torch.no_grad()で囲む）
    with torch.no_grad():
        x -= learning_rate * x.grad

    # 4. 勾配を初期化
    x.grad.zero_()

print(f"最適化後の x = {x.item():.4f}")
print(f"最小値 y = {((x.item() - 3) ** 2):.6f}")
`,
    hints: [
      "y = (x - 3) ** 2 で損失を計算します",
      "y.backward() で勾配を計算します",
      "パラメータ更新は torch.no_grad() ブロック内で行います",
      "x -= learning_rate * x.grad でパラメータを更新します",
      "x.grad.zero_() で勾配をリセットします",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "最適化後の x = 3.0000",
      },
    ],
  },
];
