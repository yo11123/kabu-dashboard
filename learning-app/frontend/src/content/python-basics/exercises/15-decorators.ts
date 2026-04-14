import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "gen-fibonacci",
    title: "フィボナッチジェネレータを作ろう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# フィボナッチ数列を生成するジェネレータ関数を作りましょう\n# yield を使って n 個のフィボナッチ数を生成します\n\ndef fibonacci(n):\n    # ここにコードを書いてください\n    pass\n\n# 最初の10個を表示\nprint(list(fibonacci(10)))`,
    solutionCode: `def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b\n\nprint(list(fibonacci(10)))`,
    hints: [
      "yield で値を一つずつ返します",
      "a, b = 0, 1 で初期化し、a, b = b, a + b で更新します",
      "range(n) でn回繰り返し、毎回 yield a します",
    ],
    testCases: [
      {
        id: "tc1",
        description: "フィボナッチ数列の最初の10個が正しい",
        type: "stdout",
        expected: "[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]\n",
      },
    ],
  },
  {
    id: "dec-cache",
    title: "キャッシュデコレータを作ろう",
    difficulty: "hard",
    executionTarget: "pyodide",
    starterCode: `# 関数の結果をキャッシュするデコレータを作りましょう\n# 同じ引数で呼ばれたら計算せずにキャッシュから返す\n\ndef cache(func):\n    # ここにコードを書いてください\n    pass\n\n@cache\ndef expensive_calc(n):\n    print(f"計算中: {n}")\n    return n ** 2\n\nprint(expensive_calc(5))   # 計算中: 5 → 25\nprint(expensive_calc(5))   # キャッシュから → 25\nprint(expensive_calc(3))   # 計算中: 3 → 9`,
    solutionCode: `def cache(func):\n    memo = {}\n    def wrapper(*args):\n        if args not in memo:\n            memo[args] = func(*args)\n        return memo[args]\n    return wrapper\n\n@cache\ndef expensive_calc(n):\n    print(f"計算中: {n}")\n    return n ** 2\n\nprint(expensive_calc(5))\nprint(expensive_calc(5))\nprint(expensive_calc(3))`,
    hints: [
      "辞書 memo を使って結果をキャッシュします",
      "args をキーとして memo に結果を保存します",
      "args が memo にあればキャッシュから返し、なければ func を実行",
    ],
    testCases: [
      {
        id: "tc1",
        description: "キャッシュが正しく動作する（2回目の呼び出しで計算しない）",
        type: "stdout",
        expected: "計算中: 5\n25\n25\n計算中: 3\n9\n",
      },
    ],
  },
];
