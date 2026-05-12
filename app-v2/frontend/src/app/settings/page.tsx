"use client";

import { useSettings, type AIProvider } from "@/stores/settings";
import { themes, type ThemeId } from "@/lib/themes";
import { cn } from "@/lib/cn";

const PROVIDERS: { id: AIProvider; label: string; help: string; placeholder: string }[] = [
  {
    id: "anthropic",
    label: "Anthropic (Claude)",
    help: "console.anthropic.com で発行",
    placeholder: "sk-ant-...",
  },
  {
    id: "openai",
    label: "OpenAI",
    help: "platform.openai.com で発行",
    placeholder: "sk-...",
  },
  {
    id: "gemini",
    label: "Google Gemini",
    help: "aistudio.google.com で発行",
    placeholder: "AIza...",
  },
];

export default function SettingsPage() {
  const { theme, aiProvider, apiKeys, setTheme, setAIProvider, setApiKey } = useSettings();

  return (
    <div className="px-4 md:px-10 py-8 max-w-3xl mx-auto space-y-10">
      <header>
        <h1 className="font-serif text-3xl md:text-4xl tracking-tight">設定</h1>
        <p className="mt-2 text-sm text-[var(--text-dim)]">
          API キーはブラウザ内（localStorage）にのみ保存され、サーバーには送信されません。
        </p>
      </header>

      <Section title="テーマ" description="UI 全体の配色を切り替えます。チャートにも即時反映されます。">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {themes.map((t) => (
            <button
              key={t.id}
              onClick={() => setTheme(t.id as ThemeId)}
              className={cn(
                "text-left rounded-xl border p-4 transition-colors",
                theme === t.id
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[var(--border)] hover:border-[var(--border-strong)] bg-[var(--surface)]",
              )}
            >
              <div className="font-medium text-sm">{t.label}</div>
              <div className="mt-1 text-xs text-[var(--text-dim)]">{t.description}</div>
            </button>
          ))}
        </div>
      </Section>

      <Section
        title="AI 分析プロバイダ"
        description="銘柄分析に使う LLM サービスを選びます。"
      >
        <div className="flex flex-wrap gap-2 mb-4">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              onClick={() => setAIProvider(p.id)}
              className={cn(
                "px-3 py-1.5 text-sm rounded-full border",
                aiProvider === p.id
                  ? "border-[var(--accent)] text-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[var(--border)] text-[var(--text-dim)] hover:border-[var(--border-strong)]",
              )}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="space-y-4">
          {PROVIDERS.map((p) => (
            <div key={p.id}>
              <label className="block text-xs uppercase tracking-widest text-[var(--text-faint)] mb-1.5">
                {p.label} API キー
              </label>
              <input
                type="password"
                autoComplete="off"
                placeholder={p.placeholder}
                value={apiKeys[p.id] ?? ""}
                onChange={(e) => setApiKey(p.id, e.target.value)}
                className="w-full px-3 py-2.5 rounded-md bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none text-sm font-mono"
              />
              <p className="mt-1 text-[11px] text-[var(--text-faint)]">{p.help}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="セキュリティに関する注意">
        <ul className="text-sm text-[var(--text-dim)] space-y-1.5 list-disc list-inside">
          <li>Web 版では localStorage に保存されます。共有端末では使用しないでください。</li>
          <li>Tauri デスクトップ版では暗号化ストレージへ移行予定です。</li>
          <li>キーは LLM 提供元へ直接送信され、本アプリのバックエンドは経由しません。</li>
        </ul>
      </Section>
    </div>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-lg font-medium">{title}</h2>
      {description && <p className="mt-1 mb-4 text-sm text-[var(--text-dim)]">{description}</p>}
      {!description && <div className="mb-4" />}
      {children}
    </section>
  );
}
