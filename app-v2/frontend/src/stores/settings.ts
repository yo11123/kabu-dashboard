"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ThemeId } from "@/lib/themes";

export type AIProvider = "anthropic" | "openai" | "gemini";

export interface SettingsState {
  theme: ThemeId;
  aiProvider: AIProvider;
  apiKeys: Partial<Record<AIProvider, string>>;
  recentSymbols: string[];
  setTheme: (t: ThemeId) => void;
  setAIProvider: (p: AIProvider) => void;
  setApiKey: (p: AIProvider, key: string) => void;
  pushRecent: (sym: string) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "claude-warm",
      aiProvider: "anthropic",
      apiKeys: {},
      recentSymbols: [],
      setTheme: (t) => set({ theme: t }),
      setAIProvider: (p) => set({ aiProvider: p }),
      setApiKey: (p, key) =>
        set((s) => ({ apiKeys: { ...s.apiKeys, [p]: key } })),
      pushRecent: (sym) =>
        set((s) => ({
          recentSymbols: [sym, ...s.recentSymbols.filter((x) => x !== sym)].slice(0, 8),
        })),
    }),
    {
      name: "kabu-v2-settings",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
