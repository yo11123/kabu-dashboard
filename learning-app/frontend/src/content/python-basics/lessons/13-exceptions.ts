export const content = `
# 例外処理

## try-except

プログラム実行中のエラー（例外）を適切に処理できます。

\`\`\`python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("ゼロでは割れません")
\`\`\`

## 複数の例外をキャッチ

\`\`\`python
def safe_convert(value):
    try:
        return int(value)
    except ValueError:
        print(f"'{value}' は整数に変換できません")
        return None
    except TypeError:
        print("型が不正です")
        return None

print(safe_convert("42"))     # 42
print(safe_convert("hello"))  # None
\`\`\`

## else と finally

\`\`\`python
try:
    number = int("42")
except ValueError:
    print("変換エラー")
else:
    print(f"成功: {number}")  # 例外が出なかった場合
finally:
    print("処理完了")          # 常に実行される
\`\`\`

## 例外の情報を取得

\`\`\`python
try:
    data = {"key": "value"}
    print(data["missing"])
except KeyError as e:
    print(f"キーが見つかりません: {e}")
\`\`\`

## カスタム例外

\`\`\`python
class InsufficientFundsError(Exception):
    def __init__(self, balance, amount):
        self.balance = balance
        self.amount = amount
        super().__init__(
            f"残高不足: 残高{balance}円に対して{amount}円の出金"
        )

def withdraw(balance, amount):
    if amount > balance:
        raise InsufficientFundsError(balance, amount)
    return balance - amount

try:
    new_balance = withdraw(1000, 2000)
except InsufficientFundsError as e:
    print(e)
\`\`\`

## よくある例外の種類

| 例外 | 発生条件 |
|------|----------|
| \`ValueError\` | 値が不正 |
| \`TypeError\` | 型が不正 |
| \`KeyError\` | 辞書にキーがない |
| \`IndexError\` | インデックスが範囲外 |
| \`FileNotFoundError\` | ファイルがない |
| \`ZeroDivisionError\` | ゼロ除算 |

それでは、演習問題に挑戦しましょう！
`;
