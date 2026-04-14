"""
Python学習 — インタラクティブなプログラミング学習ページ
"""
import streamlit as st
import io
import sys
import traceback
import json

# ─── コース・レッスン・演習データ ───

COURSES = [
    {
        "id": "python-basics",
        "title": "Python基礎",
        "icon": ":material/code:",
        "color": "#d4af37",
        "lessons": [
            {
                "id": "01",
                "title": "はじめてのPython",
                "content": """
## はじめてのPython

プログラミングの第一歩は、画面にテキストを表示することです。Pythonでは **print()** 関数を使います。

```python
print("Hello, World!")
```

### 文字列とは
文字列はダブルクォーテーション `""` またはシングルクォーテーション `''` で囲みます。

### f文字列（フォーマット文字列）
変数の値を埋め込むには **f文字列** を使います。
```python
name = "太郎"
print(f"こんにちは、{name}さん!")
```
""",
                "exercises": [
                    {
                        "id": "hello",
                        "title": "文字列を出力しよう",
                        "difficulty": "初級",
                        "description": '`print()` を使って **「こんにちは、Python!」** と出力しましょう。',
                        "starter": '# "こんにちは、Python!" と出力してみましょう\n',
                        "solution": 'print("こんにちは、Python!")',
                        "check": lambda out: "こんにちは、Python!" in out,
                        "hints": ["print() 関数を使います", '文字列は "" で囲みます'],
                    },
                    {
                        "id": "fstring",
                        "title": "名前を表示しよう",
                        "difficulty": "初級",
                        "description": '変数 `name` に名前を代入し、**「私の名前は〇〇です」** と出力しましょう。',
                        "starter": 'name = ""\nprint()',
                        "solution": 'name = "太郎"\nprint(f"私の名前は{name}です")',
                        "check": lambda out: "私の名前は" in out and "です" in out,
                        "hints": ["name変数に文字列を代入", 'f"私の名前は{name}です"'],
                    },
                ],
            },
            {
                "id": "02",
                "title": "変数とデータ型",
                "content": """
## 変数とデータ型

### 変数とは
変数は、データを保存するための「名前付きの箱」です。

```python
x = 10        # 整数 (int)
name = "太郎"  # 文字列 (str)
pi = 3.14     # 浮動小数点数 (float)
flag = True   # 真偽値 (bool)
```

### 型の確認
`type()` 関数で変数のデータ型を確認できます。

```python
print(type(42))     # <class 'int'>
print(type(3.14))   # <class 'float'>
print(type("hello")) # <class 'str'>
```

### 演算子
```python
a, b = 10, 3
print(a + b)   # 13 (足し算)
print(a - b)   # 7  (引き算)
print(a * b)   # 30 (掛け算)
print(a / b)   # 3.33... (割り算)
print(a // b)  # 3  (整数除算)
print(a % b)   # 1  (余り)
print(a ** b)  # 1000 (べき乗)
```
""",
                "exercises": [
                    {
                        "id": "calc",
                        "title": "合計を計算しよう",
                        "difficulty": "初級",
                        "description": "変数 `x` に10、`y` に20を代入し、合計を出力しましょう。",
                        "starter": "# x に 10、y に 20 を代入し、合計を出力\n",
                        "solution": "x = 10\ny = 20\nprint(x + y)",
                        "check": lambda out: "30" in out,
                        "hints": ["x = 10, y = 20 と書きます", "print(x + y) で合計を出力"],
                    },
                    {
                        "id": "types",
                        "title": "データ型を確認しよう",
                        "difficulty": "初級",
                        "description": "4つの変数の型を `type()` で出力しましょう。",
                        "starter": 'a = 42\nb = 3.14\nc = "hello"\nd = True\n\n# type() で出力してください\n',
                        "solution": 'a = 42\nb = 3.14\nc = "hello"\nd = True\nprint(type(a))\nprint(type(b))\nprint(type(c))\nprint(type(d))',
                        "check": lambda out: "int" in out and "float" in out and "str" in out and "bool" in out,
                        "hints": ["print(type(a)) のように書きます"],
                    },
                ],
            },
            {
                "id": "03",
                "title": "リストと辞書",
                "content": """
## リストと辞書

### リスト (list)
```python
fruits = ["りんご", "バナナ", "ぶどう"]
fruits.append("みかん")  # 追加
print(fruits[0])  # りんご
print(len(fruits))  # 4
```

### 辞書 (dict)
```python
person = {"名前": "田中太郎", "年齢": 25}
print(person["名前"])  # 田中太郎
person["趣味"] = "プログラミング"
```

### リストのスライス
```python
numbers = [0, 1, 2, 3, 4, 5]
print(numbers[1:4])  # [1, 2, 3]
print(numbers[:3])   # [0, 1, 2]
print(numbers[-2:])  # [4, 5]
```
""",
                "exercises": [
                    {
                        "id": "list",
                        "title": "リストを操作しよう",
                        "difficulty": "初級",
                        "description": 'fruitsリストに `"みかん"` を追加し、リストの長さを出力しましょう。',
                        "starter": 'fruits = ["りんご", "バナナ", "ぶどう"]\n\n# "みかん" を追加し、長さを出力\n',
                        "solution": 'fruits = ["りんご", "バナナ", "ぶどう"]\nfruits.append("みかん")\nprint(len(fruits))',
                        "check": lambda out: "4" in out,
                        "hints": ["append() で追加", "len() で長さ取得"],
                    },
                    {
                        "id": "dict",
                        "title": "辞書を作ろう",
                        "difficulty": "中級",
                        "description": '辞書 person を作成し **「名前: 田中太郎, 年齢: 25」** と出力しましょう。',
                        "starter": "# 辞書を作成して出力しましょう\n",
                        "solution": 'person = {"名前": "田中太郎", "年齢": 25}\nprint(f"名前: {person[\'名前\']}, 年齢: {person[\'年齢\']}")',
                        "check": lambda out: "名前: 田中太郎" in out and "年齢: 25" in out,
                        "hints": ['{"キー": 値} で作成', 'person["名前"] でアクセス'],
                    },
                ],
            },
            {
                "id": "04",
                "title": "条件分岐",
                "content": """
## 条件分岐

### if文
```python
age = 20
if age >= 18:
    print("成人です")
else:
    print("未成年です")
```

### if-elif-else
```python
score = 75
if score >= 90:
    print("A")
elif score >= 80:
    print("B")
elif score >= 70:
    print("C")
else:
    print("F")
```

### 比較演算子
`==`, `!=`, `>`, `<`, `>=`, `<=`

### 論理演算子
`and`, `or`, `not`
""",
                "exercises": [
                    {
                        "id": "judge",
                        "title": "点数を判定しよう",
                        "difficulty": "初級",
                        "description": "80以上→優秀、60以上→合格、それ以外→不合格 を返す関数を作りましょう。",
                        "starter": 'def judge(score):\n    # ここにコードを書いてください\n    pass\n\nprint(judge(85))\nprint(judge(65))\nprint(judge(40))',
                        "solution": 'def judge(score):\n    if score >= 80:\n        return "優秀"\n    elif score >= 60:\n        return "合格"\n    else:\n        return "不合格"\n\nprint(judge(85))\nprint(judge(65))\nprint(judge(40))',
                        "check": lambda out: "優秀" in out and "合格" in out and "不合格" in out,
                        "hints": ["if, elif, else を使います", "大きい数値の条件から順に判定"],
                    },
                ],
            },
            {
                "id": "05",
                "title": "繰り返し処理",
                "content": """
## 繰り返し処理

### for文
```python
for i in range(5):
    print(i)  # 0, 1, 2, 3, 4

for fruit in ["りんご", "バナナ"]:
    print(fruit)
```

### while文
```python
count = 0
while count < 5:
    print(count)
    count += 1
```

### リスト内包表記
```python
squares = [x ** 2 for x in range(1, 6)]
print(squares)  # [1, 4, 9, 16, 25]

evens = [x for x in range(20) if x % 2 == 0]
```
""",
                "exercises": [
                    {
                        "id": "forsum",
                        "title": "合計を計算しよう",
                        "difficulty": "初級",
                        "description": "for文で1から10までの合計を計算して出力しましょう。",
                        "starter": "total = 0\n# for文で1から10まで合計\n\nprint(total)",
                        "solution": "total = 0\nfor i in range(1, 11):\n    total += i\nprint(total)",
                        "check": lambda out: "55" in out,
                        "hints": ["range(1, 11) で1〜10", "total += i で加算"],
                    },
                    {
                        "id": "listcomp",
                        "title": "リスト内包表記を使おう",
                        "difficulty": "中級",
                        "description": "1から20までの偶数のリストを内包表記で作り出力しましょう。",
                        "starter": "evens = []  # 内包表記に書き換え\nprint(evens)",
                        "solution": "evens = [i for i in range(1, 21) if i % 2 == 0]\nprint(evens)",
                        "check": lambda out: "[2, 4, 6, 8, 10, 12, 14, 16, 18, 20]" in out,
                        "hints": ["[式 for 変数 in range() if 条件]", "i % 2 == 0 で偶数判定"],
                    },
                ],
            },
            {
                "id": "06",
                "title": "関数",
                "content": """
## 関数

### 関数の定義
```python
def greet(name):
    return f"こんにちは、{name}さん!"

print(greet("太郎"))
```

### デフォルト引数
```python
def greet(name, greeting="こんにちは"):
    return f"{greeting}、{name}さん!"
```

### lambda式
```python
square = lambda x: x ** 2
numbers = sorted([3, 1, 4], key=lambda x: -x)
```
""",
                "exercises": [
                    {
                        "id": "bmi",
                        "title": "BMIを計算する関数",
                        "difficulty": "初級",
                        "description": "体重(kg)と身長(m)からBMIを計算し、小数点1桁で返す関数を作りましょう。",
                        "starter": "def calc_bmi(weight, height):\n    pass\n\nprint(calc_bmi(70, 1.75))\nprint(calc_bmi(55, 1.60))",
                        "solution": "def calc_bmi(weight, height):\n    return round(weight / (height ** 2), 1)\n\nprint(calc_bmi(70, 1.75))\nprint(calc_bmi(55, 1.60))",
                        "check": lambda out: "22.9" in out and "21.5" in out,
                        "hints": ["BMI = weight / (height ** 2)", "round(value, 1) で丸め"],
                    },
                ],
            },
            {
                "id": "07",
                "title": "クラスとオブジェクト",
                "content": """
## クラスとオブジェクト

```python
class Dog:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def bark(self):
        return f"{self.name}がワンワン！"

dog = Dog("ポチ", 3)
print(dog.bark())
```

### 継承
```python
class Animal:
    def __init__(self, name):
        self.name = name

class Cat(Animal):
    def speak(self):
        return f"{self.name}: ニャー"
```
""",
                "exercises": [
                    {
                        "id": "bank",
                        "title": "銀行口座クラスを作ろう",
                        "difficulty": "中級",
                        "description": "入金・出金・残高表示ができるBankAccountクラスを作りましょう。",
                        "starter": 'class BankAccount:\n    pass\n\naccount = BankAccount("太郎", 1000)\naccount.deposit(500)\nprint(account)\naccount.withdraw(200)\nprint(account)\naccount.withdraw(2000)\nprint(account)',
                        "solution": 'class BankAccount:\n    def __init__(self, owner, balance=0):\n        self.owner = owner\n        self.balance = balance\n    def deposit(self, amount):\n        self.balance += amount\n    def withdraw(self, amount):\n        if amount > self.balance:\n            print("残高不足です")\n        else:\n            self.balance -= amount\n    def __str__(self):\n        return f"{self.owner}: {self.balance}円"\n\naccount = BankAccount("太郎", 1000)\naccount.deposit(500)\nprint(account)\naccount.withdraw(200)\nprint(account)\naccount.withdraw(2000)\nprint(account)',
                        "check": lambda out: "1500" in out and "1300" in out and "残高不足" in out,
                        "hints": ["__init__でowner,balanceを初期化", "withdrawで残高チェック"],
                    },
                ],
            },
            {
                "id": "08",
                "title": "例外処理",
                "content": """
## 例外処理

### try-except
```python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("ゼロでは割れません")
```

### 複数の例外
```python
try:
    value = int("hello")
except ValueError:
    print("変換エラー")
except TypeError:
    print("型エラー")
```

### finally
```python
try:
    num = int("42")
except ValueError:
    print("エラー")
else:
    print(f"成功: {num}")
finally:
    print("処理完了")
```
""",
                "exercises": [
                    {
                        "id": "safediv",
                        "title": "安全な除算関数",
                        "difficulty": "初級",
                        "description": "ゼロ除算と型エラーを安全に処理する除算関数を作りましょう。",
                        "starter": 'def safe_divide(a, b):\n    pass\n\nprint(safe_divide(10, 3))\nprint(safe_divide(10, 0))\nprint(safe_divide("10", 2))',
                        "solution": 'def safe_divide(a, b):\n    try:\n        return round(a / b, 2)\n    except ZeroDivisionError:\n        print("エラー: ゼロ除算")\n        return None\n    except TypeError:\n        print("エラー: 型不正")\n        return None\n\nprint(safe_divide(10, 3))\nprint(safe_divide(10, 0))\nprint(safe_divide("10", 2))',
                        "check": lambda out: "3.33" in out and "エラー" in out and "None" in out,
                        "hints": ["try-exceptで例外をキャッチ", "ZeroDivisionErrorとTypeError"],
                    },
                ],
            },
        ],
    },
]


# ─── コード実行エンジン ───

def execute_code(code: str, timeout: int = 10) -> tuple[str, str]:
    """ユーザーコードを安全に実行して stdout, stderr を返す"""
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = captured_out = io.StringIO()
    sys.stderr = captured_err = io.StringIO()
    try:
        exec(code, {"__builtins__": __builtins__}, {})
    except Exception:
        captured_err.write(traceback.format_exc())
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
    return captured_out.getvalue(), captured_err.getvalue()


# ─── メインUI ───

# セッション初期化
if "learning_progress" not in st.session_state:
    st.session_state.learning_progress = {}
if "learning_course" not in st.session_state:
    st.session_state.learning_course = None
if "learning_lesson" not in st.session_state:
    st.session_state.learning_lesson = None

course_data = COURSES[0]  # 現時点ではPython基礎のみ


def show_course_home():
    """コース一覧画面"""
    st.markdown(
        '<h1 style="font-family:Cormorant Garamond,serif; color:#d4af37;">'
        ':material/school: Python学習</h1>',
        unsafe_allow_html=True,
    )
    st.caption("ブラウザ上でPythonコードを書いて実行しながら学べます")
    st.divider()

    cols = st.columns(2)
    for i, lesson in enumerate(course_data["lessons"]):
        lid = f"python-basics/{lesson['id']}"
        completed = st.session_state.learning_progress.get(lid, False)
        with cols[i % 2]:
            icon = "✅" if completed else f"**{i + 1}**"
            if st.button(
                f"{icon}　{lesson['title']}",
                key=f"lesson_{lesson['id']}",
                use_container_width=True,
            ):
                st.session_state.learning_lesson = lesson["id"]
                st.rerun()

    # 進捗
    total = len(course_data["lessons"])
    done = sum(
        1
        for l in course_data["lessons"]
        if st.session_state.learning_progress.get(f"python-basics/{l['id']}", False)
    )
    st.divider()
    st.progress(done / total if total > 0 else 0, text=f"進捗: {done}/{total} レッスン完了")


def show_lesson(lesson_data):
    """レッスン画面"""
    lesson_idx = next(
        i for i, l in enumerate(course_data["lessons"]) if l["id"] == lesson_data["id"]
    )

    # ヘッダー
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(
            f'<h1 style="font-family:Cormorant Garamond,serif; color:#d4af37;">'
            f'{lesson_data["title"]}</h1>',
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("← 一覧へ", key="back_to_list"):
            st.session_state.learning_lesson = None
            st.rerun()

    # レッスン内容
    st.markdown(lesson_data["content"])

    # 演習問題
    st.divider()
    st.markdown(
        '<h2 style="font-family:Cormorant Garamond,serif; color:#d4af37;">'
        "演習問題</h2>",
        unsafe_allow_html=True,
    )

    all_passed = True
    for ex in lesson_data["exercises"]:
        ex_key = f"code_{lesson_data['id']}_{ex['id']}"
        result_key = f"result_{lesson_data['id']}_{ex['id']}"
        passed_key = f"passed_{lesson_data['id']}_{ex['id']}"

        is_passed = st.session_state.get(passed_key, False)
        badge = "　✅ 完了" if is_passed else ""

        with st.expander(f"**{ex['title']}**　`{ex['difficulty']}`{badge}", expanded=not is_passed):
            st.markdown(ex["description"])

            # コードエディタ
            code = st.text_area(
                "コード",
                value=st.session_state.get(ex_key, ex["starter"]),
                height=180,
                key=ex_key,
                label_visibility="collapsed",
            )

            # ボタン行
            btn_cols = st.columns([1, 1, 1, 2])
            with btn_cols[0]:
                run_clicked = st.button("▶ 実行", key=f"run_{ex['id']}", type="primary")
            with btn_cols[1]:
                check_clicked = st.button("✓ 解答チェック", key=f"check_{ex['id']}")
            with btn_cols[2]:
                if st.button("💡 ヒント", key=f"hint_{ex['id']}"):
                    for i, h in enumerate(ex["hints"]):
                        st.info(f"ヒント{i + 1}: {h}")
            with btn_cols[3]:
                with st.popover("📖 解答を見る"):
                    st.code(ex["solution"], language="python")

            # 実行
            if run_clicked or check_clicked:
                stdout, stderr = execute_code(code)
                st.session_state[result_key] = (stdout, stderr)

                if stdout:
                    st.code(stdout, language="text")
                if stderr:
                    st.error(stderr)

                # 解答チェック
                if check_clicked:
                    if stderr:
                        st.error("❌ コードにエラーがあります")
                    elif ex["check"](stdout):
                        st.success("🎉 正解です！")
                        st.session_state[passed_key] = True
                        st.balloons()
                    else:
                        st.warning("❌ 期待した出力と異なります。もう一度試してみましょう。")

            elif result_key in st.session_state:
                stdout, stderr = st.session_state[result_key]
                if stdout:
                    st.code(stdout, language="text")
                if stderr:
                    st.error(stderr)

        if not st.session_state.get(passed_key, False):
            all_passed = False

    # レッスン完了判定
    lid = f"python-basics/{lesson_data['id']}"
    if all_passed and not st.session_state.learning_progress.get(lid, False):
        st.session_state.learning_progress[lid] = True

    # ナビゲーション
    st.divider()
    nav_cols = st.columns(3)
    with nav_cols[0]:
        if lesson_idx > 0:
            prev_lesson = course_data["lessons"][lesson_idx - 1]
            if st.button(f"← {prev_lesson['title']}", key="prev_lesson"):
                st.session_state.learning_lesson = prev_lesson["id"]
                st.rerun()
    with nav_cols[2]:
        if lesson_idx < len(course_data["lessons"]) - 1:
            next_lesson = course_data["lessons"][lesson_idx + 1]
            if st.button(f"{next_lesson['title']} →", key="next_lesson"):
                st.session_state.learning_lesson = next_lesson["id"]
                st.rerun()


# ─── ルーティング ───

if st.session_state.learning_lesson:
    lesson = next(
        (l for l in course_data["lessons"] if l["id"] == st.session_state.learning_lesson),
        None,
    )
    if lesson:
        show_lesson(lesson)
    else:
        st.session_state.learning_lesson = None
        show_course_home()
else:
    show_course_home()
