import { describe, expect, it } from "vitest";
import { defaultStrategy } from "../../src/engine/strategy";
import { validateStrategy } from "../../src/engine/validate";
import type { Strategy } from "../../src/engine/model";

describe("validateStrategy", () => {
  it("accepts the default strategy", () => {
    expect(validateStrategy(defaultStrategy())).toEqual([]);
  });

  it("rejects a non-positive bankroll", () => {
    const strat = defaultStrategy();
    strat.bankrollUsd = -1;
    const errors = validateStrategy(strat);
    expect(errors.some((e) => e.path === "bankrollUsd")).toBe(true);
  });

  it("rejects allocations exceeding bankroll", () => {
    const strat = defaultStrategy();
    strat.bankrollUsd = 10;
    const errors = validateStrategy(strat);
    expect(errors.some((e) => e.message.includes("exceed bankrollUsd"))).toBe(true);
  });

  it("rejects duplicate entry ids", () => {
    const strat = defaultStrategy();
    strat.assets[0].entries[1].id = strat.assets[0].entries[0].id;
    const errors = validateStrategy(strat);
    expect(errors.some((e) => e.message.includes("duplicate entry id"))).toBe(true);
  });

  it("rejects tp1Fraction + tp2Fraction over 1", () => {
    const strat = defaultStrategy();
    strat.assets[0].takeProfit.tp1Fraction = 0.8;
    strat.assets[0].takeProfit.tp2Fraction = 0.8;
    const errors = validateStrategy(strat);
    expect(errors.some((e) => e.message.includes("tp1Fraction + tp2Fraction"))).toBe(true);
  });

  it("rejects unsupported product ids", () => {
    const strat = defaultStrategy();
    (strat.assets[0] as { productId: string }).productId = "DOGE-USD";
    const errors = validateStrategy(strat as unknown as Strategy);
    expect(errors.some((e) => e.message.includes("unsupported product_id"))).toBe(true);
  });

  it("rejects stop >= tp1", () => {
    const strat = defaultStrategy();
    strat.assets[0].stopPrice = strat.assets[0].takeProfit.tp1Price + 1;
    const errors = validateStrategy(strat);
    expect(errors.some((e) => e.message.includes("must be < takeProfit.tp1Price"))).toBe(true);
  });

  it("rejects non-finite values", () => {
    const strat = defaultStrategy();
    strat.assets[0].stopPrice = Number.POSITIVE_INFINITY;
    const errors = validateStrategy(strat);
    expect(errors.some((e) => e.path.endsWith("stopPrice"))).toBe(true);
  });
});
