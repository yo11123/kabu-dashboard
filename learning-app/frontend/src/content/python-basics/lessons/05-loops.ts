export const content = `
# 繰り返し処理

## for文

**for文** はシーケンス（リストや範囲）の要素を一つずつ取り出して処理を繰り返します。

\`\`\`python
fruits = ["りんご", "バナナ", "ぶどう"]

for fruit in fruits:
    print(fruit)
# りんご
# バナナ
# ぶどう
\`\`\`

## range() 関数

数値の範囲で繰り返す場合は \`range()\` を使います。

\`\`\`python
# 0から4まで
for i in range(5):
    print(i)  # 0, 1, 2, 3, 4

# 1から10まで
for i in range(1, 11):
    print(i)  # 1, 2, ..., 10

# 2ずつ増加
for i in range(0, 10, 2):
    print(i)  # 0, 2, 4, 6, 8
\`\`\`

## while文

**while文** は条件が真である間、処理を繰り返します。

\`\`\`python
count = 0

while count < 5:
    print(count)
    count += 1
# 0, 1, 2, 3, 4
\`\`\`

## break と continue

- **break**: ループを途中で終了する
- **continue**: 現在の繰り返しをスキップして次へ

\`\`\`python
for i in range(10):
    if i == 5:
        break      # 5で終了
    print(i)       # 0, 1, 2, 3, 4

for i in range(10):
    if i % 2 == 0:
        continue   # 偶数をスキップ
    print(i)       # 1, 3, 5, 7, 9
\`\`\`

## リスト内包表記

リスト内包表記を使うと、ループを簡潔に書けます。

\`\`\`python
# 通常のfor文
squares = []
for i in range(1, 6):
    squares.append(i ** 2)

# リスト内包表記（同じ結果）
squares = [i ** 2 for i in range(1, 6)]
print(squares)  # [1, 4, 9, 16, 25]

# 条件付きリスト内包表記
evens = [i for i in range(1, 11) if i % 2 == 0]
print(evens)  # [2, 4, 6, 8, 10]
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
