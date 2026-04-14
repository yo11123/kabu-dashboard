export const content = `
# 文字列操作

## 文字列メソッド

Pythonの文字列には多くの便利なメソッドがあります。

\`\`\`python
text = "Hello, Python World!"

print(text.upper())      # HELLO, PYTHON WORLD!
print(text.lower())      # hello, python world!
print(text.title())      # Hello, Python World!
print(text.strip())      # 前後の空白を削除
print(text.replace("Python", "Java"))  # Hello, Java World!
\`\`\`

## 文字列の分割と結合

\`\`\`python
# 分割
csv_line = "りんご,バナナ,ぶどう"
fruits = csv_line.split(",")
print(fruits)  # ['りんご', 'バナナ', 'ぶどう']

# 結合
result = " / ".join(fruits)
print(result)  # りんご / バナナ / ぶどう
\`\`\`

## 文字列のスライス

\`\`\`python
text = "Python"
print(text[0])     # P
print(text[0:3])   # Pyt
print(text[-3:])   # hon
print(text[::-1])  # nohtyP（逆順）
\`\`\`

## 文字列の検索

\`\`\`python
text = "Pythonプログラミング入門"

print("Python" in text)      # True
print(text.startswith("Py")) # True
print(text.endswith("入門"))  # True
print(text.find("プログラミング"))  # 6（位置）
print(text.count("ン"))      # 2（出現回数）
\`\`\`

## 文字列フォーマット

\`\`\`python
name = "太郎"
age = 25
pi = 3.14159

# f文字列
print(f"{name}は{age}歳です")

# 桁数指定
print(f"円周率: {pi:.2f}")     # 円周率: 3.14
print(f"パーセント: {0.856:.1%}")  # パーセント: 85.6%
print(f"右寄せ: {name:>10}")   # 右寄せ:       太郎
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
