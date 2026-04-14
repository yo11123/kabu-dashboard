export const content = `
# 評価指標

## なぜ評価指標が重要か

モデルの性能を正しく評価するには、問題に適した評価指標を選ぶ必要があります。正解率だけでは不十分な場合が多くあります。

## 分類の評価指標

### 混同行列（Confusion Matrix）

\`\`\`python
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

cm = confusion_matrix(y_test, y_pred)
print(cm)
# [[TN, FP],
#  [FN, TP]]
\`\`\`

- **TP（True Positive）**: 正しく陽性と予測
- **TN（True Negative）**: 正しく陰性と予測
- **FP（False Positive）**: 誤って陽性と予測（第一種の過誤）
- **FN（False Negative）**: 誤って陰性と予測（第二種の過誤）

### 正解率（Accuracy）

\`\`\`
Accuracy = (TP + TN) / (TP + TN + FP + FN)
\`\`\`

\`\`\`python
from sklearn.metrics import accuracy_score
print(f"正解率: {accuracy_score(y_test, y_pred):.2f}")
\`\`\`

### 適合率（Precision）

陽性と予測したもののうち、実際に陽性だった割合。

\`\`\`
Precision = TP / (TP + FP)
\`\`\`

### 再現率（Recall）

実際に陽性のもののうち、正しく陽性と予測できた割合。

\`\`\`
Recall = TP / (TP + FN)
\`\`\`

### F1スコア

適合率と再現率の調和平均。

\`\`\`
F1 = 2 * (Precision * Recall) / (Precision + Recall)
\`\`\`

\`\`\`python
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report

print(classification_report(y_test, y_pred))
\`\`\`

### AUC-ROC

\`\`\`python
from sklearn.metrics import roc_auc_score

y_prob = model.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_prob)
print(f"AUC: {auc:.2f}")
\`\`\`

## 回帰の評価指標

### MSE（平均二乗誤差）

\`\`\`python
from sklearn.metrics import mean_squared_error
mse = mean_squared_error(y_test, y_pred)
\`\`\`

### RMSE（二乗平均平方根誤差）

\`\`\`python
import numpy as np
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
\`\`\`

### MAE（平均絶対誤差）

\`\`\`python
from sklearn.metrics import mean_absolute_error
mae = mean_absolute_error(y_test, y_pred)
\`\`\`

### R²スコア（決定係数）

\`\`\`python
from sklearn.metrics import r2_score
r2 = r2_score(y_test, y_pred)
\`\`\`

## 評価指標の選び方

| 状況 | 推奨指標 |
|------|---------|
| クラスが均衡 | 正解率 |
| クラスが不均衡 | F1スコア、AUC-ROC |
| 偽陽性を避けたい | 適合率 |
| 偽陰性を避けたい | 再現率 |
| 回帰（外れ値少ない） | MSE / RMSE |
| 回帰（外れ値多い） | MAE |

## まとめ

適切な評価指標を選ぶことは、モデル開発において非常に重要です。問題の性質とビジネス要件に基づいて、最適な指標を選択しましょう。
`;
