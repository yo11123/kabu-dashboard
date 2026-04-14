import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-05-01",
    title: "学習ループの実装",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn
import torch.optim as optim

# データの準備（y = 2x + 1 のデータ）
torch.manual_seed(42)
X = torch.randn(100, 1)
y = 2 * X + 1 + 0.1 * torch.randn(100, 1)

# モデルの定義
model = nn.Linear(1, 1)

# 損失関数とオプティマイザを定義してください
criterion = # ここにコードを書く（MSE損失）
optimizer = # ここにコードを書く（SGD, lr=0.1）

# 学習ループを実装してください（100エポック）
for epoch in range(100):
    # 1. 順伝播
    outputs = # ここにコードを書く

    # 2. 損失計算
    loss = # ここにコードを書く

    # 3. 勾配初期化、逆伝播、パラメータ更新
    # ここにコードを書く

# 学習結果
w = model.weight.item()
b = model.bias.item()
print(f"学習した重み: {w:.2f}")
print(f"学習したバイアス: {b:.2f}")
print(f"期待値: 重み≈2.00, バイアス≈1.00")
`,
    solutionCode: `import torch
import torch.nn as nn
import torch.optim as optim

# データの準備（y = 2x + 1 のデータ）
torch.manual_seed(42)
X = torch.randn(100, 1)
y = 2 * X + 1 + 0.1 * torch.randn(100, 1)

# モデルの定義
model = nn.Linear(1, 1)

# 損失関数とオプティマイザを定義してください
criterion = nn.MSELoss()
optimizer = optim.SGD(model.parameters(), lr=0.1)

# 学習ループを実装してください（100エポック）
for epoch in range(100):
    # 1. 順伝播
    outputs = model(X)

    # 2. 損失計算
    loss = criterion(outputs, y)

    # 3. 勾配初期化、逆伝播、パラメータ更新
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

# 学習結果
w = model.weight.item()
b = model.bias.item()
print(f"学習した重み: {w:.2f}")
print(f"学習したバイアス: {b:.2f}")
print(f"期待値: 重み≈2.00, バイアス≈1.00")
`,
    hints: [
      "nn.MSELoss() で平均二乗誤差の損失関数を作成します",
      "optim.SGD(model.parameters(), lr=0.1) でSGDオプティマイザを作成します",
      "順伝播は model(X) で実行します",
      "optimizer.zero_grad() → loss.backward() → optimizer.step() の順番が重要です",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "学習した重み: 2.0",
      },
      {
        id: "tc2",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "学習したバイアス: 1.0",
      },
    ],
  },
  {
    id: "dl-05-02",
    title: "DataLoaderの使い方",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# データの準備
torch.manual_seed(42)
X = torch.randn(200, 5)
y = (X[:, 0] * 2 + X[:, 1] * 3 + 1).unsqueeze(1)

# 問題1: TensorDatasetとDataLoaderを作成してください
# バッチサイズ32、シャッフルあり
dataset = # ここにコードを書く
dataloader = # ここにコードを書く

# モデルの定義
model = nn.Sequential(
    nn.Linear(5, 16),
    nn.ReLU(),
    nn.Linear(16, 1)
)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

# 問題2: ミニバッチ学習ループを実装してください（20エポック）
for epoch in range(20):
    total_loss = 0
    for batch_X, batch_y in dataloader:
        # ここにコードを書く
        pass

    if (epoch + 1) % 10 == 0:
        avg_loss = total_loss / len(dataloader)
        print(f"Epoch {epoch+1}, Loss: {avg_loss:.4f}")

# テスト
model.eval()
with torch.no_grad():
    test_input = torch.tensor([[1.0, 1.0, 0.0, 0.0, 0.0]])
    prediction = model(test_input)
    print(f"入力 [1,1,0,0,0] の予測値: {prediction.item():.2f}")
    print(f"期待値: {1*2 + 1*3 + 1:.2f}")
`,
    solutionCode: `import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# データの準備
torch.manual_seed(42)
X = torch.randn(200, 5)
y = (X[:, 0] * 2 + X[:, 1] * 3 + 1).unsqueeze(1)

# 問題1: TensorDatasetとDataLoaderを作成してください
# バッチサイズ32、シャッフルあり
dataset = TensorDataset(X, y)
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

# モデルの定義
model = nn.Sequential(
    nn.Linear(5, 16),
    nn.ReLU(),
    nn.Linear(16, 1)
)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

# 問題2: ミニバッチ学習ループを実装してください（20エポック）
for epoch in range(20):
    total_loss = 0
    for batch_X, batch_y in dataloader:
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    if (epoch + 1) % 10 == 0:
        avg_loss = total_loss / len(dataloader)
        print(f"Epoch {epoch+1}, Loss: {avg_loss:.4f}")

# テスト
model.eval()
with torch.no_grad():
    test_input = torch.tensor([[1.0, 1.0, 0.0, 0.0, 0.0]])
    prediction = model(test_input)
    print(f"入力 [1,1,0,0,0] の予測値: {prediction.item():.2f}")
    print(f"期待値: {1*2 + 1*3 + 1:.2f}")
`,
    hints: [
      "TensorDataset(X, y) でデータセットを作成します",
      "DataLoader(dataset, batch_size=32, shuffle=True) でデータローダーを作成します",
      "ミニバッチループ内で順伝播→損失計算→勾配初期化→逆伝播→更新を行います",
      "total_loss += loss.item() でエポック全体の損失を集計します",
    ],
    testCases: [
      {
        id: "tc3",
        description: "正しい結果が出力される",
        type: "custom",
        checkCode: `
output_lines = stdout.strip().split("\\n")
assert len(output_lines) >= 3, "出力が不足しています"
assert "Epoch 10" in output_lines[0], "Epoch 10の出力がありません"
assert "Epoch 20" in output_lines[1], "Epoch 20の出力がありません"
assert "予測値" in output_lines[2], "予測値の出力がありません"
print("PASS")
`,
      },
    ],
  },
];
