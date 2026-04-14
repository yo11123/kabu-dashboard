export const content = `
# 転移学習

## 転移学習とは

転移学習（Transfer Learning）は、あるタスクで学習済みのモデルの知識を、別のタスクに活用する手法です。大規模データセットで事前学習されたモデルを使うことで、少量のデータでも高い性能を達成できます。

## なぜ転移学習が有効か

- **大規模データが不要**: 事前学習済みモデルの知識を活用
- **学習時間の短縮**: ゼロから学習するより圧倒的に速い
- **高い性能**: ImageNetなどで学習した汎用的な特徴を利用
- **少量データでも有効**: 数百枚の画像でも高精度を達成可能

## 事前学習済みモデル

PyTorchのtorchvisionには多くの事前学習済みモデルが用意されています。

\`\`\`python
import torchvision.models as models

# ResNet18の読み込み（事前学習済み）
model = models.resnet18(weights='IMAGENET1K_V1')

# 利用可能なモデル
# models.resnet50(weights='IMAGENET1K_V1')
# models.vgg16(weights='IMAGENET1K_V1')
# models.mobilenet_v2(weights='IMAGENET1K_V1')
# models.efficientnet_b0(weights='IMAGENET1K_V1')
\`\`\`

## 転移学習のアプローチ

### 1. 特徴抽出（Feature Extraction）

事前学習済みモデルの重みを固定し、最後の分類層のみを置き換えて学習します。

\`\`\`python
import torch
import torch.nn as nn
import torchvision.models as models

# 事前学習済みResNet18を読み込み
model = models.resnet18(weights='IMAGENET1K_V1')

# すべてのパラメータを固定
for param in model.parameters():
    param.requires_grad = False

# 最後の全結合層を置き換え（10クラス分類の場合）
num_features = model.fc.in_features
model.fc = nn.Linear(num_features, 10)

# 新しい層のパラメータのみが学習される
print(f"学習対象パラメータ数: {sum(p.numel() for p in model.parameters() if p.requires_grad)}")
\`\`\`

### 2. ファインチューニング（Fine-tuning）

事前学習済みモデルの一部（または全部）の重みも低い学習率で更新します。

\`\`\`python
import torch
import torch.nn as nn
import torchvision.models as models

model = models.resnet18(weights='IMAGENET1K_V1')

# 最後の全結合層を置き換え
num_features = model.fc.in_features
model.fc = nn.Linear(num_features, 10)

# 層ごとに異なる学習率を設定
optimizer = torch.optim.Adam([
    {'params': model.conv1.parameters(), 'lr': 1e-5},
    {'params': model.layer1.parameters(), 'lr': 1e-5},
    {'params': model.layer2.parameters(), 'lr': 1e-4},
    {'params': model.layer3.parameters(), 'lr': 1e-4},
    {'params': model.layer4.parameters(), 'lr': 1e-3},
    {'params': model.fc.parameters(), 'lr': 1e-2},
])
\`\`\`

## データの前処理

事前学習済みモデルを使う場合、訓練時と同じ前処理を適用する必要があります。

\`\`\`python
from torchvision import transforms

# ImageNet用の前処理
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# 訓練用（データ拡張あり）
transform_train = transforms.Compose([
    transforms.RandomResizedCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])
\`\`\`

## 完全な転移学習パイプライン

\`\`\`python
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.models as models
from torch.utils.data import DataLoader

def train_transfer_learning(train_loader, val_loader, num_classes, num_epochs=10):
    # モデルの準備
    model = models.resnet18(weights='IMAGENET1K_V1')

    # 特徴抽出層を固定
    for param in model.parameters():
        param.requires_grad = False

    # 分類層の置き換え
    model.fc = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(model.fc.in_features, num_classes)
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.fc.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

    best_acc = 0.0

    for epoch in range(num_epochs):
        # 訓練
        model.train()
        train_loss = 0
        correct = 0
        total = 0

        for inputs, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

        train_acc = 100. * correct / total

        # 検証
        model.eval()
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for inputs, labels in val_loader:
                outputs = model(inputs)
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()

        val_acc = 100. * val_correct / val_total

        print(f"Epoch {epoch+1}: Train Acc={train_acc:.2f}%, Val Acc={val_acc:.2f}%")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), 'best_transfer_model.pth')

        scheduler.step()

    return model
\`\`\`

## 転移学習のベストプラクティス

1. **データが少ない場合**: 特徴抽出アプローチを使用
2. **データがある程度ある場合**: ファインチューニングを使用
3. **類似タスクの場合**: 浅い層は固定、深い層をファインチューニング
4. **異なるタスクの場合**: より多くの層をファインチューニング
5. **学習率**: 事前学習済み層は低い学習率、新しい層は高い学習率

## まとめ

転移学習は、事前学習済みモデルの知識を活用して効率的にモデルを構築する強力な手法です。特徴抽出とファインチューニングの2つのアプローチを使い分けることで、少量のデータでも高い性能を達成できます。
`;
