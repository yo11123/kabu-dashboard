"use client";

import { useState } from "react";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { apiPost } from "@/lib/api/client";
import { useSettings } from "@/stores/settings";
import type { AIPromptResponse } from "@/types/api";

export function AIPanel({ symbol }: { symbol: string }) {
  const provider = useSettings((s) => s.aiProvider);
  const apiKey = useSettings((s) => s.apiKeys[provider]);

  const [loading, setLoading] = useState(false);
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!apiKey) {
    return (
      <div className="space-y-3 text-sm text-[var(--text-dim)]">
        <p>AI 分析を有効にするには、設定画面で API キーを登録してください。</p>
        <Link
          href="/settings"
          className="inline-flex items-center gap-1 text-[var(--accent)] hover:underline"
        >
          設定を開く →
        </Link>
      </div>
    );
  }

  async function analyze() {
    setLoading(true);
    setError(null);
    setText(null);
    try {
      const prompt = await apiPost<AIPromptResponse>("/ai/build-prompt", {
        symbol,
        language: "ja",
        include_fundamentals: true,
        include_technicals: true,
      });
      const result = await callProvider(provider, apiKey!, prompt);
      setText(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <button
        onClick={analyze}
        disabled={loading}
        className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50"
      >
        <Sparkles size={14} />
        {loading ? "分析中…" : `${provider} で分析`}
      </button>

      {error && (
        <div className="text-sm text-[var(--bear)] whitespace-pre-wrap break-words">{error}</div>
      )}
      {text && (
        <div className="text-sm leading-relaxed whitespace-pre-wrap text-[var(--text)]">{text}</div>
      )}
    </div>
  );
}

async function callProvider(
  provider: "anthropic" | "openai" | "gemini",
  apiKey: string,
  prompt: AIPromptResponse,
): Promise<string> {
  if (provider === "anthropic") {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-6",
        max_tokens: 600,
        system: prompt.system,
        messages: [{ role: "user", content: prompt.user }],
      }),
    });
    if (!res.ok) throw new Error(`Anthropic ${res.status}: ${await res.text()}`);
    const json = await res.json();
    return json.content?.[0]?.text ?? "(no content)";
  }
  if (provider === "openai") {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [
          { role: "system", content: prompt.system },
          { role: "user", content: prompt.user },
        ],
      }),
    });
    if (!res.ok) throw new Error(`OpenAI ${res.status}: ${await res.text()}`);
    const json = await res.json();
    return json.choices?.[0]?.message?.content ?? "(no content)";
  }
  if (provider === "gemini") {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: prompt.system }] },
          contents: [{ role: "user", parts: [{ text: prompt.user }] }],
        }),
      },
    );
    if (!res.ok) throw new Error(`Gemini ${res.status}: ${await res.text()}`);
    const json = await res.json();
    return json.candidates?.[0]?.content?.parts?.[0]?.text ?? "(no content)";
  }
  throw new Error(`Unknown provider: ${provider}`);
}
