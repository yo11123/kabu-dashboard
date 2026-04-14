export const content = `
# ファイル入出力

## ファイルの書き込み

\`open()\` 関数でファイルを開き、\`write()\` で書き込みます。

\`\`\`python
# ファイルに書き込む
with open("test.txt", "w") as f:
    f.write("こんにちは\\n")
    f.write("Python\\n")
\`\`\`

> **ポイント**: \`with\` 文を使うと、ファイルが自動的に閉じられます。

## ファイルの読み込み

\`\`\`python
# ファイルを読み込む
with open("test.txt", "r") as f:
    content = f.read()
    print(content)

# 1行ずつ読み込む
with open("test.txt", "r") as f:
    for line in f:
        print(line.strip())
\`\`\`

## モードの種類

| モード | 説明 |
|--------|------|
| \`"r"\` | 読み込み（デフォルト） |
| \`"w"\` | 書き込み（上書き） |
| \`"a"\` | 追記 |
| \`"x"\` | 新規作成（既存ならエラー） |

## CSV処理

\`\`\`python
import csv

# CSVの読み込み
data = """名前,年齢,都市
太郎,25,東京
花子,30,大阪"""

import io
reader = csv.DictReader(io.StringIO(data))
for row in reader:
    print(f"{row['名前']} ({row['年齢']}歳) - {row['都市']}")
\`\`\`

## JSON処理

\`\`\`python
import json

# Pythonオブジェクト → JSON文字列
data = {"name": "太郎", "age": 25, "hobbies": ["読書", "映画"]}
json_str = json.dumps(data, ensure_ascii=False, indent=2)
print(json_str)

# JSON文字列 → Pythonオブジェクト
parsed = json.loads(json_str)
print(parsed["name"])  # 太郎
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
