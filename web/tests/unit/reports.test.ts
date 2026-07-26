import { describe, expect, it } from "vitest";
import { reconstructTrades, buildReportZip } from "../../src/engine/reports";
import { defaultStrategy } from "../../src/engine/strategy";
import type { EngineEvent, Run } from "../../src/engine/model";

function ev(partial: Partial<EngineEvent> & Pick<EngineEvent, "sequence" | "ts" | "eventType" | "productId">): EngineEvent {
  return { runId: "r1", level: "info", message: "", payload: null, ...partial };
}

describe("reconstructTrades", () => {
  it("pairs an entry with its stop exit", () => {
    const events: EngineEvent[] = [
      ev({ sequence: 1, ts: "t1", eventType: "entry_filled", productId: "BTC-USD", payload: { base_qty: 1, new_avg_entry: 100 } }),
      ev({ sequence: 2, ts: "t2", eventType: "stop_filled", productId: "BTC-USD", payload: { realized_pnl: -10 } }),
    ];
    const trades = reconstructTrades(events);
    expect(trades).toHaveLength(1);
    expect(trades[0].exitReason).toBe("stop");
    expect(trades[0].realizedPnl).toBe(-10);
  });

  it("leaves an unmatched entry as open", () => {
    const events: EngineEvent[] = [
      ev({ sequence: 1, ts: "t1", eventType: "entry_filled", productId: "BTC-USD", payload: { base_qty: 1, new_avg_entry: 100 } }),
    ];
    const trades = reconstructTrades(events);
    expect(trades[0].exitReason).toBe("open");
  });
});

describe("buildReportZip", () => {
  it("produces a non-empty zip blob containing the required files", async () => {
    const strategy = defaultStrategy();
    const run: Run = {
      runId: "r1",
      status: "completed",
      strategySnapshot: strategy,
      strategyHash: "hash1",
      datasetSnapshot: {
        datasetId: "d1",
        name: "test",
        source: "bundled",
        createdAt: "t",
        startTs: "t",
        endTs: "t",
        products: ["BTC-USD"],
        rowCount: 1,
        sha256: "hash2",
        schemaVersion: 1,
      },
      datasetHash: "hash2",
      engineVersion: "0.2.0",
      startedAt: "t",
      completedAt: "t",
      cursor: 1,
      eventSequence: 0,
      summary: {
        endingEquity: 1000,
        maxDrawdown: 0,
        totalRealizedPnl: 0,
        totalUnrealizedPnl: 0,
        stopCount: 0,
        tp1Count: 0,
        tp2Count: 0,
        entriesFilledCount: 0,
        durationTicks: 1,
      },
    };

    const blob = await buildReportZip({
      run,
      strategy,
      dataset: run.datasetSnapshot,
      orders: [],
      positions: [],
      events: [],
      equitySamples: [],
    });

    expect(blob.size).toBeGreaterThan(0);

    const JSZip = (await import("jszip")).default;
    const zip = await JSZip.loadAsync(blob);
    for (const name of ["README.md", "manifest.json", "summary.json", "equity_curve.csv", "trades.csv", "strategy_snapshot.yaml"]) {
      expect(zip.file(name)).not.toBeNull();
    }
  });
});
