import type { LessonMeta } from "@/types/course";

import { exercises as exercises01 } from "./exercises/01-intro-to-genai";
import { exercises as exercises02 } from "./exercises/02-llm-basics";
import { exercises as exercises03 } from "./exercises/03-openai-api";
import { exercises as exercises04 } from "./exercises/04-prompt-engineering";
import { exercises as exercises05 } from "./exercises/05-few-shot-learning";
import { exercises as exercises06 } from "./exercises/06-chain-of-thought";
import { exercises as exercises07 } from "./exercises/07-embeddings";
import { exercises as exercises08 } from "./exercises/08-rag-basics";
import { exercises as exercises09 } from "./exercises/09-building-chatbot";
import { exercises as exercises10 } from "./exercises/10-building-ai-app";

export const generativeAiLessons: LessonMeta[] = [
  { id: "01-intro-to-genai", title: "生成AI入門", description: "生成AIの概要と歴史", order: 1, exercises: exercises01 },
  { id: "02-llm-basics", title: "LLMの基礎", description: "大規模言語モデルの仕組み", order: 2, exercises: exercises02 },
  { id: "03-openai-api", title: "OpenAI API", description: "OpenAI APIの使い方", order: 3, exercises: exercises03 },
  { id: "04-prompt-engineering", title: "プロンプトエンジニアリング", description: "効果的なプロンプトの設計", order: 4, exercises: exercises04 },
  { id: "05-few-shot-learning", title: "Few-shotラーニング", description: "少数例示による学習", order: 5, exercises: exercises05 },
  { id: "06-chain-of-thought", title: "Chain of Thought", description: "思考の連鎖による推論", order: 6, exercises: exercises06 },
  { id: "07-embeddings", title: "エンベディング", description: "テキストのベクトル表現", order: 7, exercises: exercises07 },
  { id: "08-rag-basics", title: "RAG基礎", description: "検索拡張生成の基礎", order: 8, exercises: exercises08 },
  { id: "09-building-chatbot", title: "チャットボット構築", description: "対話システムの構築", order: 9, exercises: exercises09 },
  { id: "10-building-ai-app", title: "AIアプリ構築", description: "AIアプリケーションの設計と実装", order: 10, exercises: exercises10 },
];
