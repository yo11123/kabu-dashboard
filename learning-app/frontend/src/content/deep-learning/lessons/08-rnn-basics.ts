export const content = `
# RNN基礎

## RNNとは

リカレントニューラルネットワーク（RNN: Recurrent Neural Network）は、時系列データやシーケンスデータを処理するためのニューラルネットワークです。過去の情報を「隠れ状態」として保持し、現在の入力と組み合わせて処理します。

## RNNの仕組み

各タイムステップ \`t\` で以下の計算を行います：

\`\`\`
h_t = tanh(W_ih * x_t + W_hh * h_{t-1} + b)
\`\`\`

- \`x_t\`: 時刻tの入力
- \`h_{t-1}\`: 前の時刻の隠れ状態
- \`h_t\`: 現在の隠れ状態
- \`W_ih, W_hh\`: 重み行列
- \`b\`: バイアス

## PyTorchでのRNN

\`\`\`python
import torch
import torch.nn as nn

# 基本的なRNN
rnn = nn.RNN(
    input_size=10,    # 入力の特徴量の次元
    hidden_size=20,   # 隠れ状態の次元
    num_layers=1,     # RNN層の数
    batch_first=True  # 入力形状を (batch, seq, feature) にする
)

# 入力: (バッチサイズ, シーケンス長, 入力次元)
x = torch.randn(3, 5, 10)  # バッチ3, 長さ5, 特徴10

# 出力と最終隠れ状態
output, h_n = rnn(x)
print(f"出力形状: {output.shape}")     # (3, 5, 20)
print(f"最終隠れ状態: {h_n.shape}")    # (1, 3, 20)
\`\`\`

## RNNの出力の理解

\`\`\`python
import torch
import torch.nn as nn

rnn = nn.RNN(input_size=4, hidden_size=8, batch_first=True)
x = torch.randn(2, 3, 4)  # バッチ2, 長さ3, 特徴4

output, h_n = rnn(x)

# outputは全タイムステップの隠れ状態
# h_nは最後のタイムステップの隠れ状態
print(f"output[:, -1, :] == h_n[0]: {torch.allclose(output[:, -1, :], h_n[0])}")
\`\`\`

## 多層RNN

\`\`\`python
import torch
import torch.nn as nn

rnn = nn.RNN(
    input_size=10,
    hidden_size=20,
    num_layers=3,      # 3層のRNN
    batch_first=True,
    dropout=0.2         # 層間にDropout
)

x = torch.randn(2, 5, 10)
output, h_n = rnn(x)
print(f"出力形状: {output.shape}")     # (2, 5, 20) 最上層の出力
print(f"隠れ状態形状: {h_n.shape}")    # (3, 2, 20) 各層の最終隠れ状態
\`\`\`

## 双方向RNN

\`\`\`python
import torch
import torch.nn as nn

rnn = nn.RNN(
    input_size=10,
    hidden_size=20,
    batch_first=True,
    bidirectional=True  # 双方向
)

x = torch.randn(2, 5, 10)
output, h_n = rnn(x)
print(f"出力形状: {output.shape}")     # (2, 5, 40) 両方向を結合
print(f"隠れ状態形状: {h_n.shape}")    # (2, 2, 20) 順方向と逆方向
\`\`\`

## RNNモデルの構築例

\`\`\`python
import torch
import torch.nn as nn

class SimpleRNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.rnn = nn.RNN(
            input_size=input_size,
            hidden_size=hidden_size,
            batch_first=True
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        output, h_n = self.rnn(x)

        # 最後のタイムステップの出力を使用
        last_output = output[:, -1, :]  # (batch, hidden_size)

        # 全結合層で予測
        out = self.fc(last_output)  # (batch, output_size)
        return out

model = SimpleRNN(input_size=1, hidden_size=32, output_size=1)
print(model)
\`\`\`

## RNNの課題

### 勾配消失問題

長いシーケンスでは、逆伝播の過程で勾配が指数的に小さくなり、初期のタイムステップの学習が困難になります。

### 勾配爆発問題

逆に勾配が指数的に大きくなることもあります。これは勾配クリッピングで対処できます。

\`\`\`python
# 勾配クリッピング
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
\`\`\`

## RNNの応用

- **時系列予測**: 株価、気温、売上の予測
- **テキスト分類**: 感情分析、スパム検出
- **系列変換**: 機械翻訳（Seq2Seq）
- **テキスト生成**: 文章の自動生成

## まとめ

RNNはシーケンスデータを処理する基本的なアーキテクチャです。隠れ状態を通じて過去の情報を伝搬しますが、勾配消失問題があるため、長い依存関係の学習は困難です。次のレッスンでは、この問題を解決するLSTMについて学びます。
`;
