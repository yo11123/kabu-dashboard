export const content = `
# 辞書の応用

## 辞書内包表記

リスト内包表記と同様に、辞書も内包表記で作成できます。

\`\`\`python
squares = {x: x ** 2 for x in range(1, 6)}
print(squares)  # {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}
\`\`\`

## get() メソッド

キーが存在しない場合にデフォルト値を返す安全なアクセス方法です。

\`\`\`python
scores = {"太郎": 85, "花子": 92}

# KeyErrorが出ない
print(scores.get("太郎", 0))   # 85
print(scores.get("次郎", 0))   # 0（デフォルト値）
\`\`\`

## setdefault() と defaultdict

\`\`\`python
# setdefault: キーがなければデフォルト値を設定
word_count = {}
words = ["apple", "banana", "apple", "cherry", "banana", "apple"]

for word in words:
    word_count[word] = word_count.get(word, 0) + 1

print(word_count)  # {'apple': 3, 'banana': 2, 'cherry': 1}
\`\`\`

## 辞書のソート

\`\`\`python
scores = {"太郎": 85, "花子": 92, "次郎": 78, "美咲": 95}

# 値でソート（降順）
sorted_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
print(sorted_scores)
# {'美咲': 95, '花子': 92, '太郎': 85, '次郎': 78}
\`\`\`

## ネストした辞書

\`\`\`python
students = {
    "太郎": {"数学": 85, "英語": 72, "国語": 90},
    "花子": {"数学": 92, "英語": 88, "国語": 85},
}

# 太郎の数学の点数
print(students["太郎"]["数学"])  # 85

# 各生徒の平均点
for name, scores in students.items():
    avg = sum(scores.values()) / len(scores)
    print(f"{name}: {avg:.1f}点")
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
