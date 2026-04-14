export const content = `
# モジュールとパッケージ

## モジュールのインポート

Pythonには多くの便利な標準ライブラリがあります。

\`\`\`python
import math
print(math.pi)        # 3.141592653589793
print(math.sqrt(16))  # 4.0

import random
print(random.randint(1, 100))  # 1〜100のランダムな整数
\`\`\`

## インポートの方法

\`\`\`python
# モジュール全体をインポート
import math

# 特定の関数だけインポート
from math import sqrt, pi

# 別名をつけてインポート
import datetime as dt
now = dt.datetime.now()
print(now)
\`\`\`

## よく使う標準ライブラリ

### math - 数学関数

\`\`\`python
import math

print(math.ceil(3.2))    # 4（切り上げ）
print(math.floor(3.8))   # 3（切り捨て）
print(math.log(100, 10)) # 2.0（対数）
print(math.factorial(5))  # 120（階乗）
\`\`\`

### datetime - 日付と時刻

\`\`\`python
from datetime import datetime, timedelta

now = datetime.now()
print(now.strftime("%Y年%m月%d日"))

# 7日後
future = now + timedelta(days=7)
print(future.strftime("%Y年%m月%d日"))
\`\`\`

### collections - 便利なデータ構造

\`\`\`python
from collections import Counter, defaultdict

# Counter: 要素の出現回数を数える
words = ["apple", "banana", "apple", "cherry", "banana", "apple"]
counter = Counter(words)
print(counter.most_common(2))  # [('apple', 3), ('banana', 2)]

# defaultdict: デフォルト値付き辞書
dd = defaultdict(list)
dd["fruits"].append("りんご")
dd["fruits"].append("バナナ")
print(dd["fruits"])  # ['りんご', 'バナナ']
\`\`\`

### itertools - イテレータ操作

\`\`\`python
from itertools import combinations, permutations

# 組み合わせ
for combo in combinations([1, 2, 3], 2):
    print(combo)  # (1,2), (1,3), (2,3)
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
