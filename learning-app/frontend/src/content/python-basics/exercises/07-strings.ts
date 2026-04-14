import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "str-count",
    title: "文字列を分析しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# 文章から単語数を数えて出力しましょう\ntext = "Python は とても 人気のある プログラミング 言語 です"\n\n# 単語数を数えて出力してください\n`,
    solutionCode: `text = "Python は とても 人気のある プログラミング 言語 です"\nwords = text.split()\nprint(len(words))`,
    hints: [
      "split() でスペース区切りで分割するとリストになります",
      "len() でリストの要素数を数えられます",
    ],
    testCases: [
      {
        id: "tc1",
        description: "単語数 7 が出力される",
        type: "stdout",
        expected: "7\n",
      },
    ],
  },
  {
    id: "str-reverse",
    title: "回文を判定しよう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# 文字列が回文（前から読んでも後ろから読んでも同じ）かどうか判定する\n# 関数を作りましょう\n\ndef is_palindrome(text):\n    # ここにコードを書いてください\n    pass\n\nprint(is_palindrome("しんぶんし"))  # True\nprint(is_palindrome("たけやぶやけた"))  # True\nprint(is_palindrome("プログラミング"))  # False`,
    solutionCode: `def is_palindrome(text):\n    return text == text[::-1]\n\nprint(is_palindrome("しんぶんし"))\nprint(is_palindrome("たけやぶやけた"))\nprint(is_palindrome("プログラミング"))`,
    hints: [
      "文字列を逆順にするには [::-1] を使います",
      "元の文字列と逆順の文字列が同じなら回文です",
    ],
    testCases: [
      {
        id: "tc1",
        description: "回文判定が正しい",
        type: "stdout",
        expected: "True\nTrue\nFalse\n",
      },
    ],
  },
];
