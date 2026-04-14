"use client";

interface ProgressBarProps {
  value: number;
  color?: string;
  height?: number;
}

export default function ProgressBar({
  value,
  color = "var(--gold)",
  height = 4,
}: ProgressBarProps) {
  return (
    <div
      className="w-full bg-bg-elevated rounded-full overflow-hidden"
      style={{ height }}
    >
      <div
        className="h-full rounded-full transition-all duration-500 ease-out"
        style={{
          width: `${Math.min(100, Math.max(0, value))}%`,
          backgroundColor: color,
        }}
      />
    </div>
  );
}
