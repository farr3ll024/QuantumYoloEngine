import JSZip from "jszip";
import type { Dataset, EngineEvent, EquitySample, Order, Position, Run, Strategy } from "./model";
import { strategyToYaml } from "./strategy";
import { ENGINE_VERSION, DISCLAIMER } from "./model";

// Mitigates spreadsheet-formula injection: any field beginning with
// =, +, -, or @ gets a leading apostrophe so Excel/Sheets treat it as text.
function csvCell(value: unknown): string {
  let s = value === null || value === undefined ? "" : String(value);
  if (/^[=+\-@]/.test(s)) s = `'${s}`;
  if (/[",\n]/.test(s)) s = `"${s.replace(/"/g, '""')}"`;
  return s;
}

function toCsv(rows: Record<string, unknown>[], columns: string[]): string {
  const header = columns.join(",");
  const body = rows.map((r) => columns.map((c) => csvCell(r[c])).join(",")).join("\n");
  return rows.length ? `${header}\n${body}\n` : `${header}\n`;
}

export interface TradeRound {
  productId: string;
  entryTs: string;
  exitTs: string | null;
  entryQty: number;
  avgEntry: number;
  exitReason: "stop" | "tp1" | "tp2" | "open";
  realizedPnl: number;
  durationSeconds: number | null;
}

/** Reconstructs entry->exit rounds from the event ledger for the trades.csv
 * export. Each fill event (stop/tp1/tp2) closes out against the running
 * position opened by the preceding entry_filled events for that product. */
export function reconstructTrades(events: EngineEvent[]): TradeRound[] {
  const rounds: TradeRound[] = [];
  const openByProduct = new Map<string, { ts: string; qty: number; avgEntry: number }>();

  for (const ev of events) {
    if (!ev.productId) continue;
    const payload = (ev.payload ?? {}) as Record<string, number>;

    if (ev.eventType === "entry_filled") {
      const existing = openByProduct.get(ev.productId);
      if (!existing) {
        openByProduct.set(ev.productId, { ts: ev.ts, qty: Number(payload.base_qty), avgEntry: Number(payload.new_avg_entry) });
      } else {
        existing.qty += Number(payload.base_qty);
        existing.avgEntry = Number(payload.new_avg_entry);
      }
    } else if (ev.eventType === "stop_filled" || ev.eventType === "tp2_filled") {
      const open = openByProduct.get(ev.productId);
      if (open) {
        rounds.push({
          productId: ev.productId,
          entryTs: open.ts,
          exitTs: ev.ts,
          entryQty: open.qty,
          avgEntry: open.avgEntry,
          exitReason: ev.eventType === "stop_filled" ? "stop" : "tp2",
          realizedPnl: Number(payload.realized_pnl),
          durationSeconds: (new Date(ev.ts).getTime() - new Date(open.ts).getTime()) / 1000,
        });
        openByProduct.delete(ev.productId);
      }
    } else if (ev.eventType === "tp1_filled") {
      const open = openByProduct.get(ev.productId);
      if (open) {
        rounds.push({
          productId: ev.productId,
          entryTs: open.ts,
          exitTs: ev.ts,
          entryQty: Number(payload.qty),
          avgEntry: open.avgEntry,
          exitReason: "tp1",
          realizedPnl: Number(payload.realized_pnl),
          durationSeconds: (new Date(ev.ts).getTime() - new Date(open.ts).getTime()) / 1000,
        });
      }
    }
  }

  for (const [productId, open] of openByProduct.entries()) {
    rounds.push({
      productId,
      entryTs: open.ts,
      exitTs: null,
      entryQty: open.qty,
      avgEntry: open.avgEntry,
      exitReason: "open",
      realizedPnl: 0,
      durationSeconds: null,
    });
  }

  return rounds;
}

export interface ReportInputs {
  run: Run;
  strategy: Strategy;
  dataset: Dataset;
  orders: Order[];
  positions: Position[];
  events: EngineEvent[];
  equitySamples: EquitySample[];
}

export async function buildReportZip(inputs: ReportInputs): Promise<Blob> {
  const { run, strategy, dataset, orders, positions, events, equitySamples } = inputs;
  const zip = new JSZip();

  const manifest = {
    schemaVersion: 1,
    appVersion: APP_VERSION,
    engineVersion: ENGINE_VERSION,
    runId: run.runId,
    createdAt: new Date().toISOString(),
    strategyHash: run.strategyHash,
    datasetHash: run.datasetHash,
    assumptions: [
      "Fills are simulated at min(market, limit) for buys and stops, max(market, limit) for take-profits.",
      "No slippage, spread, latency, or exchange fees are modeled.",
      "No order-book depth or liquidity constraints are modeled.",
      "Equity is reconstructed event-by-event from the run's event ledger, not projected from the final position.",
    ],
    disclaimer: DISCLAIMER,
  };

  const drawdownRows = equitySamples.map((s) => ({ ts: s.ts, drawdown: s.drawdown }));
  const trades = reconstructTrades(events);

  zip.file(
    "README.md",
    `# QuantumYoloEngine report — run ${run.runId}\n\n${DISCLAIMER}\n\nSee manifest.json for calculation assumptions and strategy/dataset attribution.\n`,
  );
  zip.file("manifest.json", JSON.stringify(manifest, null, 2));
  zip.file("summary.json", JSON.stringify(run.summary, null, 2));
  zip.file(
    "summary.csv",
    toCsv(
      run.summary ? [run.summary as unknown as Record<string, unknown>] : [],
      [
        "endingEquity",
        "maxDrawdown",
        "totalRealizedPnl",
        "totalUnrealizedPnl",
        "stopCount",
        "tp1Count",
        "tp2Count",
        "entriesFilledCount",
        "durationTicks",
      ],
    ),
  );
  zip.file("equity_curve.csv", toCsv(equitySamples as unknown as Record<string, unknown>[], ["ts", "equity", "drawdown"]));
  zip.file("drawdown.csv", toCsv(drawdownRows, ["ts", "drawdown"]));
  zip.file(
    "events.csv",
    toCsv(events as unknown as Record<string, unknown>[], ["sequence", "ts", "level", "productId", "eventType", "message"]),
  );
  zip.file(
    "orders.csv",
    toCsv(orders as unknown as Record<string, unknown>[], [
      "orderId",
      "productId",
      "orderType",
      "ruleId",
      "side",
      "status",
      "limitOrTriggerPrice",
      "quoteSizeUsd",
      "createdAt",
      "filledAt",
    ]),
  );
  zip.file(
    "positions.csv",
    toCsv(positions as unknown as Record<string, unknown>[], [
      "productId",
      "baseQty",
      "avgEntry",
      "investedQuote",
      "realizedPnl",
      "state",
      "tp1Done",
      "tp2Done",
      "stopDone",
      "activeStopPrice",
    ]),
  );
  zip.file(
    "trades.csv",
    toCsv(trades as unknown as Record<string, unknown>[], [
      "productId",
      "entryTs",
      "exitTs",
      "entryQty",
      "avgEntry",
      "exitReason",
      "realizedPnl",
      "durationSeconds",
    ]),
  );
  zip.file("strategy_snapshot.yaml", strategyToYaml(strategy));
  zip.file("dataset_manifest.json", JSON.stringify(dataset, null, 2));

  return zip.generateAsync({ type: "blob" });
}

const APP_VERSION = "0.1.0";
