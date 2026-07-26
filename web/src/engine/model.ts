// Core domain model. No `any`; every boundary (YAML import, CSV import,
// IndexedDB reads) must run through validate.ts before values are trusted
// as one of these types.

export const PRODUCT_IDS = ["BTC-USD", "ETH-USD"] as const;
export type ProductId = (typeof PRODUCT_IDS)[number];

export interface EntryRule {
  id: string;
  price: number;
  quoteSizeUsd: number;
}

export interface TakeProfitRule {
  tp1Price: number;
  tp1Fraction: number;
  tp2Price: number;
  tp2Fraction: number;
}

export interface AssetStrategy {
  productId: ProductId;
  enabled: boolean;
  allocationUsd: number;
  entries: EntryRule[];
  stopPrice: number;
  takeProfit: TakeProfitRule;
}

export interface Strategy {
  schemaVersion: 1;
  name: string;
  bankrollUsd: number;
  quoteCurrency: "USD";
  assets: AssetStrategy[];
  moveStopToBreakevenAfterTp1: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Dataset {
  datasetId: string;
  name: string;
  source: "bundled" | "upload";
  createdAt: string;
  startTs: string;
  endTs: string;
  products: ProductId[];
  rowCount: number;
  sha256: string;
  schemaVersion: 1;
}

export type RunStatus = "created" | "running" | "paused" | "completed" | "canceled" | "failed";

export interface RunSummary {
  endingEquity: number;
  maxDrawdown: number;
  totalRealizedPnl: number;
  totalUnrealizedPnl: number;
  stopCount: number;
  tp1Count: number;
  tp2Count: number;
  entriesFilledCount: number;
  durationTicks: number;
}

export interface Run {
  runId: string;
  status: RunStatus;
  strategySnapshot: Strategy;
  strategyHash: string;
  datasetSnapshot: Dataset;
  datasetHash: string;
  engineVersion: string;
  startedAt: string;
  completedAt: string | null;
  cursor: number;
  eventSequence: number;
  summary: RunSummary | null;
}

export interface Tick {
  ts: string;
  productId: ProductId;
  price: number;
}

export type OrderType = "entry" | "stop" | "tp1" | "tp2";
export type OrderSide = "buy" | "sell";
export type OrderStatus = "open" | "filled" | "canceled";

export interface Order {
  runId: string;
  orderId: string;
  ruleId: string;
  productId: ProductId;
  orderType: OrderType;
  side: OrderSide;
  status: OrderStatus;
  limitOrTriggerPrice: number;
  quoteSizeUsd: number | null;
  baseSize: number | null;
  createdAt: string;
  filledAt: string | null;
}

export type PositionLifecycleState =
  | "waiting_for_entry"
  | "active"
  | "tp1_hit"
  | "stopped_out"
  | "completed";

export interface Position {
  runId: string;
  productId: ProductId;
  baseQty: number;
  avgEntry: number;
  investedQuote: number;
  realizedPnl: number;
  state: PositionLifecycleState;
  tp1Done: boolean;
  tp2Done: boolean;
  stopDone: boolean;
  activeStopPrice: number;
}

export type EventLevel = "info" | "warn" | "error";

export interface EngineEvent {
  runId: string;
  sequence: number;
  ts: string;
  level: EventLevel;
  eventType: string;
  productId: ProductId | null;
  message: string;
  payload: Record<string, unknown> | null;
}

export interface EquitySample {
  ts: string;
  equity: number;
  drawdown: number;
}

export const ENGINE_VERSION = "0.2.0";
export const DISCLAIMER =
  "Experimental software for education and paper trading only. It does not place live trades and is not financial advice. Backtests and simulated results do not predict future performance.";
