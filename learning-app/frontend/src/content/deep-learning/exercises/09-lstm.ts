import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-09-01",
    title: "LSTMの基本操作",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn

# 問題1: 以下の仕様でLSTMを作成してください
# - input_size: 5
# - hidden_size: 10
# - num_layers: 2
# - batch_first: True
lstm = # ここにコードを書く

# テスト入力
x = torch.randn(3, 8, 5)  # バッチ3, シーケンス長8, 特徴量5

# 問題2: LSTMに入力を通してください（出力、隠れ状態、セル状態を取得）
output, (h_n, c_n) = # ここにコードを書く

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")
print(f"隠れ状態形状: {h_n.shape}")
print(f"セル状態形状: {c_n.shape}")
`,
    solutionCode: `import torch
import torch.nn as nn

# 問題1: 以下の仕様でLSTMを作成してください
# - input_size: 5
# - hidden_size: 10
# - num_layers: 2
# - batch_first: True
lstm = nn.LSTM(input_size=5, hidden_size=10, num_layers=2, batch_first=True)

# テスト入力
x = torch.randn(3, 8, 5)  # バッチ3, シーケンス長8, 特徴量5

# 問題2: LSTMに入力を通してください（出力、隠れ状態、セル状態を取得）
output, (h_n, c_n) = lstm(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")
print(f"隠れ状態形状: {h_n.shape}")
print(f"セル状態形状: {c_n.shape}")
`,
    hints: [
      "nn.LSTM() の引数はnn.RNNとほぼ同じです",
      "LSTMの出力は output, (h_n, c_n) のタプルです（RNNと違いセル状態c_nもある）",
      "num_layers=2の場合、h_nとc_nの最初の次元は2になります",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "入力形状: torch.Size([3, 8, 5])",
      },
      {
        id: "tc2",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "出力形状: torch.Size([3, 8, 10])",
      },
      {
        id: "tc3",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "隠れ状態形状: torch.Size([2, 3, 10])",
      },
      {
        id: "tc4",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "セル状態形状: torch.Size([2, 3, 10])",
      },
    ],
  },
  {
    id: "dl-09-02",
    title: "LSTMによる時系列予測",
    difficulty: "hard",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn
import torch.optim as optim
import math

torch.manual_seed(42)

# サイン波のデータ作成
def create_sine_data(seq_length, num_samples):
    X = []
    y = []
    for i in range(num_samples):
        start = i * 0.1
        seq = [math.sin(start + j * 0.1) for j in range(seq_length + 1)]
        X.append(seq[:-1])
        y.append(seq[-1])
    X = torch.tensor(X, dtype=torch.float32).unsqueeze(-1)  # (samples, seq_len, 1)
    y = torch.tensor(y, dtype=torch.float32).unsqueeze(-1)  # (samples, 1)
    return X, y

train_X, train_y = create_sine_data(seq_length=20, num_samples=200)

# 問題: LSTM時系列予測モデルを構築して学習させてください
class LSTMPredictor(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        # ここにコードを書く（LSTM + 全結合層）
        pass

    def forward(self, x):
        # ここにコードを書く
        pass

model = LSTMPredictor(input_size=1, hidden_size=32, output_size=1)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

# 学習ループ（50エポック）
for epoch in range(50):
    model.train()
    outputs = model(train_X)
    loss = criterion(outputs, train_y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if (epoch + 1) % 25 == 0:
        print(f"Epoch {epoch+1}, Loss: {loss.item():.6f}")

# テスト
model.eval()
with torch.no_grad():
    test_X, test_y = create_sine_data(seq_length=20, num_samples=10)
    predictions = model(test_X)
    test_loss = criterion(predictions, test_y)
    print(f"テスト損失: {test_loss.item():.6f}")
    print("学習完了")
`,
    solutionCode: `import torch
import torch.nn as nn
import torch.optim as optim
import math

torch.manual_seed(42)

# サイン波のデータ作成
def create_sine_data(seq_length, num_samples):
    X = []
    y = []
    for i in range(num_samples):
        start = i * 0.1
        seq = [math.sin(start + j * 0.1) for j in range(seq_length + 1)]
        X.append(seq[:-1])
        y.append(seq[-1])
    X = torch.tensor(X, dtype=torch.float32).unsqueeze(-1)
    y = torch.tensor(y, dtype=torch.float32).unsqueeze(-1)
    return X, y

train_X, train_y = create_sine_data(seq_length=20, num_samples=200)

# 問題: LSTM時系列予測モデルを構築して学習させてください
class LSTMPredictor(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        output, (h_n, c_n) = self.lstm(x)
        last_output = output[:, -1, :]
        prediction = self.fc(last_output)
        return prediction

model = LSTMPredictor(input_size=1, hidden_size=32, output_size=1)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

# 学習ループ（50エポック）
for epoch in range(50):
    model.train()
    outputs = model(train_X)
    loss = criterion(outputs, train_y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if (epoch + 1) % 25 == 0:
        print(f"Epoch {epoch+1}, Loss: {loss.item():.6f}")

# テスト
model.eval()
with torch.no_grad():
    test_X, test_y = create_sine_data(seq_length=20, num_samples=10)
    predictions = model(test_X)
    test_loss = criterion(predictions, test_y)
    print(f"テスト損失: {test_loss.item():.6f}")
    print("学習完了")
`,
    hints: [
      "self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True) でLSTM層を定義",
      "self.fc = nn.Linear(hidden_size, output_size) で出力層を定義",
      "forward() ではLSTMの出力から最後のタイムステップを取り出し、全結合層に通します",
      "output[:, -1, :] で最後のタイムステップの出力を取得します",
    ],
    testCases: [
      {
        id: "tc5",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "学習完了",
      },
    ],
  },
];
