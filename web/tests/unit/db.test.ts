import { describe, expect, it } from "vitest";
import "fake-indexeddb/auto";
import { deleteRun, getRun, listRuns, listStrategies, saveRun, saveStrategy } from "../../src/storage/db";
import { defaultStrategy } from "../../src/engine/strategy";
import type { Run } from "../../src/engine/model";

// storage/db.ts memoizes a single DB connection at module scope (by design --
// it's a browser singleton), so these tests share one fake-indexeddb backing
// store across the whole file and use unique ids rather than resetting state.

function makeRun(runId: string): Run {
  const strategy = defaultStrategy();
  return {
    runId,
    status: "completed",
    strategySnapshot: strategy,
    strategyHash: "abc123",
    datasetSnapshot: {
      datasetId: "ds1",
      name: "test",
      source: "bundled",
      createdAt: new Date().toISOString(),
      startTs: new Date().toISOString(),
      endTs: new Date().toISOString(),
      products: ["BTC-USD"],
      rowCount: 10,
      sha256: "def456",
      schemaVersion: 1,
    },
    datasetHash: "def456",
    engineVersion: "0.2.0",
    startedAt: new Date().toISOString(),
    completedAt: new Date().toISOString(),
    cursor: 10,
    eventSequence: 5,
    summary: {
      endingEquity: 1000,
      maxDrawdown: 0,
      totalRealizedPnl: 0,
      totalUnrealizedPnl: 0,
      stopCount: 0,
      tp1Count: 0,
      tp2Count: 0,
      entriesFilledCount: 0,
      durationTicks: 10,
    },
  };
}

describe("storage/db", () => {
  it("saves and retrieves a strategy", async () => {
    await saveStrategy("s1", defaultStrategy());
    const strategies = await listStrategies();
    expect(strategies.some((s) => s.id === "s1")).toBe(true);
  });

  it("saves and retrieves a run", async () => {
    const run = makeRun("run-1");
    await saveRun({ run, orders: [], positions: [], events: [], equitySamples: [] });
    const stored = await getRun("run-1");
    expect(stored?.run.runId).toBe("run-1");
  });

  it("lists runs newest-first", async () => {
    const runA = makeRun("run-a");
    const runB = { ...makeRun("run-b"), startedAt: new Date(Date.now() + 1000).toISOString() };
    await saveRun({ run: runA, orders: [], positions: [], events: [], equitySamples: [] });
    await saveRun({ run: runB, orders: [], positions: [], events: [], equitySamples: [] });
    const runs = await listRuns();
    expect(runs[0].run.runId).toBe("run-b");
  });

  it("deletes a run", async () => {
    const run = makeRun("run-del");
    await saveRun({ run, orders: [], positions: [], events: [], equitySamples: [] });
    await deleteRun("run-del");
    expect(await getRun("run-del")).toBeUndefined();
  });
});
