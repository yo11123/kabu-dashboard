"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type LineData,
  type HistogramData,
  type Time,
} from "lightweight-charts";
import { getCssVar } from "@/lib/themes";

export interface IndicatorLine {
  key: string;
  data: { time: string; value: number | null | undefined }[];
  color: string;
  lineWidth?: 1 | 2 | 3 | 4;
}

export interface IndicatorHistogram {
  data: { time: string; value: number | null | undefined }[];
  positiveColor: string;
  negativeColor: string;
}

interface Props {
  title: string;
  lines: IndicatorLine[];
  histogram?: IndicatorHistogram;
  /** Horizontal reference lines (e.g. RSI 30/70). */
  referenceLines?: { value: number; color: string; style?: LineStyle }[];
  /** Lock the visible value range (e.g. [0, 100] for RSI). */
  fixedRange?: { min: number; max: number };
  height?: number;
  parentChart: IChartApi | null;
}

/** Generic sub-chart pane that mirrors the parent chart's time scale. */
export function IndicatorPane({
  title,
  lines,
  histogram,
  referenceLines,
  fixedRange,
  height = 120,
  parentChart,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineSeriesRef = useRef<Map<string, ISeriesApi<"Line">>>(new Map());
  const histSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const text = getCssVar("--text-dim") || "#888";
    const grid = getCssVar("--grid") || "rgba(0,0,0,0.06)";

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: text,
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
        fontSize: 11,
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
        visible: false, // x-axis shown only on the bottom-most chart (main)
        rightOffset: 0,
        fixRightEdge: true,
        fixLeftEdge: true,
        lockVisibleTimeRangeOnResize: true,
      },
      handleScroll: false,
      handleScale: false,
      autoSize: true,
    });

    chartRef.current = chart;

    return () => {
      chart.remove();
      chartRef.current = null;
      lineSeriesRef.current.clear();
      histSeriesRef.current = null;
    };
  }, []);

  // Update series data
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    // Lines: add/remove/update
    const wantedKeys = new Set(lines.map((l) => l.key));
    for (const [key, series] of lineSeriesRef.current) {
      if (!wantedKeys.has(key)) {
        chart.removeSeries(series);
        lineSeriesRef.current.delete(key);
      }
    }
    for (const line of lines) {
      let series = lineSeriesRef.current.get(line.key);
      if (!series) {
        series = chart.addLineSeries({
          color: line.color,
          lineWidth: line.lineWidth ?? 1,
          priceLineVisible: false,
          lastValueVisible: true,
        });
        lineSeriesRef.current.set(line.key, series);
      } else {
        series.applyOptions({ color: line.color, lineWidth: line.lineWidth ?? 1 });
      }
      const data: LineData<Time>[] = line.data
        .map((p) => ({ time: p.time as Time, value: p.value as number | null }))
        .filter(
          (p): p is LineData<Time> =>
            p.value !== null && p.value !== undefined && !Number.isNaN(p.value),
        );
      series.setData(data);
    }

    // Histogram (MACD hist): single series, recolor per bar
    if (histogram) {
      if (!histSeriesRef.current) {
        histSeriesRef.current = chart.addHistogramSeries({
          priceFormat: { type: "price", precision: 4, minMove: 0.0001 },
          priceLineVisible: false,
          lastValueVisible: false,
        });
      }
      const data: HistogramData<Time>[] = histogram.data
        .map((p) => ({
          time: p.time as Time,
          value: p.value as number | null,
          color:
            (p.value as number) >= 0 ? histogram.positiveColor : histogram.negativeColor,
        }))
        .filter(
          (p): p is HistogramData<Time> =>
            p.value !== null && p.value !== undefined && !Number.isNaN(p.value),
        );
      histSeriesRef.current.setData(data);
    } else if (histSeriesRef.current) {
      chart.removeSeries(histSeriesRef.current);
      histSeriesRef.current = null;
    }

    // Reference & fixed-range lines attached to the first line series so they
    // share its price scale. Remove previous ones first to avoid accumulation.
    const firstSeries = lines[0] ? lineSeriesRef.current.get(lines[0].key) : null;
    for (const pl of priceLinesRef.current) {
      try {
        firstSeries?.removePriceLine(pl);
      } catch {
        // series may have been removed already
      }
    }
    priceLinesRef.current = [];

    if (firstSeries) {
      if (referenceLines) {
        for (const ref of referenceLines) {
          priceLinesRef.current.push(
            firstSeries.createPriceLine({
              price: ref.value,
              color: ref.color,
              lineWidth: 1,
              lineStyle: ref.style ?? LineStyle.Dashed,
              axisLabelVisible: true,
              title: "",
            }),
          );
        }
      }
      if (fixedRange) {
        for (const v of [fixedRange.min, fixedRange.max]) {
          priceLinesRef.current.push(
            firstSeries.createPriceLine({
              price: v,
              color: "transparent",
              lineWidth: 1,
              lineStyle: LineStyle.Dotted,
              axisLabelVisible: false,
              title: "",
            }),
          );
        }
      }
    }
  }, [lines, histogram, referenceLines, fixedRange]);

  // Sync time scale with parent chart
  useEffect(() => {
    if (!parentChart || !chartRef.current) return;
    const parentTS = parentChart.timeScale();
    const ownTS = chartRef.current.timeScale();

    const initial = parentTS.getVisibleLogicalRange();
    if (initial) ownTS.setVisibleLogicalRange(initial);

    const handler = (range: { from: number; to: number } | null) => {
      if (range) ownTS.setVisibleLogicalRange(range);
    };
    parentTS.subscribeVisibleLogicalRangeChange(handler);
    return () => {
      parentTS.unsubscribeVisibleLogicalRangeChange(handler);
    };
  }, [parentChart]);

  return (
    <div className="relative">
      <div className="absolute top-1.5 left-2 z-10 text-[10px] uppercase tracking-widest text-[var(--text-faint)] font-mono pointer-events-none">
        {title}
      </div>
      <div ref={containerRef} style={{ height }} className="w-full" />
    </div>
  );
}
