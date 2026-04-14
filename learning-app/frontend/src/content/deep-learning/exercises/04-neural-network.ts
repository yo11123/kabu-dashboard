import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-04-01",
    title: "nn.Moduleでモデルを定義",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn

# 問題: 以下の仕様でニューラルネットワークを定義してください
# - 入力層: 20次元
# - 隠れ層1: 64ニューロン + ReLU活性化
# - 隠れ層2: 32ニューロン + ReLU活性化
# - 出力層: 5次元（5クラス分類）

class MyNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        # ここに層を定義してください
        pass

    def forward(self, x):
        # ここに順伝播を定義してください
        pass

# モデルの作成とテスト
model = MyNetwork()

# テスト入力
x = torch.randn(4, 20)  # バッチサイズ4, 入力20次元
output = model(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")

# パラメータ数の計算
total_params = sum(p.numel() for p in model.parameters())
print(f"パラメータ総数: {total_params}")
`,
    solutionCode: `import torch
import torch.nn as nn

# 問題: 以下の仕様でニューラルネットワークを定義してください
# - 入力層: 20次元
# - 隠れ層1: 64ニューロン + ReLU活性化
# - 隠れ層2: 32ニューロン + ReLU活性化
# - 出力層: 5次元（5クラス分類）

class MyNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(20, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 5)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x

# モデルの作成とテスト
model = MyNetwork()

# テスト入力
x = torch.randn(4, 20)  # バッチサイズ4, 入力20次元
output = model(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")

# パラメータ数の計算
total_params = sum(p.numel() for p in model.parameters())
print(f"パラメータ総数: {total_params}")
`,
    hints: [
      "nn.Linear(入力次元, 出力次元) で全結合層を定義します",
      "nn.ReLU() で活性化関数を定義します",
      "forward() メソッドで各層を順番に適用します",
      "出力層にはReLUを適用しません",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "入力形状: torch.Size([4, 20])",
      },
      {
        type: "stdout",
        expected: "出力形状: torch.Size([4, 5])",
      },
      {
        type: "stdout",
        expected: "パラメータ総数: 3493",
      },
    ],
  },
  {
    id: "dl-04-02",
    title: "nn.Sequentialでモデル構築",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn

# 問題: nn.Sequentialを使って以下のモデルを構築してください
# - Linear(10, 32) -> ReLU -> Dropout(0.3) -> Linear(32, 16) -> ReLU -> Linear(16, 1)

model = nn.Sequential(
    # ここにコードを書く
)

# テスト
x = torch.randn(8, 10)
model.eval()  # Dropoutを無効化してテスト
output = model(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")
print(f"層の数: {len(model)}")
`,
    solutionCode: `import torch
import torch.nn as nn

# 問題: nn.Sequentialを使って以下のモデルを構築してください
# - Linear(10, 32) -> ReLU -> Dropout(0.3) -> Linear(32, 16) -> ReLU -> Linear(16, 1)

model = nn.Sequential(
    nn.Linear(10, 32),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(32, 16),
    nn.ReLU(),
    nn.Linear(16, 1),
)

# テスト
x = torch.randn(8, 10)
model.eval()  # Dropoutを無効化してテスト
output = model(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")
print(f"層の数: {len(model)}")
`,
    hints: [
      "nn.Sequential() の中に層をカンマ区切りで並べます",
      "nn.Dropout(確率) でドロップアウト層を追加します",
      "6つの層（Linear, ReLU, Dropout, Linear, ReLU, Linear）を順番に定義します",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "入力形状: torch.Size([8, 10])",
      },
      {
        type: "stdout",
        expected: "出力形状: torch.Size([8, 1])",
      },
      {
        type: "stdout",
        expected: "層の数: 6",
      },
    ],
  },
];
