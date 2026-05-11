"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import type { IChartApi } from "lightweight-charts";
import { useOhlcv, useTechnicals, useFundamentals } from "@/hooks/useStockData";
import { useIsMobile } from "@/hooks/useBreakpoint";
import { useSettings } from "@/stores/settings";
import { CandleChart } from "@/components/chart/CandleChart";
import { IndicatorPane } from "@/components/chart/IndicatorPane";
import {
  ChartToolbar,
  type Period,
  type Overlays,
  type Subpanels,
} from "@/components/chart/ChartToolbar";
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
  const [subpanels, setSubpanels] = useState<Subpanels>({
    volume: true,
    rsi: false,
    macd: false,
  });
  const [tab, setTab] = useState<Tab>("technical");
  const [mainChart, setMainChart] = useState<IChartApi | null>(null);

  const ohlcvQ = useOhlcv(symbol, period, "1d");
  const techQ = useTechnicals(symbol, period);
  const fundQ = useFundamentals(symbol);

  useEffect(() => {
    pushRecent(symbol);
  }, [symbol, pushRecent]);

  const toggleOverlay = (k: keyof Overlays) =>
    setOverlays((o) => ({ ...o, [k]: !o[k] }));
  const toggleSubpanel = (k: keyof Subpanels) =>
    setSubpanels((s) => ({ ...s, [k]: !s[k] }));

  const handleChartReady = useCallback((chart: IChartApi) => {
    setMainChart(chart);
  }, []);

  const rsiData = useMemo(
    () =>
      (techQ.data?.series ?? []).map((p) => ({ time: p.time, value: p.rsi14 })),
    [techQ.data],
  );
  const macdLine = useMemo(
    () =>
      (techQ.data?.series ?? []).map((p) => ({ time: p.time, value: p.macd })),
    [techQ.data],
  );
  const macdSignal = useMemo(
    () =>
      (techQ.data?.series ?? []).map((p) => ({
        time: p.time,
        value: p.macd_signal,
      })),
    [techQ.data],
  );
  const macdHist = useMemo(
    () =>
      (techQ.data?.series ?? []).map((p) => ({
        time: p.time,
        value: p.macd_hist,
      })),
    [techQ.data],
  );

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
      subpanels={subpanels}
      onSubpanelToggle={toggleSubpanel}
    />
  );

  const ChartStack = ohlcvQ.isLoading ? (
    <div className="h-[400px] flex items-center justify-center text-[var(--text-faint)] text-sm">
      読み込み中…
    </div>
  ) : ohlcvQ.error ? (
    <div className="h-[400px] flex items-center justify-center text-[var(--bear)] text-sm">
      データを取得できませんでした
    </div>
  ) : (
    <div className="space-y-1">
      <CandleChart
        ohlcv={ohlcvQ.data?.points ?? []}
        technicals={techQ.data?.series}
        overlays={overlays}
        showVolume={subpanels.volume}
        height={isMobile ? 320 : 460}
        onChartReady={handleChartReady}
      />
      {subpanels.rsi && techQ.data && (
        <IndicatorPane
          title="RSI(14)"
          height={isMobile ? 100 : 120}
          parentChart={mainChart}
          lines={[{ key: "rsi", data: rsiData, color: "#c97444", lineWidth: 1 }]}
          referenceLines={[
            { value: 70, color: "rgba(200,74,74,0.5)" },
            { value: 30, color: "rgba(47,138,95,0.5)" },
          ]}
        />
      )}
      {subpanels.macd && techQ.data && (
        <IndicatorPane
          title="MACD(12,26,9)"
          height={isMobile ? 100 : 120}
          parentChart={mainChart}
          lines={[
            { key: "macd", data: macdLine, color: "#4ea3ff", lineWidth: 1 },
            { key: "signal", data: macdSignal, color: "#c97444", lineWidth: 1 },
          ]}
          histogram={{
            data: macdHist,
            positiveColor: "rgba(47,138,95,0.55)",
            negativeColor: "rgba(200,74,74,0.55)",
          }}
        />
      )}
    </div>
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
        <div className="px-2">{ChartStack}</div>

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
            {ChartStack}
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
