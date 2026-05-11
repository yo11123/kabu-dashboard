"use client";

import { use, useEffect, useState } from "react";
import { useOhlcv, useTechnicals, useFundamentals } from "@/hooks/useStockData";
import { useIsMobile } from "@/hooks/useBreakpoint";
import { useSettings } from "@/stores/settings";
import { CandleChart } from "@/components/chart/CandleChart";
import { ChartToolbar, type Period, type Overlays } from "@/components/chart/ChartToolbar";
import { TechnicalPanel } from "@/components/panels/TechnicalPanel";
import { FundamentalsPanel } from "@/components/panels/FundamentalsPanel";
import { AIPanel } from "@/components/panels/AIPanel";
import { cn } from "@/lib/cn";

type Tab = "technical" | "fundamentals" | "ai";

export default function StockDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol: rawSymbol } = use(params);
  const symbol = decodeURIComponent(rawSymbol);
  const isMobile = useIsMobile();
  const pushRecent = useSettings((s) => s.pushRecent);

  const [period, setPeriod] = useState<Period>("1y");
  const [overlays, setOverlays] = useState<Overlays>({
    sma20: false,
    sma50: true,
    sma200: false,
    bb: false,
  });
  const [tab, setTab] = useState<Tab>("technical");

  const ohlcvQ = useOhlcv(symbol, period, "1d");
  const techQ = useTechnicals(symbol, period);
  const fundQ = useFundamentals(symbol);

  useEffect(() => {
    pushRecent(symbol);
  }, [symbol, pushRecent]);

  const toggleOverlay = (k: keyof Overlays) =>
    setOverlays((o) => ({ ...o, [k]: !o[k] }));

  const lastPrice = ohlcvQ.data?.points.at(-1)?.close;
  const firstPrice = ohlcvQ.data?.points[0]?.close;
  const change = lastPrice && firstPrice ? lastPrice - firstPrice : null;
  const changePct = change && firstPrice ? (change / firstPrice) * 100 : null;
  const name = fundQ.data?.name ?? symbol;

  const Header = (
    <header className="flex items-baseline justify-between gap-4">
      <div className="min-w-0">
        <h1 className="font-serif text-2xl md:text-3xl truncate">{name}</h1>
        <div className="text-xs text-[var(--text-faint)] font-mono">{symbol}</div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-xl md:text-2xl font-mono">
          {lastPrice != null ? lastPrice.toFixed(2) : "–"}
        </div>
        {changePct != null && (
          <div
            className={cn(
              "text-xs font-mono",
              changePct >= 0 ? "text-[var(--bull)]" : "text-[var(--bear)]",
            )}
          >
            {changePct >= 0 ? "+" : ""}
            {changePct.toFixed(2)}% ({period})
          </div>
        )}
      </div>
    </header>
  );

  const Toolbar = (
    <ChartToolbar
      period={period}
      onPeriodChange={setPeriod}
      overlays={overlays}
      onOverlayToggle={toggleOverlay}
      compact={isMobile}
    />
  );

  const Chart = ohlcvQ.isLoading ? (
    <div className="h-[400px] flex items-center justify-center text-[var(--text-faint)] text-sm">
      読み込み中…
    </div>
  ) : ohlcvQ.error ? (
    <div className="h-[400px] flex items-center justify-center text-[var(--bear)] text-sm">
      データを取得できませんでした
    </div>
  ) : (
    <CandleChart
      ohlcv={ohlcvQ.data?.points ?? []}
      technicals={techQ.data?.series}
      overlays={overlays}
      height={isMobile ? 320 : 480}
    />
  );

  const TabContent = (
    <>
      {tab === "technical" &&
        (techQ.data ? (
          <TechnicalPanel data={techQ.data} />
        ) : (
          <p className="text-sm text-[var(--text-faint)]">読み込み中…</p>
        ))}
      {tab === "fundamentals" &&
        (fundQ.data ? (
          <FundamentalsPanel data={fundQ.data} />
        ) : (
          <p className="text-sm text-[var(--text-faint)]">読み込み中…</p>
        ))}
      {tab === "ai" && <AIPanel symbol={symbol} />}
    </>
  );

  if (isMobile) {
    return (
      <div className="flex flex-col">
        <div className="sticky top-0 z-30 bg-[var(--bg)]/95 backdrop-blur border-b border-[var(--border)] px-4 py-3">
          {Header}
        </div>
        <div className="px-4 py-3 overflow-x-auto">{Toolbar}</div>
        <div className="px-2">{Chart}</div>

        <div className="sticky top-[72px] z-20 bg-[var(--bg)]/95 backdrop-blur border-y border-[var(--border)] flex">
          <TabButton active={tab === "technical"} onClick={() => setTab("technical")}>
            テクニカル
          </TabButton>
          <TabButton active={tab === "fundamentals"} onClick={() => setTab("fundamentals")}>
            ファンダ
          </TabButton>
          <TabButton active={tab === "ai"} onClick={() => setTab("ai")}>
            AI 分析
          </TabButton>
        </div>
        <div className="px-4 py-5">{TabContent}</div>
      </div>
    );
  }

  return (
    <div className="px-8 py-6 max-w-[1600px] mx-auto">
      <div className="mb-5">{Header}</div>
      <div className="grid grid-cols-[1fr_360px] gap-6">
        <section className="space-y-3">
          {Toolbar}
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
            {Chart}
          </div>
        </section>

        <aside className="rounded-xl border border-[var(--border)] bg-[var(--surface)] flex flex-col">
          <div className="flex border-b border-[var(--border)]">
            <TabButton active={tab === "technical"} onClick={() => setTab("technical")}>
              テクニカル
            </TabButton>
            <TabButton active={tab === "fundamentals"} onClick={() => setTab("fundamentals")}>
              ファンダ
            </TabButton>
            <TabButton active={tab === "ai"} onClick={() => setTab("ai")}>
              AI 分析
            </TabButton>
          </div>
          <div className="p-5 flex-1 overflow-y-auto">{TabContent}</div>
        </aside>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex-1 px-3 py-2.5 text-sm transition-colors",
        active
          ? "text-[var(--accent)] border-b-2 border-[var(--accent)]"
          : "text-[var(--text-dim)] hover:text-[var(--text)] border-b-2 border-transparent",
      )}
    >
      {children}
    </button>
  );
}
