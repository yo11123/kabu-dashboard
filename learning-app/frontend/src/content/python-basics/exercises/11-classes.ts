import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "class-bank",
    title: "銀行口座クラスを作ろう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# BankAccount クラスを作成しましょう\n# - __init__: 口座名(owner)と残高(balance=0)を初期化\n# - deposit(amount): 入金（残高を増やす）\n# - withdraw(amount): 出金（残高不足ならメッセージを表示して出金しない）\n# - __str__: "口座名: 残高円" の形式\n\nclass BankAccount:\n    # ここにコードを書いてください\n    pass\n\naccount = BankAccount("太郎", 1000)\naccount.deposit(500)\nprint(account)\naccount.withdraw(200)\nprint(account)\naccount.withdraw(2000)\nprint(account)`,
    solutionCode: `class BankAccount:\n    def __init__(self, owner, balance=0):\n        self.owner = owner\n        self.balance = balance\n\n    def deposit(self, amount):\n        self.balance += amount\n\n    def withdraw(self, amount):\n        if amount > self.balance:\n            print("残高不足です")\n        else:\n            self.balance -= amount\n\n    def __str__(self):\n        return f"{self.owner}: {self.balance}円"\n\naccount = BankAccount("太郎", 1000)\naccount.deposit(500)\nprint(account)\naccount.withdraw(200)\nprint(account)\naccount.withdraw(2000)\nprint(account)`,
    hints: [
      "__init__ で self.owner と self.balance を初期化します",
      "withdraw では amount > self.balance を先にチェックしましょう",
      '__str__ で f"{self.owner}: {self.balance}円" を返します',
    ],
    testCases: [
      {
        id: "tc1",
        description: "入出金が正しく動作する",
        type: "stdout",
        expected: "太郎: 1500円\n太郎: 1300円\n残高不足です\n太郎: 1300円\n",
      },
    ],
  },
];
