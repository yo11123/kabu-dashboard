export const content = `
# リストと辞書

## リスト (list)

リストは、複数の値を順序付きで格納するデータ構造です。\`[]\` で作成します。

\`\`\`python
fruits = ["りんご", "バナナ", "ぶどう"]
numbers = [1, 2, 3, 4, 5]
mixed = [1, "hello", True, 3.14]  # 異なる型も混在可能
\`\`\`

### リストの操作

\`\`\`python
fruits = ["りんご", "バナナ", "ぶどう"]

# 要素の取得 (インデックスは0から)
print(fruits[0])   # りんご
print(fruits[-1])  # ぶどう (末尾)

# 要素の追加
fruits.append("みかん")

# 要素の削除
fruits.remove("バナナ")

# リストの長さ
print(len(fruits))  # 3
\`\`\`

## タプル (tuple)

タプルはリストに似ていますが、作成後に変更できない（イミュータブル）データ構造です。

\`\`\`python
point = (10, 20)
rgb = (255, 128, 0)

print(point[0])  # 10
\`\`\`

## 辞書 (dict)

辞書は、キーと値のペアを格納するデータ構造です。\`{}\` で作成します。

\`\`\`python
person = {
    "名前": "田中太郎",
    "年齢": 25,
    "職業": "エンジニア"
}

# 値の取得
print(person["名前"])  # 田中太郎

# 値の更新
person["年齢"] = 26

# キーと値の追加
person["趣味"] = "プログラミング"

# キーの存在確認
print("名前" in person)  # True
\`\`\`

### 辞書のループ

\`\`\`python
person = {"名前": "田中太郎", "年齢": 25}

for key, value in person.items():
    print(f"{key}: {value}")
# 名前: 田中太郎
# 年齢: 25
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
