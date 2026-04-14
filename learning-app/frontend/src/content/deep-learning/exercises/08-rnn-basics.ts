import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-08-01",
    title: "RNNの基本操作",
    difficulty: "easy",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn

# 問題1: 以下の仕様でRNNを作成してください
# - input_size: 4
# - hidden_size: 8
# - num_layers: 1
# - batch_first: True
rnn = # ここにコードを書く

# テスト入力（バッチ2, シーケンス長5, 特徴量4）
x = torch.randn(2, 5, 4)

# 問題2: RNNに入力を通して出力と隠れ状態を取得してください
output, h_n = # ここにコードを書く

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")
print(f"最終隠れ状態形状: {h_n.shape}")

# 問題3: 最後のタイムステップの出力とh_nが一致することを確認
is_equal = torch.allclose(output[:, -1, :], h_n[0], atol=1e-6)
print(f"output[:,-1,:] == h_n[0]: {is_equal}")
`,
    solutionCode: `import torch
import torch.nn as nn

# 問題1: 以下の仕様でRNNを作成してください
# - input_size: 4
# - hidden_size: 8
# - num_layers: 1
# - batch_first: True
rnn = nn.RNN(input_size=4, hidden_size=8, num_layers=1, batch_first=True)

# テスト入力（バッチ2, シーケンス長5, 特徴量4）
x = torch.randn(2, 5, 4)

# 問題2: RNNに入力を通して出力と隠れ状態を取得してください
output, h_n = rnn(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")
print(f"最終隠れ状態形状: {h_n.shape}")

# 問題3: 最後のタイムステップの出力とh_nが一致することを確認
is_equal = torch.allclose(output[:, -1, :], h_n[0], atol=1e-6)
print(f"output[:,-1,:] == h_n[0]: {is_equal}")
`,
    hints: [
      "nn.RNN() のパラメータを指定して作成します",
      "rnn(x) で出力と隠れ状態のタプルが返されます",
      "batch_first=True の場合、入力形状は (batch, seq_len, input_size) です",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "入力形状: torch.Size([2, 5, 4])",
      },
      {
        type: "stdout",
        expected: "出力形状: torch.Size([2, 5, 8])",
      },
      {
        type: "stdout",
        expected: "最終隠れ状態形状: torch.Size([1, 2, 8])",
      },
      {
        type: "stdout",
        expected: "output[:,-1,:] == h_n[0]: True",
      },
    ],
  },
  {
    id: "dl-08-02",
    title: "RNNによるシーケンス分類モデル",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn

# 問題: RNNを使ったシーケンス分類モデルを構築してください
# - 入力: (batch, seq_len=10, input_size=3)
# - RNN: hidden_size=16, num_layers=1
# - 全結合層: 16 → 4（4クラス分類）
# - 最後のタイムステップの出力を使って分類

class RNNClassifier(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super().__init__()
        # ここにコードを書く
        pass

    def forward(self, x):
        # ここにコードを書く
        pass

# テスト
model = RNNClassifier(input_size=3, hidden_size=16, num_classes=4)

x = torch.randn(5, 10, 3)  # バッチ5, 長さ10, 特徴3
output = model(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")

total_params = sum(p.numel() for p in model.parameters())
print(f"パラメータ総数: {total_params}")
`,
    solutionCode: `import torch
import torch.nn as nn

# 問題: RNNを使ったシーケンス分類モデルを構築してください
# - 入力: (batch, seq_len=10, input_size=3)
# - RNN: hidden_size=16, num_layers=1
# - 全結合層: 16 → 4（4クラス分類）
# - 最後のタイムステップの出力を使って分類

class RNNClassifier(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super().__init__()
        self.rnn = nn.RNN(input_size=input_size, hidden_size=hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        output, h_n = self.rnn(x)
        last_output = output[:, -1, :]
        out = self.fc(last_output)
        return out

# テスト
model = RNNClassifier(input_size=3, hidden_size=16, num_classes=4)

x = torch.randn(5, 10, 3)  # バッチ5, 長さ10, 特徴3
output = model(x)

print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")

total_params = sum(p.numel() for p in model.parameters())
print(f"パラメータ総数: {total_params}")
`,
    hints: [
      "self.rnn = nn.RNN(..., batch_first=True) でRNN層を定義します",
      "self.fc = nn.Linear(hidden_size, num_classes) で全結合層を定義します",
      "forward()ではRNNの出力から最後のタイムステップ output[:, -1, :] を取り出します",
      "取り出した出力を全結合層に通して分類結果を得ます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "入力形状: torch.Size([5, 10, 3])",
      },
      {
        type: "stdout",
        expected: "出力形状: torch.Size([5, 4])",
      },
      {
        type: "stdout",
        expected: "パラメータ総数: 388",
      },
    ],
  },
];
