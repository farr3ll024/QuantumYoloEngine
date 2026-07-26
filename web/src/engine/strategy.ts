import { dump, load } from "js-yaml";
import type { AssetStrategy, ProductId, Strategy } from "./model";

// Stable, sorted JSON snapshot + sha256 hash. Must match
// quantum_yolo_engine.engine.strategy_snapshot_and_hash exactly (same key
// names, same nesting, same sort) or cross-run attribution breaks.
export function strategySnapshot(strategy: Strategy): Record<string, unknown> {
  const assets: Record<string, unknown> = {};
  for (const asset of strategy.assets) {
    assets[asset.productId] = {
      enabled: asset.enabled,
      allocation_usd: asset.allocationUsd,
      stop_price: asset.stopPrice,
      take_profit: {
        tp1_price: asset.takeProfit.tp1Price,
        tp1_fraction: asset.takeProfit.tp1Fraction,
        tp2_price: asset.takeProfit.tp2Price,
        tp2_fraction: asset.takeProfit.tp2Fraction,
      },
      entries: asset.entries.map((e) => ({ id: e.id, price: e.price, quote_size_usd: e.quoteSizeUsd })),
    };
  }
  return { assets };
}

function stableStringify(value: unknown): string {
  if (typeof value === "number") return pyFloatRepr(value);
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  const keys = Object.keys(value as Record<string, unknown>).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${stableStringify((value as Record<string, unknown>)[k])}`).join(",")}}`;
}

// Every numeric leaf in the strategy snapshot is a Python `float(...)`, and
// json.dumps renders whole-number floats with a trailing ".0" (e.g. 100.0),
// while JS's default number-to-string does not (100). Matching this exactly
// is required for the hash to match quantum_yolo_engine's sha256 byte-for-byte.
function pyFloatRepr(n: number): string {
  if (!Number.isFinite(n)) throw new Error(`cannot hash a non-finite number: ${n}`);
  return Number.isInteger(n) ? `${n}.0` : String(n);
}

async function sha256Hex(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// Real SHA-256, matching quantum_yolo_engine.engine.strategy_snapshot_and_hash
// exactly. Async because it uses SubtleCrypto -- callers that need this
// inside a synchronous code path (e.g. simulate.ts's createRun) must compute
// it ahead of time and pass the resulting hex string in.
export async function strategyHash(strategy: Strategy): Promise<string> {
  return sha256Hex(stableStringify(strategySnapshot(strategy)));
}

export function defaultStrategy(): Strategy {
  const now = new Date().toISOString();
  const btc: AssetStrategy = {
    productId: "BTC-USD",
    enabled: true,
    allocationUsd: 600,
    stopPrice: 62000,
    takeProfit: { tp1Price: 91000, tp1Fraction: 0.5, tp2Price: 96000, tp2Fraction: 0.5 },
    entries: [
      { id: "btc_e1", price: 85000, quoteSizeUsd: 80 },
      { id: "btc_e2", price: 86000, quoteSizeUsd: 80 },
      { id: "btc_e3", price: 84500, quoteSizeUsd: 100 },
      { id: "btc_e4", price: 82000, quoteSizeUsd: 120 },
      { id: "btc_e5", price: 78000, quoteSizeUsd: 120 },
      { id: "btc_e6", price: 70000, quoteSizeUsd: 100 },
    ],
  };
  const eth: AssetStrategy = {
    productId: "ETH-USD",
    enabled: true,
    allocationUsd: 400,
    stopPrice: 1780,
    takeProfit: { tp1Price: 3100, tp1Fraction: 0.5, tp2Price: 3350, tp2Fraction: 0.5 },
    entries: [
      { id: "eth_e1", price: 2770, quoteSizeUsd: 60 },
      { id: "eth_e2", price: 2840, quoteSizeUsd: 70 },
      { id: "eth_e3", price: 2820, quoteSizeUsd: 70 },
      { id: "eth_e4", price: 2550, quoteSizeUsd: 80 },
      { id: "eth_e5", price: 2200, quoteSizeUsd: 60 },
      { id: "eth_e6", price: 1950, quoteSizeUsd: 60 },
    ],
  };
  return {
    schemaVersion: 1,
    name: "Default BTC/ETH ladder",
    bankrollUsd: 1000,
    quoteCurrency: "USD",
    assets: [btc, eth],
    moveStopToBreakevenAfterTp1: true,
    createdAt: now,
    updatedAt: now,
  };
}

interface YamlAssetShape {
  enabled?: boolean;
  allocation_usd: number;
  stop_price: number;
  take_profit: { tp1_price: number; tp1_fraction: number; tp2_price: number; tp2_fraction: number };
  entries: { id: string; price: number; quote_size_usd: number }[];
}

interface YamlStrategyShape {
  bankroll_usd: number;
  quote_currency?: string;
  name?: string;
  move_stop_to_breakeven_after_tp1?: boolean;
  assets: Record<string, YamlAssetShape>;
}

export function strategyToYaml(strategy: Strategy): string {
  const assets: Record<string, unknown> = {};
  for (const asset of strategy.assets) {
    assets[asset.productId] = {
      enabled: asset.enabled,
      allocation_usd: asset.allocationUsd,
      stop_price: asset.stopPrice,
      take_profit: {
        tp1_price: asset.takeProfit.tp1Price,
        tp1_fraction: asset.takeProfit.tp1Fraction,
        tp2_price: asset.takeProfit.tp2Price,
        tp2_fraction: asset.takeProfit.tp2Fraction,
      },
      entries: asset.entries.map((e) => ({ id: e.id, price: e.price, quote_size_usd: e.quoteSizeUsd })),
    };
  }
  const doc: YamlStrategyShape = {
    bankroll_usd: strategy.bankrollUsd,
    quote_currency: strategy.quoteCurrency,
    name: strategy.name,
    move_stop_to_breakeven_after_tp1: strategy.moveStopToBreakevenAfterTp1,
    assets: assets as Record<string, YamlAssetShape>,
  };
  return dump(doc, { sortKeys: false });
}

export class StrategyImportError extends Error {}

/** Parses YAML text into a Strategy. Never uses an unsafe loader (js-yaml's
 * default `load` refuses custom tags/constructors, unlike `loadAll` with
 * schema overrides) and never executes arbitrary code from the document. */
export function strategyFromYaml(text: string, existing?: Pick<Strategy, "createdAt">): Strategy {
  let raw: unknown;
  try {
    raw = load(text);
  } catch (err) {
    throw new StrategyImportError(`invalid YAML: ${(err as Error).message}`);
  }
  if (!raw || typeof raw !== "object") {
    throw new StrategyImportError("strategy YAML must be a mapping");
  }
  const doc = raw as YamlStrategyShape;
  if (typeof doc.bankroll_usd !== "number" || !doc.assets || typeof doc.assets !== "object") {
    throw new StrategyImportError("strategy YAML must include bankroll_usd and assets");
  }

  const assets: AssetStrategy[] = Object.entries(doc.assets).map(([productId, v]) => {
    if (!v || !v.take_profit || !Array.isArray(v.entries)) {
      throw new StrategyImportError(`asset ${productId} is missing required fields`);
    }
    return {
      productId: productId as ProductId,
      enabled: v.enabled ?? true,
      allocationUsd: Number(v.allocation_usd),
      stopPrice: Number(v.stop_price),
      takeProfit: {
        tp1Price: Number(v.take_profit.tp1_price),
        tp1Fraction: Number(v.take_profit.tp1_fraction),
        tp2Price: Number(v.take_profit.tp2_price),
        tp2Fraction: Number(v.take_profit.tp2_fraction),
      },
      entries: v.entries.map((e) => ({ id: String(e.id), price: Number(e.price), quoteSizeUsd: Number(e.quote_size_usd) })),
    };
  });

  const now = new Date().toISOString();
  return {
    schemaVersion: 1,
    name: doc.name ?? "Imported strategy",
    bankrollUsd: Number(doc.bankroll_usd),
    quoteCurrency: "USD",
    assets,
    moveStopToBreakevenAfterTp1: doc.move_stop_to_breakeven_after_tp1 ?? true,
    createdAt: existing?.createdAt ?? now,
    updatedAt: now,
  };
}
