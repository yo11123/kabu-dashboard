import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-06-01",
    title: "畳み込み層の理解",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn

# 問題1: 以下の仕様で畳み込み層を作成してください
# - 入力チャネル: 3（RGB画像）
# - 出力チャネル: 16
# - カーネルサイズ: 3
# - パディング: 1
conv = # ここにコードを書く

# 問題2: MaxPool2dを作成してください（カーネル2, ストライド2）
pool = # ここにコードを書く

# テスト入力（バッチ1, RGB, 32x32）
x = torch.randn(1, 3, 32, 32)

# 畳み込み適用
out1 = conv(x)
print(f"入力形状: {x.shape}")
print(f"Conv2d後: {out1.shape}")

# プーリング適用
out2 = pool(out1)
print(f"MaxPool後: {out2.shape}")

# 出力サイズの計算を確認
# Conv2d: (32 - 3 + 2*1) / 1 + 1 = 32
# MaxPool: 32 / 2 = 16
`,
    solutionCode: `import torch
import torch.nn as nn

# 問題1: 以下の仕様で畳み込み層を作成してください
# - 入力チャネル: 3（RGB画像）
# - 出力チャネル: 16
# - カーネルサイズ: 3
# - パディング: 1
conv = nn.Conv2d(3, 16, kernel_size=3, padding=1)

# 問題2: MaxPool2dを作成してください（カーネル2, ストライド2）
pool = nn.MaxPool2d(kernel_size=2, stride=2)

# テスト入力（バッチ1, RGB, 32x32）
x = torch.randn(1, 3, 32, 32)

# 畳み込み適用
out1 = conv(x)
print(f"入力形状: {x.shape}")
print(f"Conv2d後: {out1.shape}")

# プーリング適用
out2 = pool(out1)
print(f"MaxPool後: {out2.shape}")

# 出力サイズの計算を確認
# Conv2d: (32 - 3 + 2*1) / 1 + 1 = 32
# MaxPool: 32 / 2 = 16
`,
    hints: [
      "nn.Conv2d(in_channels, out_channels, kernel_size, padding) で畳み込み層を作成します",
      "nn.MaxPool2d(kernel_size, stride) でプーリング層を作成します",
      "padding=1, kernel_size=3 で入力と出力の空間サイズが同じになります",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "入力形状: torch.Size([1, 3, 32, 32])",
      },
      {
        id: "tc2",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "Conv2d後: torch.Size([1, 16, 32, 32])",
      },
      {
        id: "tc3",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "MaxPool後: torch.Size([1, 16, 16, 16])",
      },
    ],
  },
  {
    id: "dl-06-02",
    title: "簡単なCNNモデルの構築",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn
import torch.nn.functional as F

# 問題: 以下の仕様でCNNモデルを構築してください
# 入力: 1チャネル, 28x28画像
# Conv1: 1→16チャネル, kernel=3, padding=1 → ReLU → MaxPool(2,2) → 14x14
# Conv2: 16→32チャネル, kernel=3, padding=1 → ReLU → MaxPool(2,2) → 7x7
# Flatten → Linear(32*7*7, 128) → ReLU → Linear(128, 10)

class MyCNN(nn.Module):
    def __init__(self):
        super().__init__()
        # ここに層を定義してください
        pass

    def forward(self, x):
        # ここに順伝播を定義してください
        pass

# テスト
model = MyCNN()
x = torch.randn(2, 1, 28, 28)
output = model(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")

total_params = sum(p.numel() for p in model.parameters())
print(f"パラメータ総数: {total_params}")
`,
    solutionCode: `import torch
import torch.nn as nn
import torch.nn.functional as F

# 問題: 以下の仕様でCNNモデルを構築してください
# 入力: 1チャネル, 28x28画像
# Conv1: 1→16チャネル, kernel=3, padding=1 → ReLU → MaxPool(2,2) → 14x14
# Conv2: 16→32チャネル, kernel=3, padding=1 → ReLU → MaxPool(2,2) → 7x7
# Flatten → Linear(32*7*7, 128) → ReLU → Linear(128, 10)

class MyCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(32 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

# テスト
model = MyCNN()
x = torch.randn(2, 1, 28, 28)
output = model(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")

total_params = sum(p.numel() for p in model.parameters())
print(f"パラメータ総数: {total_params}")
`,
    hints: [
      "Conv2dの後にReLU、MaxPoolを順番に適用します",
      "Flattenは x.view(x.size(0), -1) で実現できます",
      "全結合層の入力サイズは 32 * 7 * 7 = 1568 です",
      "F.relu() は関数型のReLUで、forward内で直接使えます",
    ],
    testCases: [
      {
        id: "tc4",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "入力形状: torch.Size([2, 1, 28, 28])",
      },
      {
        id: "tc5",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "出力形状: torch.Size([2, 10])",
      },
      {
        id: "tc6",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "パラメータ総数: 206922",
      },
    ],
  },
];
