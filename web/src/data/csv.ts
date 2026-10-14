// CSV dataset import. Turns an uploaded (or bundled) `ts,product_id,price`
// file into validated ticks for the engine. Same row format the Python
// reference engine replays via `CsvMarketFeed` (quantum_yolo_engine/feeds.py).
//
// File-level problems (empty file, missing columns, no usable rows) and data
// that would silently corrupt a run (unsupported products, non-positive or
// non-numeric prices) throw CsvImportError. Recoverable row-level problems
// (unparseable timestamps, short rows, duplicate (ts, product_id) pairs,
// out-of-order rows) are fixed or dropped and reported as warnings.
//
// Missing assets are forward-filled by the engine at replay time, never here:
// the returned ticks are exactly the observations in the file.

import { PRODUCT_IDS, type ProductId, type Tick } from "../engine/model";

export const MAX_CSV_BYTES = 25 * 1024 * 1024;

const REQUIRED_COLUMNS = ["ts", "product_id", "price"] as const;
const MAX_ERRORS_IN_MESSAGE = 5;

export interface CsvIssue {
  /** 1-based line number in the file (the header is line 1). */
  row?: number;
  message: string;
}

export interface CsvImportResult {
  ticks: Tick[];
  products: ProductId[];
  startTs: string;
  endTs: string;
  rowCount: number;
  warnings: CsvIssue[];
}

export class CsvImportError extends Error {
  readonly issues: CsvIssue[];
  constructor(issues: CsvIssue[]) {
    const shown = issues
      .slice(0, MAX_ERRORS_IN_MESSAGE)
      .map((i) => (i.row ? `row ${i.row}: ${i.message}` : i.message));
    const more = issues.length > MAX_ERRORS_IN_MESSAGE ? ` (and ${issues.length - MAX_ERRORS_IN_MESSAGE} more)` : "";
    super(`${shown.join("; ")}${more}`);
    this.name = "CsvImportError";
    this.issues = issues;
  }
}

/** Splits one CSV line, honoring double-quoted fields and `""` escapes. */
function splitCsvLine(line: string): string[] {
  const fields: string[] = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      fields.push(field);
      field = "";
    } else {
      field += ch;
    }
  }
  fields.push(field);
  return fields.map((f) => f.trim());
}

// ISO 8601 date or date-time ("T" or space separator), optional fractional
// seconds and offset. Offset-less values are read as UTC, matching the Python
// engine's `pd.to_datetime(..., utc=True)` rather than the browser's local zone.
const ISO_TS = /^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?(Z|[+-]\d{2}:?\d{2})?$/i;

/** Returns the timestamp as a canonical UTC ISO string, or null if invalid. */
function normalizeTimestamp(raw: string): string | null {
  const m = ISO_TS.exec(raw);
  if (!m) return null;
  let value = raw.replace(" ", "T");
  if (!m[1]) value += value.includes("T") ? "Z" : "T00:00:00Z";
  else if (/^[+-]\d{4}$/.test(m[1])) value = `${value.slice(0, -2)}:${value.slice(-2)}`;
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? null : new Date(ms).toISOString();
}

function isProductId(value: string): value is ProductId {
  return (PRODUCT_IDS as readonly string[]).includes(value);
}

/**
 * Parses and validates a `ts,product_id,price` CSV. Extra columns are
 * ignored. Throws CsvImportError if the file cannot be used; otherwise returns
 * ticks sorted by timestamp (stable, so same-timestamp rows keep file order)
 * plus any warnings about rows that were dropped or reordered.
 */
export function parseAndValidateCsv(text: string): CsvImportResult {
  if (text.length > MAX_CSV_BYTES) {
    throw new CsvImportError([{ message: `file too large (limit ${MAX_CSV_BYTES / 1024 / 1024}MB)` }]);
  }

  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/);
  const headerIndex = lines.findIndex((l) => l.trim() !== "");
  if (headerIndex === -1) {
    throw new CsvImportError([{ message: "file is empty" }]);
  }

  const header = splitCsvLine(lines[headerIndex]).map((h) => h.toLowerCase());
  const missing = REQUIRED_COLUMNS.filter((c) => !header.includes(c));
  if (missing.length) {
    throw new CsvImportError([
      { message: `missing required column(s): ${missing.join(", ")} (expected ${REQUIRED_COLUMNS.join(",")})` },
    ]);
  }
  const tsCol = header.indexOf("ts");
  const productCol = header.indexOf("product_id");
  const priceCol = header.indexOf("price");
  const minFields = Math.max(tsCol, productCol, priceCol) + 1;

  const errors: CsvIssue[] = [];
  const warnings: CsvIssue[] = [];
  const parsed: { tick: Tick; epochMs: number; row: number }[] = [];

  for (let i = headerIndex + 1; i < lines.length; i++) {
    if (lines[i].trim() === "") continue;
    const row = i + 1;
    const fields = splitCsvLine(lines[i]);
    if (fields.length < minFields) {
      warnings.push({ row, message: `expected at least ${minFields} columns, found ${fields.length}; row skipped` });
      continue;
    }

    const productId = fields[productCol];
    if (!isProductId(productId)) {
      errors.push({ row, message: `unsupported product_id "${productId}" (supported: ${PRODUCT_IDS.join(", ")})` });
      continue;
    }

    const rawPrice = fields[priceCol];
    const price = rawPrice === "" ? Number.NaN : Number(rawPrice);
    if (!Number.isFinite(price) || price <= 0) {
      errors.push({ row, message: `price must be a positive number, got "${rawPrice}"` });
      continue;
    }

    const ts = normalizeTimestamp(fields[tsCol]);
    if (ts === null) {
      warnings.push({ row, message: `invalid timestamp "${fields[tsCol]}"; row skipped` });
      continue;
    }

    parsed.push({ tick: { ts, productId, price }, epochMs: Date.parse(ts), row });
  }

  if (errors.length) throw new CsvImportError(errors);
  if (!parsed.length) {
    throw new CsvImportError([{ message: "no valid data rows" }, ...warnings]);
  }

  if (parsed.some((p, i) => i > 0 && p.epochMs < parsed[i - 1].epochMs)) {
    warnings.push({ message: "rows are not in timestamp order; sorted by timestamp" });
    parsed.sort((a, b) => a.epochMs - b.epochMs);
  }

  const seen = new Map<string, number>();
  const ticks: Tick[] = [];
  for (const p of parsed) {
    const key = `${p.tick.ts}|${p.tick.productId}`;
    const firstRow = seen.get(key);
    if (firstRow !== undefined) {
      warnings.push({ row: p.row, message: `duplicate (ts, product_id) of row ${firstRow}; row dropped` });
      continue;
    }
    seen.set(key, p.row);
    ticks.push(p.tick);
  }

  const present = new Set(ticks.map((t) => t.productId));
  return {
    ticks,
    products: PRODUCT_IDS.filter((id) => present.has(id)),
    startTs: ticks[0].ts,
    endTs: ticks[ticks.length - 1].ts,
    rowCount: ticks.length,
    warnings,
  };
}
