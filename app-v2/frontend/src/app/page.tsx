"use client";

import { useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { useSymbolSearch } from "@/hooks/useStockData";
import { useSettings } from "@/stores/settings";
import { useIsMobile } from "@/hooks/useBreakpoint";

export default function HomePage() {
  const [q, setQ] = useState("");
  const { data, isLoading } = useSymbolSearch(q);
  const recents = useSettings((s) => s.recentSymbols);
  const isMobile = useIsMobile();

  return (
    <div className="px-4 md:px-10 py-8 md:py-16 max-w-3xl mx-auto">
      <header className="mb-8 md:mb-12">
        <h1 className="font-serif text-3xl md:text-5xl tracking-tight">銘柄を探す</h1>
        <p className="mt-2 text-sm text-[var(--text-dim)]">
          日本株 4 桁コード（例: 7203）または米株ティッカー（例: AAPL）
        </p>
      </header>

      <div className="relative">
        <Search
          size={isMobile ? 18 : 16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-faint)]"
        />
        <input
          autoFocus
          type="search"
          inputMode="search"
          placeholder="銘柄コードまたは社名"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-full pl-10 pr-3 py-3 md:py-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none text-base"
        />
      </div>

      {isLoading && q && (
        <div className="mt-6 text-sm text-[var(--text-faint)]">検索中…</div>
      )}

      {data && data.length > 0 && (
        <ul className="mt-6 divide-y divide-[var(--border)] rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
          {data.map((s) => (
            <li key={s.symbol}>
              <Link
                href={`/stock/${encodeURIComponent(s.symbol)}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-[var(--surface-2)] transition-colors"
              >
                <div>
                  <div className="font-mono text-sm">{s.symbol}</div>
                  <div className="text-sm text-[var(--text-dim)]">{s.name}</div>
                </div>
                <span className="text-[10px] uppercase tracking-widest text-[var(--text-faint)]">
                  {s.market}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {recents.length > 0 && (
        <section className="mt-10">
          <h2 className="text-xs uppercase tracking-[0.2em] text-[var(--text-faint)] mb-3">
            最近見た銘柄
          </h2>
          <div className="flex flex-wrap gap-2">
            {recents.map((sym) => (
              <Link
                key={sym}
                href={`/stock/${encodeURIComponent(sym)}`}
                className="px-3 py-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] text-sm font-mono hover:border-[var(--accent)] hover:text-[var(--accent)]"
              >
                {sym}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
