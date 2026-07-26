// Event-sourced equity/drawdown reconstruction. Must match
// quantum_yolo_engine/metrics.py exactly (see tests/parity). Equity is
// replayed strictly from the event ledger and price ticks in chronological
// order -- never projected backward from the final position snapshot.
import type { EngineEvent, EquitySample, ProductId, Tick } from "./model";

export interface EquityCurveResult {
  samples: EquitySample[];
  maxDrawdown: number;
  endingEquity: number;
}

interface ProductState {
  baseQty: number;
  avgEntry: number;
  realizedPnl: number;
  markPrice: number | null;
}

export function computeEquityCurve(
  bankrollUsd: number,
  ticks: Tick[],
  events: EngineEvent[],
): EquityCurveResult {
  const ticksByTs = new Map<string, Tick[]>();
  const tickOrder: string[] = [];
  for (const row of ticks) {
    if (!ticksByTs.has(row.ts)) {
      ticksByTs.set(row.ts, []);
      tickOrder.push(row.ts);
    }
    ticksByTs.get(row.ts)!.push(row);
  }

  const eventsByTs = new Map<string, EngineEvent[]>();
  for (const ev of events) {
    if (!eventsByTs.has(ev.ts)) eventsByTs.set(ev.ts, []);
    eventsByTs.get(ev.ts)!.push(ev);
  }
  for (const list of eventsByTs.values()) list.sort((a, b) => a.sequence - b.sequence);

  const allTs = Array.from(new Set([...tickOrder, ...eventsByTs.keys()])).sort();

  const state = new Map<ProductId, ProductState>();
  const getState = (productId: ProductId): ProductState => {
    if (!state.has(productId)) state.set(productId, { baseQty: 0, avgEntry: 0, realizedPnl: 0, markPrice: null });
    return state.get(productId)!;
  };

  const samples: EquitySample[] = [];
  let runningPeak = bankrollUsd;
  let maxDrawdown = 0;

  for (const ts of allTs) {
    for (const row of ticksByTs.get(ts) ?? []) {
      getState(row.productId).markPrice = row.price;
    }

    for (const ev of eventsByTs.get(ts) ?? []) {
      const payload = (ev.payload ?? {}) as Record<string, number>;
      if (!ev.productId) continue;
      const s = getState(ev.productId);

      if (ev.eventType === "entry_filled") {
        s.baseQty += Number(payload.base_qty);
        s.avgEntry = Number(payload.new_avg_entry);
      } else if (ev.eventType === "stop_filled") {
        s.realizedPnl += Number(payload.realized_pnl);
        s.baseQty = 0;
      } else if (ev.eventType === "tp1_filled") {
        s.realizedPnl += Number(payload.realized_pnl);
        s.baseQty -= Number(payload.qty);
      } else if (ev.eventType === "tp2_filled") {
        s.realizedPnl += Number(payload.realized_pnl);
        s.baseQty = 0;
      }
    }

    if (!ticksByTs.has(ts)) continue;

    let equity = bankrollUsd;
    for (const s of state.values()) {
      equity += s.realizedPnl;
      if (s.baseQty > 0 && s.markPrice !== null) {
        equity += (s.markPrice - s.avgEntry) * s.baseQty;
      }
    }

    runningPeak = Math.max(runningPeak, equity);
    const drawdown = equity - runningPeak;
    maxDrawdown = Math.min(maxDrawdown, drawdown);

    samples.push({ ts, equity: round8(equity), drawdown: round8(drawdown) });
  }

  return {
    samples,
    maxDrawdown: round8(maxDrawdown),
    endingEquity: samples.length ? samples[samples.length - 1].equity : bankrollUsd,
  };
}

export function round8(x: number): number {
  return Math.round(x * 1e8) / 1e8;
}
