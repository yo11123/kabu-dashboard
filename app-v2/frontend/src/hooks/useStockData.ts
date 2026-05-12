"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api/client";
import type {
  FundamentalsResponse,
  OHLCVResponse,
  SymbolHit,
  TechnicalResponse,
} from "@/types/api";

export function useSymbolSearch(q: string) {
  return useQuery({
    queryKey: ["symbols", q],
    queryFn: () => apiGet<SymbolHit[]>("/symbols/search", { q, limit: 8 }),
    staleTime: 60_000,
  });
}

export function useOhlcv(symbol: string, period: string, interval: string) {
  return useQuery({
    queryKey: ["ohlcv", symbol, period, interval],
    queryFn: () =>
      apiGet<OHLCVResponse>(`/stock/${encodeURIComponent(symbol)}/ohlcv`, { period, interval }),
    enabled: !!symbol,
    staleTime: 60_000,
  });
}

export function useTechnicals(symbol: string, period: string) {
  return useQuery({
    queryKey: ["technicals", symbol, period],
    queryFn: () =>
      apiGet<TechnicalResponse>(`/stock/${encodeURIComponent(symbol)}/technicals`, { period }),
    enabled: !!symbol,
    staleTime: 60_000,
  });
}

export function useFundamentals(symbol: string) {
  return useQuery({
    queryKey: ["fundamentals", symbol],
    queryFn: () =>
      apiGet<FundamentalsResponse>(`/stock/${encodeURIComponent(symbol)}/fundamentals`),
    enabled: !!symbol,
    staleTime: 5 * 60_000,
  });
}
