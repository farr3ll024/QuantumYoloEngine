import { describe, expect, it } from "vitest";
import { CsvImportError, parseAndValidateCsv } from "../../src/data/csv";

describe("parseAndValidateCsv", () => {
  it("parses a well-formed csv", () => {
    const csv = "ts,product_id,price\n2026-01-01T00:00:00Z,BTC-USD,100\n2026-01-01T00:00:00Z,ETH-USD,10\n";
    const result = parseAndValidateCsv(csv);
    expect(result.rowCount).toBe(2);
    expect(result.products.sort()).toEqual(["BTC-USD", "ETH-USD"]);
  });

  it("forward-fills a missing asset without inventing values before its first observation", () => {
    const csv =
      "ts,product_id,price\n" +
      "2026-01-01T00:00:00Z,BTC-USD,100\n" +
      "2026-01-01T00:01:00Z,ETH-USD,10\n";
    const result = parseAndValidateCsv(csv);
    expect(result.ticks.filter((t) => t.productId === "ETH-USD")).toHaveLength(1);
  });

  it("rejects missing required columns", () => {
    expect(() => parseAndValidateCsv("ts,price\n2026-01-01T00:00:00Z,100\n")).toThrow(CsvImportError);
  });

  it("rejects an empty file", () => {
    expect(() => parseAndValidateCsv("")).toThrow(CsvImportError);
  });

  it("rejects non-positive prices", () => {
    const csv = "ts,product_id,price\n2026-01-01T00:00:00Z,BTC-USD,-5\n";
    expect(() => parseAndValidateCsv(csv)).toThrow(CsvImportError);
  });

  it("rejects unsupported product ids", () => {
    const csv = "ts,product_id,price\n2026-01-01T00:00:00Z,DOGE-USD,5\n";
    expect(() => parseAndValidateCsv(csv)).toThrow(CsvImportError);
  });

  it("flags duplicate (ts, product_id) rows as warnings and drops the duplicate", () => {
    const csv =
      "ts,product_id,price\n" +
      "2026-01-01T00:00:00Z,BTC-USD,100\n" +
      "2026-01-01T00:00:00Z,BTC-USD,101\n";
    const result = parseAndValidateCsv(csv);
    expect(result.rowCount).toBe(1);
    expect(result.warnings.some((w) => w.message.includes("duplicate"))).toBe(true);
  });

  it("sorts unordered rows and warns", () => {
    const csv =
      "ts,product_id,price\n" +
      "2026-01-01T00:02:00Z,BTC-USD,102\n" +
      "2026-01-01T00:00:00Z,BTC-USD,100\n";
    const result = parseAndValidateCsv(csv);
    expect(result.ticks[0].price).toBe(100);
    expect(result.warnings.some((w) => w.message.includes("not in timestamp order"))).toBe(true);
  });

  it("rejects invalid timestamps as row-level issues", () => {
    const csv = "ts,product_id,price\nnot-a-date,BTC-USD,100\n2026-01-01T00:00:00Z,BTC-USD,101\n";
    const result = parseAndValidateCsv(csv);
    expect(result.warnings.some((w) => w.message.includes("invalid timestamp"))).toBe(true);
    expect(result.rowCount).toBe(1);
  });
});
