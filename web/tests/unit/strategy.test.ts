import { describe, expect, it } from "vitest";
import { defaultStrategy, strategyFromYaml, strategyToYaml, strategyHash } from "../../src/engine/strategy";

describe("strategy YAML import/export", () => {
  it("round-trips through YAML without losing data", () => {
    const original = defaultStrategy();
    const yaml = strategyToYaml(original);
    const reimported = strategyFromYaml(yaml, original);

    expect(reimported.bankrollUsd).toBe(original.bankrollUsd);
    expect(reimported.assets).toHaveLength(original.assets.length);
    expect(reimported.assets[0].entries).toHaveLength(original.assets[0].entries.length);
    expect(reimported.assets[0].stopPrice).toBe(original.assets[0].stopPrice);
  });

  it("throws a StrategyImportError on invalid YAML", () => {
    expect(() => strategyFromYaml("not: valid: yaml: at: all:")).toThrow();
  });

  it("throws on a document missing required fields", () => {
    expect(() => strategyFromYaml("bankroll_usd: 100\n")).toThrow();
  });
});

describe("strategyHash", () => {
  it("is stable for identical strategies", async () => {
    const a = defaultStrategy();
    const b = defaultStrategy();
    expect(await strategyHash(a)).toBe(await strategyHash(b));
  });

  it("changes when a value changes", async () => {
    const a = defaultStrategy();
    const b = defaultStrategy();
    b.assets[0].stopPrice += 1;
    expect(await strategyHash(a)).not.toBe(await strategyHash(b));
  });

  it("produces a real 64-character hex sha256 digest", async () => {
    const hash = await strategyHash(defaultStrategy());
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });
});
