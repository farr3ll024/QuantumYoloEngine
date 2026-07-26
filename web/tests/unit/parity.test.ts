import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { applyTick, createRun } from "../../src/engine/simulate";
import { computeEquityCurve } from "../../src/engine/metrics";
import { strategyHash } from "../../src/engine/strategy";
import { fixtureToStrategy, fixtureTicks, normalizeForComparison, deepRound, type ParityFixture } from "../../src/engine/parity";

// Strips the strategy_loaded event's Python-only `snapshot`/`strategy_source_path`
// payload fields down to just `sha256` -- the TS engine intentionally emits a
// slimmer payload for this bootstrap metadata event since the full snapshot is
// already available at fixture.strategy. The sha256 itself must still match.
function slimStrategyLoadedPayload(events: Record<string, unknown>[]): Record<string, unknown>[] {
  return events.map((e) =>
    e.eventType === "strategy_loaded" && e.payload && typeof e.payload === "object"
      ? { ...e, payload: { sha256: (e.payload as { sha256: string }).sha256 } }
      : e,
  );
}

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES_DIR = join(__dirname, "../../../tests/parity/fixtures");

const fixtureFiles = readdirSync(FIXTURES_DIR).filter((f) => f.endsWith(".json"));

describe("cross-engine parity against Python-generated fixtures", () => {
  it("found fixtures to test against", () => {
    expect(fixtureFiles.length).toBeGreaterThanOrEqual(10);
  });

  for (const file of fixtureFiles) {
    it(`matches fixture ${file}`, async () => {
      const fixture: ParityFixture = JSON.parse(readFileSync(join(FIXTURES_DIR, file), "utf-8"));
      const strategy = fixtureToStrategy(fixture);
      const ticks = fixtureTicks(fixture);

      const bootstrapTs = fixture.expectedEvents[0].ts as string;
      const hash = await strategyHash(strategy);
      expect(hash).toBe(fixture.strategyHash);
      const state = createRun(strategy, `fixture-${fixture.name}`, bootstrapTs, hash);

      const byTs = new Map<string, Record<string, number>>();
      for (const t of ticks) {
        if (!byTs.has(t.ts)) byTs.set(t.ts, {});
        byTs.get(t.ts)![t.productId] = t.price;
      }
      for (const [ts, prices] of Array.from(byTs.entries()).sort((a, b) => a[0].localeCompare(b[0]))) {
        applyTick(state, ts, prices);
      }

      const dp = fixture.roundDp;

      // orders: compare type/side/status/price, ignoring wall-clock created_at for entry orders.
      // Python's fixture generator extracts rows via `order by created_at, order_id`, so match
      // that sort here rather than relying on insertion order.
      const sortedOrders = [...state.orders].sort(
        (a, b) => a.createdAt.localeCompare(b.createdAt) || a.orderId.localeCompare(b.orderId),
      );
      const actualOrders = sortedOrders.map((o) => ({
        order_id: o.orderId,
        product_id: o.productId,
        order_type: o.orderType,
        rule_id: o.ruleId,
        side: o.side,
        price: deepRound(o.limitOrTriggerPrice, dp),
        quote_size_usd: o.quoteSizeUsd === null ? null : deepRound(o.quoteSizeUsd, dp),
        base_size: o.baseSize,
        status: o.status,
        created_at: o.createdAt,
        filled_at: o.filledAt,
      }));
      expect(normalizeForComparison(actualOrders, bootstrapTs)).toEqual(
        normalizeForComparison(fixture.expectedOrders, bootstrapTs),
      );

      const actualPositions = Array.from(state.positions.values())
        .sort((a, b) => a.productId.localeCompare(b.productId))
        .map((p) => ({
          product_id: p.productId,
          base_qty: deepRound(p.baseQty, dp),
          avg_entry: deepRound(p.avgEntry, dp),
          invested_quote: deepRound(p.investedQuote, dp),
          realized_pnl: deepRound(p.realizedPnl, dp),
          state: p.state,
          tp1_done: p.tp1Done ? 1 : 0,
          tp2_done: p.tp2Done ? 1 : 0,
          stop_done: p.stopDone ? 1 : 0,
          active_stop_price: deepRound(p.activeStopPrice, dp),
        }));
      expect(actualPositions).toEqual(fixture.expectedPositions);

      const actualEvents = state.events.map((e) => ({
        sequence: e.sequence,
        ts: e.ts,
        level: e.level,
        productId: e.productId,
        eventType: e.eventType,
        message: e.message,
        payload: e.payload ? deepRound(e.payload, dp) : null,
      }));
      expect(normalizeForComparison(slimStrategyLoadedPayload(actualEvents), bootstrapTs)).toEqual(
        normalizeForComparison(slimStrategyLoadedPayload(fixture.expectedEvents), bootstrapTs),
      );

      const equity = computeEquityCurve(fixture.bankrollUsd, ticks, state.events);
      const actualEquitySamples = equity.samples.map((s) => ({
        ts: s.ts,
        equity: deepRound(s.equity, dp),
        drawdown: deepRound(s.drawdown, dp),
      }));
      expect(actualEquitySamples).toEqual(fixture.expectedEquitySamples);

      const positions = Array.from(state.positions.values());
      const summary = {
        ending_equity: deepRound(equity.endingEquity, dp),
        max_drawdown: deepRound(equity.maxDrawdown, dp),
        total_realized_pnl: deepRound(
          positions.reduce((s, p) => s + p.realizedPnl, 0),
          dp,
        ),
        stop_count: positions.filter((p) => p.stopDone).length,
        tp1_count: positions.filter((p) => p.tp1Done).length,
        tp2_count: positions.filter((p) => p.tp2Done).length,
        entries_filled_count: state.orders.filter((o) => o.orderType === "entry" && o.status === "filled").length,
      };
      expect(summary).toEqual(fixture.expectedSummary);
    });
  }
});
