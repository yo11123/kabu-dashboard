export const content = `
# タプルとセット

## タプル (tuple)

タプルはリストに似ていますが、一度作成すると変更できません（イミュータブル）。

\`\`\`python
# タプルの作成
point = (10, 20)
rgb = (255, 128, 0)

# 要素へのアクセス
print(point[0])  # 10
print(point[1])  # 20

# アンパック
x, y = point
print(f"x={x}, y={y}")  # x=10, y=20
\`\`\`

## タプルの活用

\`\`\`python
# 複数の値を返す関数
def min_max(numbers):
    return min(numbers), max(numbers)

minimum, maximum = min_max([3, 1, 4, 1, 5, 9])
print(f"最小: {minimum}, 最大: {maximum}")

# タプルをキーに使う（辞書のキーにできる）
locations = {
    (35.68, 139.69): "東京",
    (34.69, 135.50): "大阪",
}
print(locations[(35.68, 139.69)])  # 東京
\`\`\`

## セット (set)

セットは重複のない要素の集合です。

\`\`\`python
# セットの作成
fruits = {"りんご", "バナナ", "ぶどう", "りんご"}
print(fruits)  # {'りんご', 'バナナ', 'ぶどう'}（重複なし）

# 要素の追加・削除
fruits.add("みかん")
fruits.discard("バナナ")
\`\`\`

## セットの演算

\`\`\`python
a = {1, 2, 3, 4, 5}
b = {4, 5, 6, 7, 8}

print(a | b)   # {1, 2, 3, 4, 5, 6, 7, 8}  和集合
print(a & b)   # {4, 5}  積集合
print(a - b)   # {1, 2, 3}  差集合
print(a ^ b)   # {1, 2, 3, 6, 7, 8}  対称差
\`\`\`

## リストの重複除去

\`\`\`python
numbers = [1, 3, 2, 3, 1, 4, 2, 5]
unique = list(set(numbers))
print(sorted(unique))  # [1, 2, 3, 4, 5]
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
