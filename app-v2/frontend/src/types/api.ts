export interface SymbolHit {
  symbol: string;
  name: string;
  market: "JP" | "US" | "OTHER";
}

export interface OHLCVPoint {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number | null;
}

export interface OHLCVResponse {
  symbol: string;
  interval: string;
  period: string;
  points: OHLCVPoint[];
}

export interface TechnicalPoint {
  time: string;
  sma20?: number | null;
  sma50?: number | null;
  sma200?: number | null;
  bb_upper?: number | null;
  bb_middle?: number | null;
  bb_lower?: number | null;
  rsi14?: number | null;
  macd?: number | null;
  macd_signal?: number | null;
  macd_hist?: number | null;
}

export interface TechnicalSummary {
  trend: "bullish" | "bearish" | "neutral";
  rsi_state: "overbought" | "oversold" | "neutral";
  macd_state: "bullish_cross" | "bearish_cross" | "neutral";
  bb_position: "upper" | "middle" | "lower";
}

export interface TechnicalResponse {
  symbol: string;
  series: TechnicalPoint[];
  summary: TechnicalSummary;
}

export interface FundamentalsResponse {
  symbol: string;
  name?: string | null;
  currency?: string | null;
  market_cap?: number | null;
  pe?: number | null;
  forward_pe?: number | null;
  pb?: number | null;
  roe?: number | null;
  dividend_yield?: number | null;
  profit_margin?: number | null;
  revenue_growth?: number | null;
  sector?: string | null;
  industry?: string | null;
  summary?: string | null;
}

export interface AIPromptResponse {
  symbol: string;
  system: string;
  user: string;
  context: Record<string, unknown>;
}
