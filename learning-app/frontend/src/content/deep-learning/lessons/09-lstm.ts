export const content = `
# LSTM

## LSTMとは

LSTM（Long Short-Term Memory）は、RNNの勾配消失問題を解決するために設計されたアーキテクチャです。「セル状態」と3つの「ゲート」を導入することで、長期的な依存関係を効果的に学習できます。

## LSTMの構造

LSTMは各タイムステップで以下の3つのゲートを使って情報の流れを制御します：

### 1. 忘却ゲート（Forget Gate）

セル状態からどの情報を忘れるかを決定します。

\`\`\`
f_t = σ(W_f * [h_{t-1}, x_t] + b_f)
\`\`\`

### 2. 入力ゲート（Input Gate）

新しい情報をどの程度セル状態に追加するかを決定します。

\`\`\`
i_t = σ(W_i * [h_{t-1}, x_t] + b_i)
C̃_t = tanh(W_C * [h_{t-1}, x_t] + b_C)
\`\`\`

### 3. 出力ゲート（Output Gate）

セル状態からどの情報を出力するかを決定します。

\`\`\`
o_t = σ(W_o * [h_{t-1}, x_t] + b_o)
h_t = o_t * tanh(C_t)
\`\`\`

### セル状態の更新

\`\`\`
C_t = f_t * C_{t-1} + i_t * C̃_t
\`\`\`

## PyTorchでのLSTM

\`\`\`python
import torch
import torch.nn as nn

lstm = nn.LSTM(
    input_size=10,
    hidden_size=20,
    num_layers=1,
    batch_first=True
)

# 入力
x = torch.randn(3, 5, 10)  # (batch, seq_len, input_size)

# 出力: output, (h_n, c_n)
output, (h_n, c_n) = lstm(x)
print(f"出力形状: {output.shape}")       # (3, 5, 20)
print(f"隠れ状態形状: {h_n.shape}")      # (1, 3, 20)
print(f"セル状態形状: {c_n.shape}")      # (1, 3, 20)
\`\`\`

## LSTMモデルの実装

### 時系列予測モデル

\`\`\`python
import torch
import torch.nn as nn

class LSTMPredictor(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # LSTM
        output, (h_n, c_n) = self.lstm(x)

        # 最後のタイムステップの出力
        last_output = output[:, -1, :]

        # 予測
        prediction = self.fc(last_output)
        return prediction

model = LSTMPredictor(
    input_size=1,
    hidden_size=64,
    num_layers=2,
    output_size=1
)
print(model)
\`\`\`

### テキスト分類モデル

\`\`\`python
import torch
import torch.nn as nn

class LSTMClassifier(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_size, num_classes):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.lstm = nn.LSTM(
            embed_dim, hidden_size,
            batch_first=True,
            bidirectional=True
        )
        self.fc = nn.Linear(hidden_size * 2, num_classes)
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        embedded = self.dropout(self.embedding(x))
        output, (h_n, c_n) = self.lstm(embedded)
        # 双方向の最終隠れ状態を結合
        hidden = torch.cat((h_n[-2], h_n[-1]), dim=1)
        out = self.fc(self.dropout(hidden))
        return out
\`\`\`

## 時系列データの準備

\`\`\`python
import torch
import numpy as np

def create_sequences(data, seq_length):
    """時系列データをシーケンスに変換"""
    sequences = []
    targets = []
    for i in range(len(data) - seq_length):
        seq = data[i:i + seq_length]
        target = data[i + seq_length]
        sequences.append(seq)
        targets.append(target)
    return torch.tensor(sequences).float(), torch.tensor(targets).float()

# サイン波のデータ
t = np.linspace(0, 100, 1000)
data = np.sin(t)

# シーケンスの作成
seq_length = 20
X, y = create_sequences(data, seq_length)
X = X.unsqueeze(-1)  # (samples, seq_length, 1)
print(f"入力形状: {X.shape}")
print(f"ターゲット形状: {y.shape}")
\`\`\`

## GRU（Gated Recurrent Unit）

LSTMの簡略版で、ゲートが2つ（リセットゲートと更新ゲート）です。LSTMより計算が軽量です。

\`\`\`python
import torch
import torch.nn as nn

gru = nn.GRU(
    input_size=10,
    hidden_size=20,
    num_layers=1,
    batch_first=True
)

x = torch.randn(3, 5, 10)
output, h_n = gru(x)  # セル状態がない
print(f"出力形状: {output.shape}")     # (3, 5, 20)
print(f"隠れ状態形状: {h_n.shape}")    # (1, 3, 20)
\`\`\`

## LSTMとRNNの比較

| 特徴 | RNN | LSTM | GRU |
|------|-----|------|-----|
| 長期依存関係 | 弱い | 強い | 強い |
| パラメータ数 | 少ない | 多い | 中程度 |
| 計算速度 | 速い | 遅い | 中程度 |
| ゲート数 | 0 | 3 | 2 |

## まとめ

LSTMはゲート機構によりRNNの勾配消失問題を解決し、長期的な依存関係を効果的に学習できます。時系列予測やテキスト分類など、シーケンスデータの処理に広く使われています。
`;
