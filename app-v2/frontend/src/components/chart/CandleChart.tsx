"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type LineData,
  type Time,
} from "lightweight-charts";
import type { OHLCVPoint, TechnicalPoint } from "@/types/api";
import { getCssVar } from "@/lib/themes";

interface Props {
  ohlcv: OHLCVPoint[];
  technicals?: TechnicalPoint[];
  overlays: { sma20?: boolean; sma50?: boolean; sma200?: boolean; bb?: boolean };
  height?: number;
}

export function CandleChart({ ohlcv, technicals, overlays, height = 480 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const overlaySeriesRef = useRef<Map<string, ISeriesApi<"Line">>>(new Map());

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const text = getCssVar("--text-dim") || "#888";
    const grid = getCssVar("--grid") || "rgba(0,0,0,0.06)";
    const bull = getCssVar("--bull") || "#2f8a5f";
    const bear = getCssVar("--bear") || "#c84a4a";

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: text,
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
      },
      grid: {
        vertLines: { color: grid },
        horzLines: { color: grid },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: false },
      autoSize: true,
    });

    const candle = chart.addCandlestickSeries({
      upColor: bull,
      downColor: bear,
      borderUpColor: bull,
      borderDownColor: bear,
      wickUpColor: bull,
      wickDownColor: bear,
    });

    chartRef.current = chart;
    candleSeriesRef.current = candle;

    const ro = new ResizeObserver(() => chart.timeScale().fitContent());
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      overlaySeriesRef.current.clear();
    };
  }, []);

  // Update candle data
  useEffect(() => {
    if (!candleSeriesRef.current || ohlcv.length === 0) return;
    const data: CandlestickData<Time>[] = ohlcv.map((p) => ({
      time: p.time as Time,
      open: p.open,
      high: p.high,
      low: p.low,
      close: p.close,
    }));
    candleSeriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [ohlcv]);

  // Update overlays
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !technicals) return;

    const wanted: { key: string; color: string; field: keyof TechnicalPoint; lineWidth?: number }[] = [];
    if (overlays.sma20) wanted.push({ key: "sma20", color: "#4ea3ff", field: "sma20" });
    if (overlays.sma50) wanted.push({ key: "sma50", color: "#c97444", field: "sma50" });
    if (overlays.sma200) wanted.push({ key: "sma200", color: "#9c66cc", field: "sma200" });
    if (overlays.bb) {
      wanted.push({ key: "bb_upper", color: "rgba(140,140,140,0.6)", field: "bb_upper" });
      wanted.push({ key: "bb_lower", color: "rgba(140,140,140,0.6)", field: "bb_lower" });
    }

    const wantedKeys = new Set(wanted.map((w) => w.key));
    for (const [key, series] of overlaySeriesRef.current) {
      if (!wantedKeys.has(key)) {
        chart.removeSeries(series);
        overlaySeriesRef.current.delete(key);
      }
    }

    for (const { key, color, field } of wanted) {
      let series = overlaySeriesRef.current.get(key);
      if (!series) {
        series = chart.addLineSeries({ color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        overlaySeriesRef.current.set(key, series);
      }
      const data: LineData<Time>[] = technicals
        .map((p) => ({ time: p.time as Time, value: p[field] as number | null }))
        .filter((p): p is LineData<Time> => p.value !== null && p.value !== undefined && !Number.isNaN(p.value));
      series.setData(data);
    }
  }, [technicals, overlays]);

  return <div ref={containerRef} style={{ height }} className="w-full" />;
}
