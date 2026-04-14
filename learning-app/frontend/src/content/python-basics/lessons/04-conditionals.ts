export const content = `
# 条件分岐

## if文

条件に応じて異なる処理を実行するには **if文** を使います。

\`\`\`python
age = 20

if age >= 18:
    print("成人です")
\`\`\`

> **ポイント**: Pythonではインデント（字下げ）でブロックを表現します。通常はスペース4つを使います。

## if-else文

条件が成り立たない場合の処理は **else** で書きます。

\`\`\`python
age = 15

if age >= 18:
    print("成人です")
else:
    print("未成年です")
\`\`\`

## if-elif-else文

3つ以上の条件分岐には **elif** を使います。

\`\`\`python
score = 75

if score >= 90:
    print("A")
elif score >= 80:
    print("B")
elif score >= 70:
    print("C")
elif score >= 60:
    print("D")
else:
    print("F")
\`\`\`

## 比較演算子

| 演算子 | 意味 | 例 |
|--------|------|-----|
| \`==\` | 等しい | \`x == 5\` |
| \`!=\` | 等しくない | \`x != 5\` |
| \`>\` | より大きい | \`x > 5\` |
| \`<\` | より小さい | \`x < 5\` |
| \`>=\` | 以上 | \`x >= 5\` |
| \`<=\` | 以下 | \`x <= 5\` |

## 論理演算子

複数の条件を組み合わせるには **and**, **or**, **not** を使います。

\`\`\`python
age = 25
income = 300

if age >= 20 and income >= 200:
    print("条件を満たしています")

if age < 18 or income < 100:
    print("条件を満たしていません")
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
