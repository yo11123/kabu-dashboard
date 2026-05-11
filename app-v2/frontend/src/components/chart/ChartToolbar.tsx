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

interface Props {
  period: Period;
  onPeriodChange: (p: Period) => void;
  overlays: Overlays;
  onOverlayToggle: (key: keyof Overlays) => void;
  compact?: boolean;
}

const OVERLAY_LABELS: { key: keyof Overlays; label: string }[] = [
  { key: "sma20", label: "MA20" },
  { key: "sma50", label: "MA50" },
  { key: "sma200", label: "MA200" },
  { key: "bb", label: "BB" },
];

export function ChartToolbar({ period, onPeriodChange, overlays, onOverlayToggle, compact }: Props) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", compact && "gap-1.5")}>
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

      <div className="flex items-center gap-1 ml-auto md:ml-2">
        {OVERLAY_LABELS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => onOverlayToggle(key)}
            className={cn(
              "px-2.5 py-1 text-xs rounded-md border transition-colors",
              overlays[key]
                ? "border-[var(--accent)] text-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[var(--border)] text-[var(--text-dim)] hover:border-[var(--border-strong)]",
            )}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
