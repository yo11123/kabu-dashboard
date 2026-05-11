"use client";

import type { FundamentalsResponse } from "@/types/api";

export function FundamentalsPanel({ data }: { data: FundamentalsResponse }) {
  return (
    <div className="space-y-4">
      {data.sector && (
        <div className="text-xs uppercase tracking-widest text-[var(--text-faint)]">
          {data.sector}
          {data.industry && ` · ${data.industry}`}
        </div>
      )}

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <Metric label="PER" value={fmt(data.pe)} />
        <Metric label="予想PER" value={fmt(data.forward_pe)} />
        <Metric label="PBR" value={fmt(data.pb)} />
        <Metric label="ROE" value={pct(data.roe)} />
        <Metric label="配当利回り" value={pct(data.dividend_yield)} />
        <Metric label="利益率" value={pct(data.profit_margin)} />
        <Metric label="売上成長率" value={pct(data.revenue_growth)} />
        <Metric label="時価総額" value={cap(data.market_cap, data.currency ?? undefined)} />
      </dl>

      {data.summary && (
        <p className="pt-3 mt-3 border-t border-[var(--border)] text-xs leading-relaxed text-[var(--text-dim)] line-clamp-6">
          {data.summary}
        </p>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] text-[var(--text-faint)]">{label}</dt>
      <dd className="font-mono">{value}</dd>
    </div>
  );
}

function fmt(v?: number | null) {
  if (v == null) return "–";
  return v.toFixed(2);
}
function pct(v?: number | null) {
  if (v == null) return "–";
  return `${(v * 100).toFixed(2)}%`;
}
function cap(v?: number | null, currency?: string) {
  if (v == null) return "–";
  if (v >= 1e12) return `${(v / 1e12).toFixed(2)}T ${currency ?? ""}`.trim();
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B ${currency ?? ""}`.trim();
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M ${currency ?? ""}`.trim();
  return v.toLocaleString();
}
