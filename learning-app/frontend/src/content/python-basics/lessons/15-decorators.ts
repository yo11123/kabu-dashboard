export const content = `
# デコレータとジェネレータ

## デコレータ

デコレータは関数を修飾（ラップ）する仕組みです。

\`\`\`python
def timer(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__}: {elapsed:.4f}秒")
        return result
    return wrapper

@timer
def slow_function():
    total = sum(range(1000000))
    return total

result = slow_function()
\`\`\`

## デコレータの仕組み

\`@timer\` は \`slow_function = timer(slow_function)\` と同じです。

\`\`\`python
def repeat(n):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(n):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def hello():
    print("こんにちは！")

hello()
# こんにちは！ が3回表示される
\`\`\`

## ジェネレータ関数

\`yield\` を使うと、値を一つずつ返すジェネレータを作れます。

\`\`\`python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

# ジェネレータはforループで使える
for num in fibonacci(10):
    print(num, end=" ")
# 0 1 1 2 3 5 8 13 21 34
\`\`\`

## ジェネレータの利点

メモリ効率が良い - 全データを一度にメモリに載せない。

\`\`\`python
# リスト: メモリに全て保持
big_list = [x ** 2 for x in range(1000000)]

# ジェネレータ: 必要なときだけ計算
big_gen = (x ** 2 for x in range(1000000))
print(sum(big_gen))  # メモリ効率が良い
\`\`\`

## 実用例: データパイプライン

\`\`\`python
def read_numbers(data):
    for line in data:
        yield int(line.strip())

def filter_positive(numbers):
    for n in numbers:
        if n > 0:
            yield n

def square(numbers):
    for n in numbers:
        yield n ** 2

# パイプラインとして連結
data = ["3", "-1", "4", "-2", "5"]
pipeline = square(filter_positive(read_numbers(data)))
print(list(pipeline))  # [9, 16, 25]
\`\`\`

これでPython基礎コースは終了です。お疲れ様でした！
`;
