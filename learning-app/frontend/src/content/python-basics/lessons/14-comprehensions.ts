export const content = `
# 内包表記とジェネレータ

## リスト内包表記（復習）

\`\`\`python
squares = [x ** 2 for x in range(1, 6)]
print(squares)  # [1, 4, 9, 16, 25]

# 条件付き
evens = [x for x in range(20) if x % 2 == 0]
print(evens)  # [0, 2, 4, ..., 18]
\`\`\`

## ネストした内包表記

\`\`\`python
# 2重ループの内包表記
matrix = [[i * j for j in range(1, 4)] for i in range(1, 4)]
print(matrix)
# [[1, 2, 3], [2, 4, 6], [3, 6, 9]]

# 行列をフラットにする
flat = [x for row in matrix for x in row]
print(flat)  # [1, 2, 3, 2, 4, 6, 3, 6, 9]
\`\`\`

## 辞書内包表記

\`\`\`python
# キーと値を入れ替え
original = {"a": 1, "b": 2, "c": 3}
reversed_dict = {v: k for k, v in original.items()}
print(reversed_dict)  # {1: 'a', 2: 'b', 3: 'c'}
\`\`\`

## セット内包表記

\`\`\`python
text = "hello world"
unique_chars = {ch for ch in text if ch != " "}
print(sorted(unique_chars))
\`\`\`

## ジェネレータ式

大量データを扱う場合、リストではなくジェネレータを使うとメモリ効率が良くなります。

\`\`\`python
# ジェネレータ式（()を使う）
gen = (x ** 2 for x in range(1000000))

# メモリを節約しつつ合計を計算
total = sum(x ** 2 for x in range(1, 101))
print(total)  # 338350
\`\`\`

## map, filter, reduce

\`\`\`python
numbers = [1, 2, 3, 4, 5]

# map: 各要素に関数を適用
doubled = list(map(lambda x: x * 2, numbers))
print(doubled)  # [2, 4, 6, 8, 10]

# filter: 条件に合う要素を抽出
odds = list(filter(lambda x: x % 2 != 0, numbers))
print(odds)  # [1, 3, 5]

# reduce: 累積処理
from functools import reduce
product = reduce(lambda x, y: x * y, numbers)
print(product)  # 120
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
