import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "genai-09-chat-history",
    title: "チャット履歴マネージャーを作ろう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `import json

# チャットボットの会話履歴を管理するクラスを作成してください。

class ChatHistory:
    def __init__(self, system_prompt: str = "", max_messages: int = 20):
        """
        system_prompt: システムプロンプト（空でも可）
        max_messages: 保持する最大メッセージ数（systemメッセージを除く）
        """
        self.system_prompt = system_prompt
        self.max_messages = max_messages
        self.messages = []

    def add_user_message(self, content: str):
        """ユーザーメッセージを追加"""
        # ここにコードを書いてください
        pass

    def add_assistant_message(self, content: str):
        """アシスタントメッセージを追加"""
        # ここにコードを書いてください
        pass

    def get_messages(self) -> list:
        """
        API送信用のメッセージリストを返す。
        system_promptがある場合は先頭に含める。
        max_messagesを超えた場合は古いメッセージから削除。
        """
        # ここにコードを書いてください
        pass

    def get_last_exchange(self) -> dict:
        """
        最後のユーザー/アシスタントのやりとりを返す。
        戻り値: {"user": "最後のユーザーメッセージ", "assistant": "最後のアシスタントメッセージ"}
        メッセージがない場合は空文字列を入れる。
        """
        # ここにコードを書いてください
        pass

    def get_summary_stats(self) -> dict:
        """
        会話の統計情報を返す。
        戻り値: {
            "total_messages": int,
            "user_messages": int,
            "assistant_messages": int,
            "total_characters": int (全メッセージの文字数合計)
        }
        """
        # ここにコードを書いてください
        pass

    def clear(self):
        """会話履歴をクリア（system_promptは保持）"""
        # ここにコードを書いてください
        pass

# テスト
chat = ChatHistory("あなたは優秀なアシスタントです。", max_messages=4)

chat.add_user_message("こんにちは")
chat.add_assistant_message("こんにちは！何かお手伝いできますか？")
chat.add_user_message("Pythonについて教えて")
chat.add_assistant_message("Pythonは汎用プログラミング言語です。")
chat.add_user_message("もっと詳しく")
chat.add_assistant_message("Pythonはデータ分析やWeb開発に使われます。")

msgs = chat.get_messages()
print(f"メッセージ数: {len(msgs)}")
for m in msgs:
    print(f"  [{m['role']}]: {m['content'][:30]}")

print()
stats = chat.get_summary_stats()
print(f"統計: {json.dumps(stats, ensure_ascii=False)}")

print()
exchange = chat.get_last_exchange()
print(f"最後のやりとり: {json.dumps(exchange, ensure_ascii=False)}")
`,
    solutionCode: `import json

class ChatHistory:
    def __init__(self, system_prompt: str = "", max_messages: int = 20):
        self.system_prompt = system_prompt
        self.max_messages = max_messages
        self.messages = []

    def add_user_message(self, content: str):
        """ユーザーメッセージを追加"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        """アシスタントメッセージを追加"""
        self.messages.append({"role": "assistant", "content": content})

    def get_messages(self) -> list:
        """API送信用のメッセージリストを返す"""
        result = []

        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})

        # max_messagesを超えた場合は古いメッセージを切り捨て
        trimmed = self.messages[-self.max_messages:] if len(self.messages) > self.max_messages else self.messages

        result.extend(trimmed)
        return result

    def get_last_exchange(self) -> dict:
        """最後のユーザー/アシスタントのやりとりを返す"""
        last_user = ""
        last_assistant = ""

        for msg in reversed(self.messages):
            if msg["role"] == "user" and not last_user:
                last_user = msg["content"]
            elif msg["role"] == "assistant" and not last_assistant:
                last_assistant = msg["content"]
            if last_user and last_assistant:
                break

        return {"user": last_user, "assistant": last_assistant}

    def get_summary_stats(self) -> dict:
        """会話の統計情報を返す"""
        user_msgs = [m for m in self.messages if m["role"] == "user"]
        assistant_msgs = [m for m in self.messages if m["role"] == "assistant"]
        total_chars = sum(len(m["content"]) for m in self.messages)

        return {
            "total_messages": len(self.messages),
            "user_messages": len(user_msgs),
            "assistant_messages": len(assistant_msgs),
            "total_characters": total_chars
        }

    def clear(self):
        """会話履歴をクリア"""
        self.messages = []

# テスト
chat = ChatHistory("あなたは優秀なアシスタントです。", max_messages=4)

chat.add_user_message("こんにちは")
chat.add_assistant_message("こんにちは！何かお手伝いできますか？")
chat.add_user_message("Pythonについて教えて")
chat.add_assistant_message("Pythonは汎用プログラミング言語です。")
chat.add_user_message("もっと詳しく")
chat.add_assistant_message("Pythonはデータ分析やWeb開発に使われます。")

msgs = chat.get_messages()
print(f"メッセージ数: {len(msgs)}")
for m in msgs:
    print(f"  [{m['role']}]: {m['content'][:30]}")

print()
stats = chat.get_summary_stats()
print(f"統計: {json.dumps(stats, ensure_ascii=False)}")

print()
exchange = chat.get_last_exchange()
print(f"最後のやりとり: {json.dumps(exchange, ensure_ascii=False)}")
`,
    hints: [
      "messagesリストにroleとcontentの辞書を追加します",
      "get_messages()ではsystem_promptがある場合のみ先頭に追加",
      "max_messagesを超えたらスライス[-max_messages:]で古いものを切り捨て",
      "get_last_exchange()はreversed()で後ろから探索すると効率的",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
c = ChatHistory("sys", max_messages=2)
c.add_user_message("U1")
c.add_assistant_message("A1")
c.add_user_message("U2")
c.add_assistant_message("A2")
msgs = c.get_messages()
assert msgs[0]["role"] == "system", "先頭はsystem"
assert msgs[0]["content"] == "sys", "systemプロンプトが正しくない"
# max_messages=2なのでU2,A2のみ
non_sys = [m for m in msgs if m["role"] != "system"]
assert len(non_sys) == 2, f"max_messages=2で2件のはず: {len(non_sys)}"
assert non_sys[0]["content"] == "U2", "古いメッセージが残っている"

stats = c.get_summary_stats()
assert stats["total_messages"] == 4, "全メッセージは4件"
assert stats["user_messages"] == 2
assert stats["assistant_messages"] == 2

ex = c.get_last_exchange()
assert ex["user"] == "U2"
assert ex["assistant"] == "A2"

c.clear()
assert c.get_summary_stats()["total_messages"] == 0
assert c.system_prompt == "sys", "clearでsystem_promptは保持"
print("PASS")
`,
      },
    ],
  },
  {
    id: "genai-09-intent-detector",
    title: "ユーザー意図検出器を作ろう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# チャットボットのためのユーザー意図（インテント）検出器を作成してください。
# キーワードマッチングベースの簡易的な意図検出です。

class IntentDetector:
    def __init__(self):
        self.intents = {}  # {intent_name: {"keywords": [...], "response_template": str}}

    def register_intent(self, name: str, keywords: list, response_template: str):
        """インテントを登録する"""
        # ここにコードを書いてください
        pass

    def detect(self, user_input: str) -> dict:
        """
        ユーザー入力からインテントを検出する。
        各インテントのキーワードとのマッチ数をスコアとする。
        戻り値: {
            "intent": str (最もスコアの高いインテント名、該当なしは"unknown"),
            "confidence": float (マッチしたキーワード数 / そのインテントの総キーワード数),
            "matched_keywords": list (マッチしたキーワード),
            "response_template": str
        }
        """
        # ここにコードを書いてください
        pass

# テスト
detector = IntentDetector()
detector.register_intent(
    "greeting",
    ["こんにちは", "おはよう", "こんばんは", "はじめまして"],
    "こんにちは！何かお手伝いできますか？"
)
detector.register_intent(
    "farewell",
    ["さようなら", "バイバイ", "また", "おやすみ"],
    "ありがとうございました。またお待ちしております！"
)
detector.register_intent(
    "help",
    ["ヘルプ", "助けて", "使い方", "方法", "教えて"],
    "以下の機能をご利用いただけます..."
)
detector.register_intent(
    "order_status",
    ["注文", "配送", "届く", "状況", "追跡"],
    "注文番号をお知らせいただけますか？"
)

test_inputs = [
    "こんにちは、はじめまして",
    "注文した商品がまだ届かない",
    "使い方を教えてください",
    "さようなら、ありがとう",
    "天気はどうですか",
]

for text in test_inputs:
    result = detector.detect(text)
    print(f"入力: {text}")
    print(f"  意図: {result['intent']} (信頼度: {result['confidence']:.2f})")
    print(f"  キーワード: {result['matched_keywords']}")
    print()
`,
    solutionCode: `class IntentDetector:
    def __init__(self):
        self.intents = {}

    def register_intent(self, name: str, keywords: list, response_template: str):
        """インテントを登録する"""
        self.intents[name] = {
            "keywords": keywords,
            "response_template": response_template
        }

    def detect(self, user_input: str) -> dict:
        """ユーザー入力からインテントを検出する"""
        best_intent = "unknown"
        best_score = 0.0
        best_matched = []
        best_template = "申し訳ありませんが、よく分かりませんでした。"

        for name, data in self.intents.items():
            matched = [kw for kw in data["keywords"] if kw in user_input]
            score = len(matched) / len(data["keywords"]) if data["keywords"] else 0.0

            if score > best_score:
                best_score = score
                best_intent = name
                best_matched = matched
                best_template = data["response_template"]

        return {
            "intent": best_intent,
            "confidence": best_score,
            "matched_keywords": best_matched,
            "response_template": best_template
        }

# テスト
detector = IntentDetector()
detector.register_intent(
    "greeting",
    ["こんにちは", "おはよう", "こんばんは", "はじめまして"],
    "こんにちは！何かお手伝いできますか？"
)
detector.register_intent(
    "farewell",
    ["さようなら", "バイバイ", "また", "おやすみ"],
    "ありがとうございました。またお待ちしております！"
)
detector.register_intent(
    "help",
    ["ヘルプ", "助けて", "使い方", "方法", "教えて"],
    "以下の機能をご利用いただけます..."
)
detector.register_intent(
    "order_status",
    ["注文", "配送", "届く", "状況", "追跡"],
    "注文番号をお知らせいただけますか？"
)

test_inputs = [
    "こんにちは、はじめまして",
    "注文した商品がまだ届かない",
    "使い方を教えてください",
    "さようなら、ありがとう",
    "天気はどうですか",
]

for text in test_inputs:
    result = detector.detect(text)
    print(f"入力: {text}")
    print(f"  意図: {result['intent']} (信頼度: {result['confidence']:.2f})")
    print(f"  キーワード: {result['matched_keywords']}")
    print()
`,
    hints: [
      "register_intent: 辞書にキーワードリストとテンプレートを保存",
      "detect: 各インテントのキーワードがuser_inputに含まれるかチェック",
      "'keyword in user_input'で部分文字列マッチができます",
      "スコア = マッチ数 / 総キーワード数 で信頼度を計算",
    ],
    testCases: [
      {
        id: "tc2",
                description: "正しい結果が出力される",
                type: "custom",
        checkCode: `
d = IntentDetector()
d.register_intent("greet", ["こんにちは", "おはよう"], "Hi!")
d.register_intent("bye", ["さようなら"], "Bye!")

r = d.detect("こんにちは！")
assert r["intent"] == "greet", f"意図が正しくない: {r['intent']}"
assert r["confidence"] == 0.5, f"信頼度が正しくない: {r['confidence']}"
assert "こんにちは" in r["matched_keywords"]

r2 = d.detect("全く関係ない文章")
assert r2["intent"] == "unknown", "該当なしはunknown"
assert r2["confidence"] == 0.0

r3 = d.detect("こんにちは、おはよう")
assert r3["confidence"] == 1.0, "両方マッチで1.0"
print("PASS")
`,
      },
    ],
  },
];
