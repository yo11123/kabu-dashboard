"use client";

import type { TechnicalResponse } from "@/types/api";
import { cn } from "@/lib/cn";

const TREND_LABEL = {
  bullish: { text: "上昇トレンド", color: "text-[var(--bull)]" },
  bearish: { text: "下降トレンド", color: "text-[var(--bear)]" },
  neutral: { text: "横ばい", color: "text-[var(--text-dim)]" },
};

const RSI_LABEL = {
  overbought: { text: "買われすぎ", color: "text-[var(--bear)]" },
  oversold: { text: "売られすぎ", color: "text-[var(--bull)]" },
  neutral: { text: "中立", color: "text-[var(--text-dim)]" },
};

const MACD_LABEL = {
  bullish_cross: { text: "ゴールデンクロス", color: "text-[var(--bull)]" },
  bearish_cross: { text: "デッドクロス", color: "text-[var(--bear)]" },
  neutral: { text: "シグナルなし", color: "text-[var(--text-dim)]" },
};

const BB_LABEL = {
  upper: { text: "上限付近", color: "text-[var(--bear)]" },
  middle: { text: "中央", color: "text-[var(--text-dim)]" },
  lower: { text: "下限付近", color: "text-[var(--bull)]" },
};

export function TechnicalPanel({ data }: { data: TechnicalResponse }) {
  const last = data.series[data.series.length - 1];
  const trend = TREND_LABEL[data.summary.trend];
  const rsi = RSI_LABEL[data.summary.rsi_state];
  const macd = MACD_LABEL[data.summary.macd_state];
  const bb = BB_LABEL[data.summary.bb_position];

  return (
    <div className="space-y-4">
      <Row label="トレンド" valueClass={trend.color} value={trend.text} />
      <Row
        label={`RSI(14): ${last?.rsi14?.toFixed(1) ?? "–"}`}
        valueClass={rsi.color}
        value={rsi.text}
      />
      <Row label="MACD" valueClass={macd.color} value={macd.text} />
      <Row label="ボリンジャー位置" valueClass={bb.color} value={bb.text} />

      <div className="pt-2 mt-2 border-t border-[var(--border)] text-xs text-[var(--text-faint)] space-y-1">
        <div>SMA20: <span className="font-mono">{fmt(last?.sma20)}</span></div>
        <div>SMA50: <span className="font-mono">{fmt(last?.sma50)}</span></div>
        <div>SMA200: <span className="font-mono">{fmt(last?.sma200)}</span></div>
      </div>
    </div>
  );
}

function Row({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="text-sm text-[var(--text-dim)]">{label}</span>
      <span className={cn("text-sm font-medium", valueClass)}>{value}</span>
    </div>
  );
}

function fmt(v?: number | null) {
  if (v == null || Number.isNaN(v)) return "–";
  return v.toFixed(2);
}
