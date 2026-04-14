export const content = `
# 関数

## 関数とは

関数は、特定の処理をまとめて名前をつけたものです。何度も同じ処理を書く代わりに、関数として定義して呼び出せます。

## 関数の定義

\`def\` キーワードを使って関数を定義します。

\`\`\`python
def greet(name):
    print(f"こんにちは、{name}さん!")

greet("太郎")   # こんにちは、太郎さん!
greet("花子")   # こんにちは、花子さん!
\`\`\`

## 戻り値

\`return\` を使って関数から値を返せます。

\`\`\`python
def add(a, b):
    return a + b

result = add(3, 5)
print(result)  # 8
\`\`\`

## デフォルト引数

引数にデフォルト値を設定できます。

\`\`\`python
def greet(name, greeting="こんにちは"):
    return f"{greeting}、{name}さん!"

print(greet("太郎"))              # こんにちは、太郎さん!
print(greet("太郎", "おはよう"))   # おはよう、太郎さん!
\`\`\`

## キーワード引数

引数名を指定して関数を呼び出せます。

\`\`\`python
def profile(name, age, city):
    return f"{name}({age}歳) - {city}在住"

# キーワード引数で順番を変えられる
print(profile(age=25, city="東京", name="太郎"))
\`\`\`

## 可変長引数

\`*args\` と \`**kwargs\` を使って、任意の数の引数を受け取れます。

\`\`\`python
def total(*args):
    return sum(args)

print(total(1, 2, 3))      # 6
print(total(10, 20, 30, 40))  # 100

def show_info(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")

show_info(name="太郎", age=25)
\`\`\`

## lambda式

簡単な関数は lambda で1行で書けます。

\`\`\`python
square = lambda x: x ** 2
print(square(5))  # 25

numbers = [3, 1, 4, 1, 5]
sorted_numbers = sorted(numbers, key=lambda x: -x)
print(sorted_numbers)  # [5, 4, 3, 1, 1]
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
