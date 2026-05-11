"use client";

import { cn } from "@/lib/cn";

export const PERIODS = ["3mo", "6mo", "1y", "2y", "5y", "max"] as const;
export type Period = (typeof PERIODS)[number];

export type Overlays = {
  sma20: boolean;
  sma50: boolean;
  sma200: boolean;
  bb: boolean;
};

export type Subpanels = {
  volume: boolean;
  rsi: boolean;
  macd: boolean;
};

interface Props {
  period: Period;
  onPeriodChange: (p: Period) => void;
  overlays: Overlays;
  onOverlayToggle: (key: keyof Overlays) => void;
  subpanels: Subpanels;
  onSubpanelToggle: (key: keyof Subpanels) => void;
  compact?: boolean;
}

const OVERLAY_LABELS: { key: keyof Overlays; label: string }[] = [
  { key: "sma20", label: "MA20" },
  { key: "sma50", label: "MA50" },
  { key: "sma200", label: "MA200" },
  { key: "bb", label: "BB" },
];

const SUBPANEL_LABELS: { key: keyof Subpanels; label: string }[] = [
  { key: "volume", label: "出来高" },
  { key: "rsi", label: "RSI" },
  { key: "macd", label: "MACD" },
];

export function ChartToolbar({
  period,
  onPeriodChange,
  overlays,
  onOverlayToggle,
  subpanels,
  onSubpanelToggle,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div className="flex items-center gap-1 p-1 rounded-lg bg-[var(--surface-2)]">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => onPeriodChange(p)}
            className={cn(
              "px-2.5 py-1 text-xs rounded-md transition-colors font-mono",
              period === p
                ? "bg-[var(--surface)] text-[var(--text)] shadow-sm"
                : "text-[var(--text-dim)] hover:text-[var(--text)]",
            )}
          >
            {p}
          </button>
        ))}
      </div>

      <ToggleGroup
        items={OVERLAY_LABELS}
        active={overlays as unknown as Record<string, boolean>}
        onToggle={(k) => onOverlayToggle(k as keyof Overlays)}
      />

      <div className="h-5 w-px bg-[var(--border)]" aria-hidden />

      <ToggleGroup
        items={SUBPANEL_LABELS}
        active={subpanels as unknown as Record<string, boolean>}
        onToggle={(k) => onSubpanelToggle(k as keyof Subpanels)}
      />
    </div>
  );
}

function ToggleGroup({
  items,
  active,
  onToggle,
}: {
  items: { key: string; label: string }[];
  active: Record<string, boolean>;
  onToggle: (key: string) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      {items.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onToggle(key)}
          className={cn(
            "px-2.5 py-1 text-xs rounded-md border transition-colors",
            active[key]
              ? "border-[var(--accent)] text-[var(--accent)] bg-[var(--accent-soft)]"
              : "border-[var(--border)] text-[var(--text-dim)] hover:border-[var(--border-strong)]",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
