/// <reference lib="webworker" />
// Runs the deterministic engine off the main thread. Never uses wall-clock
// time as a trading input -- ticks are consumed strictly from the dataset
// supplied by the caller. Progress updates are batched (one postMessage per
// N ticks, configurable) so the UI stays responsive without flooding it.
import { applyTick, createRun, type SimState } from "../engine/simulate";
import { computeEquityCurve } from "../engine/metrics";
import { strategyHash } from "../engine/strategy";
import type { EngineEvent, Order, Position, ProductId, Strategy, Tick } from "../engine/model";

export type WorkerCommand =
  | { type: "start"; runId: string; strategy: Strategy; ticks: Tick[]; startedAt: string; speed: number }
  | { type: "pause" }
  | { type: "resume" }
  | { type: "step" }
  | { type: "cancel" }
  | { type: "reset" }
  | { type: "setSpeed"; speed: number };

export interface WorkerProgressMessage {
  type: "progress";
  cursor: number;
  totalTicks: number;
  currentTs: string | null;
  positions: Position[];
  latestEquity: number;
}

export interface WorkerDoneMessage {
  type: "done";
  status: "completed" | "canceled";
  orders: Order[];
  positions: Position[];
  events: EngineEvent[];
  equitySamples: ReturnType<typeof computeEquityCurve>["samples"];
  maxDrawdown: number;
  endingEquity: number;
}

export type WorkerMessage = WorkerProgressMessage | WorkerDoneMessage | { type: "error"; message: string };

const PROGRESS_BATCH = 25;

let state: SimState | null = null;
let ticks: Tick[] = [];
let cursor = 0;
let running = false;
let canceled = false;
let speed = 1;
let loopTimer: ReturnType<typeof setTimeout> | null = null;

function groupTicksByTs(all: Tick[]): { ts: string; prices: Partial<Record<ProductId, number>> }[] {
  const byTs = new Map<string, Partial<Record<ProductId, number>>>();
  const order: string[] = [];
  for (const t of all) {
    if (!byTs.has(t.ts)) {
      byTs.set(t.ts, {});
      order.push(t.ts);
    }
    byTs.get(t.ts)![t.productId] = t.price;
  }
  return order.map((ts) => ({ ts, prices: byTs.get(ts)! }));
}

let groupedTicks: { ts: string; prices: Partial<Record<ProductId, number>> }[] = [];

function postProgress(): void {
  if (!state) return;
  const positions = Array.from(state.positions.values());
  const lastTs = cursor > 0 ? groupedTicks[cursor - 1]?.ts ?? null : null;
  const eq = computeEquityCurve(state.bankrollUsd, ticks.slice(0, tickCountThrough(cursor)), state.events);
  postMessage({
    type: "progress",
    cursor,
    totalTicks: groupedTicks.length,
    currentTs: lastTs,
    positions,
    latestEquity: eq.samples.length ? eq.samples[eq.samples.length - 1].equity : state.bankrollUsd,
  } satisfies WorkerProgressMessage);
}

function tickCountThrough(groupCursor: number): number {
  if (groupCursor <= 0) return 0;
  const cutoffTs = groupedTicks[groupCursor - 1].ts;
  let count = 0;
  for (const t of ticks) {
    if (t.ts <= cutoffTs) count++;
  }
  return count;
}

function stepOnce(): boolean {
  if (!state || cursor >= groupedTicks.length) return false;
  const { ts, prices } = groupedTicks[cursor];
  applyTick(state, ts, prices);
  cursor++;
  return true;
}

function finish(status: "completed" | "canceled"): void {
  running = false;
  if (loopTimer) clearTimeout(loopTimer);
  if (!state) return;
  const eq = computeEquityCurve(state.bankrollUsd, ticks, state.events);
  const positions = Array.from(state.positions.values());
  postMessage({
    type: "done",
    status,
    orders: state.orders,
    positions,
    events: state.events,
    equitySamples: eq.samples,
    maxDrawdown: eq.maxDrawdown,
    endingEquity: eq.endingEquity,
  } satisfies WorkerDoneMessage);
}

function runLoop(): void {
  if (!running || canceled) return;
  let stepsThisBatch = 0;
  while (running && !canceled && stepsThisBatch < PROGRESS_BATCH) {
    const advanced = stepOnce();
    stepsThisBatch++;
    if (!advanced) {
      finish("completed");
      return;
    }
  }
  postProgress();
  if (canceled) {
    finish("canceled");
    return;
  }
  // speed is a UI-only pacing control (delay between batches); it never
  // changes which ticks are processed or in what order.
  const delayMs = Math.max(0, 16 / Math.max(0.01, speed));
  loopTimer = setTimeout(runLoop, delayMs);
}

self.onmessage = async (ev: MessageEvent<WorkerCommand>) => {
  const cmd = ev.data;
  try {
    switch (cmd.type) {
      case "start": {
        const hash = await strategyHash(cmd.strategy);
        state = createRun(cmd.strategy, cmd.runId, cmd.startedAt, hash);
        ticks = cmd.ticks;
        groupedTicks = groupTicksByTs(ticks);
        cursor = 0;
        canceled = false;
        speed = cmd.speed;
        running = true;
        runLoop();
        break;
      }
      case "pause":
        running = false;
        if (loopTimer) clearTimeout(loopTimer);
        break;
      case "resume":
        if (!running && !canceled) {
          running = true;
          runLoop();
        }
        break;
      case "step":
        if (!running) {
          const advanced = stepOnce();
          postProgress();
          if (!advanced) finish("completed");
        }
        break;
      case "cancel":
        canceled = true;
        running = false;
        if (loopTimer) clearTimeout(loopTimer);
        finish("canceled");
        break;
      case "reset":
        running = false;
        canceled = false;
        state = null;
        ticks = [];
        groupedTicks = [];
        cursor = 0;
        if (loopTimer) clearTimeout(loopTimer);
        break;
      case "setSpeed":
        speed = cmd.speed;
        break;
    }
  } catch (err) {
    postMessage({ type: "error", message: (err as Error).message } satisfies WorkerMessage);
  }
};
