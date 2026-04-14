export const content = `
# 機械学習入門

## 機械学習とは

機械学習（Machine Learning）とは、データからパターンを学習し、予測や判断を自動的に行うアルゴリズムの総称です。明示的にプログラムされるのではなく、データから「学ぶ」ことが特徴です。

## 機械学習の種類

### 1. 教師あり学習（Supervised Learning）
入力データとそれに対応する正解ラベルのペアを使って学習します。

- **分類（Classification）**: カテゴリを予測（例：スパムメール判定）
- **回帰（Regression）**: 連続値を予測（例：住宅価格予測）

### 2. 教師なし学習（Unsupervised Learning）
正解ラベルなしでデータの構造やパターンを発見します。

- **クラスタリング**: データをグループに分ける
- **次元削減**: データの特徴量を圧縮する

### 3. 強化学習（Reinforcement Learning）
エージェントが環境と相互作用しながら、報酬を最大化する行動を学習します。

## scikit-learn について

scikit-learn は Python で最も広く使われている機械学習ライブラリです。

\`\`\`python
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# データの分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# モデルの学習
model = LinearRegression()
model.fit(X_train, y_train)

# 予測
predictions = model.predict(X_test)
\`\`\`

## 機械学習の基本的な流れ

1. **データ収集**: 分析に必要なデータを集める
2. **データ前処理**: 欠損値処理、正規化など
3. **特徴量エンジニアリング**: モデルに適した特徴量を作成
4. **モデル選択**: 問題に適したアルゴリズムを選ぶ
5. **学習**: データを使ってモデルを訓練
6. **評価**: テストデータでモデルの性能を評価
7. **チューニング**: ハイパーパラメータを調整して性能向上

## まとめ

機械学習は、データから自動的にパターンを学習する強力な技術です。scikit-learn を使うことで、Pythonで簡単に機械学習モデルを構築できます。次のレッスンでは、データ操作の基盤となる NumPy と Pandas を学びます。
`;
