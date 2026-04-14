export const content = `
# CNN基礎

## CNNとは

畳み込みニューラルネットワーク（CNN: Convolutional Neural Network）は、画像認識に特化したニューラルネットワークです。局所的な特徴を効率的に捉える畳み込み演算を使用します。

## なぜCNNが必要か

全結合層だけで画像を処理すると以下の問題があります：

- **パラメータ数の爆発**: 28×28の画像でも784個の入力。大きな画像では膨大になる
- **空間的な情報の喪失**: ピクセル間の位置関係が失われる
- **並進不変性がない**: 画像中の物体の位置が変わると認識できない

CNNはこれらの問題を解決します。

## 畳み込み層（Conv2d）

カーネル（フィルタ）を画像上でスライドさせながら特徴量を抽出します。

\`\`\`python
import torch
import torch.nn as nn

# 畳み込み層の定義
conv = nn.Conv2d(
    in_channels=1,    # 入力チャネル数（グレースケール=1, RGB=3）
    out_channels=16,  # 出力チャネル数（フィルタの数）
    kernel_size=3,    # カーネルサイズ（3x3）
    stride=1,         # ストライド（移動幅）
    padding=1          # パディング
)

# 入力: (バッチサイズ, チャネル, 高さ, 幅)
x = torch.randn(1, 1, 28, 28)
output = conv(x)
print(f"入力形状: {x.shape}")
print(f"出力形状: {output.shape}")
\`\`\`

### 出力サイズの計算

\`\`\`
出力サイズ = (入力サイズ - カーネルサイズ + 2 * パディング) / ストライド + 1
\`\`\`

例：入力28、カーネル3、パディング1、ストライド1の場合：
\`\`\`
(28 - 3 + 2*1) / 1 + 1 = 28
\`\`\`

## プーリング層

空間サイズを縮小し、計算量を削減しつつ重要な特徴を保持します。

\`\`\`python
import torch
import torch.nn as nn

# 最大プーリング
maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
x = torch.randn(1, 16, 28, 28)
output = maxpool(x)
print(f"MaxPool後: {output.shape}")  # (1, 16, 14, 14)

# 平均プーリング
avgpool = nn.AvgPool2d(kernel_size=2, stride=2)
output2 = avgpool(x)
print(f"AvgPool後: {output2.shape}")  # (1, 16, 14, 14)
\`\`\`

## バッチ正規化

学習を安定させ、収束を早める手法です。

\`\`\`python
import torch.nn as nn

# 畳み込み層用のバッチ正規化
bn = nn.BatchNorm2d(16)  # チャネル数を指定
\`\`\`

## 基本的なCNNモデル

\`\`\`python
import torch
import torch.nn as nn

class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        # 畳み込みブロック1
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.pool = nn.MaxPool2d(2, 2)

        # 畳み込みブロック2
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)

        # 全結合層
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, 10)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        # Conv Block 1: (1, 28, 28) -> (32, 14, 14)
        x = self.pool(self.relu(self.bn1(self.conv1(x))))

        # Conv Block 2: (32, 14, 14) -> (64, 7, 7)
        x = self.pool(self.relu(self.bn2(self.conv2(x))))

        # Flatten: (64, 7, 7) -> (3136,)
        x = x.view(x.size(0), -1)

        # FC layers
        x = self.dropout(self.relu(self.fc1(x)))
        x = self.fc2(x)
        return x

model = SimpleCNN()
print(model)

# テスト
x = torch.randn(4, 1, 28, 28)
output = model(x)
print(f"出力形状: {output.shape}")  # (4, 10)
\`\`\`

## 特徴マップの可視化

畳み込み層が学習する「特徴」を理解するために、中間層の出力を可視化することが有効です。

\`\`\`python
# 中間層の出力を取得
def get_feature_maps(model, x):
    features = []
    x = model.conv1(x)
    features.append(x.detach())
    x = model.relu(model.bn1(x))
    x = model.pool(x)
    x = model.conv2(x)
    features.append(x.detach())
    return features
\`\`\`

## まとめ

CNNは畳み込み層・プーリング層・全結合層を組み合わせて、画像から階層的に特徴を抽出します。浅い層ではエッジや色などの低レベル特徴を、深い層ではより複雑で抽象的な特徴を学習します。
`;
