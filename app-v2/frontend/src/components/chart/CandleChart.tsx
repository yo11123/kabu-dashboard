"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type HistogramData,
  type LineData,
  type Time,
} from "lightweight-charts";
import type { OHLCVPoint, TechnicalPoint } from "@/types/api";
import { getCssVar } from "@/lib/themes";

interface Props {
  ohlcv: OHLCVPoint[];
  technicals?: TechnicalPoint[];
  overlays: { sma20?: boolean; sma50?: boolean; sma200?: boolean; bb?: boolean };
  showVolume?: boolean;
  height?: number;
  onChartReady?: (chart: IChartApi) => void;
}

export function CandleChart({
  ohlcv,
  technicals,
  overlays,
  showVolume = false,
  height = 480,
  onChartReady,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
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
      rightPriceScale: { borderVisible: false, minimumWidth: 60 },
      timeScale: {
        borderVisible: false,
        timeVisible: false,
        rightOffset: 0,
        fixRightEdge: true,
        fixLeftEdge: true,
        lockVisibleTimeRangeOnResize: true,
        rightBarStaysOnScroll: true,
      },
      handleScroll: {
        horzTouchDrag: true,
        vertTouchDrag: false,
        mouseWheel: false,
        pressedMouseMove: true,
      },
      handleScale: {
        axisPressedMouseMove: { time: true, price: false },
        mouseWheel: true,
        pinch: true,
      },
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

    onChartReady?.(chart);

    return () => {
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      overlaySeriesRef.current.clear();
    };
  }, [onChartReady]);

  // Toggle volume series + adjust main scale margins
  useEffect(() => {
    const chart = chartRef.current;
    const candle = candleSeriesRef.current;
    if (!chart || !candle) return;

    if (showVolume) {
      if (!volumeSeriesRef.current) {
        const vol = chart.addHistogramSeries({
          priceFormat: { type: "volume" },
          priceScaleId: "volume",
          color: "rgba(140,140,140,0.45)",
        });
        chart
          .priceScale("volume")
          .applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
        volumeSeriesRef.current = vol;
      }
      // Push the main candle scale up to leave room for volume.
      candle.priceScale().applyOptions({ scaleMargins: { top: 0.05, bottom: 0.28 } });
    } else {
      if (volumeSeriesRef.current) {
        chart.removeSeries(volumeSeriesRef.current);
        volumeSeriesRef.current = null;
      }
      candle.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.08 } });
    }
  }, [showVolume]);

  // Update candle + volume data
  useEffect(() => {
    if (!candleSeriesRef.current || !chartRef.current || ohlcv.length === 0) return;

    const bull = getCssVar("--bull") || "#2f8a5f";
    const bear = getCssVar("--bear") || "#c84a4a";

    const candleData: CandlestickData<Time>[] = ohlcv.map((p) => ({
      time: p.time as Time,
      open: p.open,
      high: p.high,
      low: p.low,
      close: p.close,
    }));
    candleSeriesRef.current.setData(candleData);

    if (volumeSeriesRef.current) {
      const volData: HistogramData<Time>[] = ohlcv
        .filter((p) => p.volume != null)
        .map((p) => ({
          time: p.time as Time,
          value: p.volume as number,
          color: p.close >= p.open ? `${bull}66` : `${bear}66`,
        }));
      volumeSeriesRef.current.setData(volData);
    }

    const ts = chartRef.current.timeScale();
    ts.applyOptions({
      rightOffset: 0,
      fixRightEdge: true,
      fixLeftEdge: true,
      lockVisibleTimeRangeOnResize: true,
      rightBarStaysOnScroll: true,
    });
    ts.fitContent();
  }, [ohlcv, showVolume]);

  // Update overlays
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !technicals) return;

    const wanted: { key: string; color: string; field: keyof TechnicalPoint }[] = [];
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
        series = chart.addLineSeries({
          color,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        overlaySeriesRef.current.set(key, series);
      }
      const data: LineData<Time>[] = technicals
        .map((p) => ({ time: p.time as Time, value: p[field] as number | null }))
        .filter(
          (p): p is LineData<Time> =>
            p.value !== null && p.value !== undefined && !Number.isNaN(p.value),
        );
      series.setData(data);
    }
  }, [technicals, overlays]);

  return <div ref={containerRef} style={{ height }} className="w-full" />;
}
