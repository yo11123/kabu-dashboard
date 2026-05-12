export type ThemeId = "claude-warm" | "claude-dark" | "terminal";

export const themes: { id: ThemeId; label: string; description: string }[] = [
  {
    id: "claude-warm",
    label: "Claude Warm",
    description: "紙のような明るい背景・落ち着いたオレンジアクセント",
  },
  {
    id: "claude-dark",
    label: "Claude Dark",
    description: "夜間でも目に優しい暖色ダーク",
  },
  {
    id: "terminal",
    label: "Terminal",
    description: "金融端末風のクールな青系ダーク",
  },
];

export function applyTheme(id: ThemeId) {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = id;
}

export function getCssVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
