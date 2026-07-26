import { PRODUCT_IDS, type AssetStrategy, type Strategy } from "./model";

export class StrategyValidationError extends Error {
  readonly errors: string[];
  constructor(errors: string[]) {
    super(errors.join("; "));
    this.name = "StrategyValidationError";
    this.errors = errors;
  }
}

export interface FieldError {
  path: string;
  message: string;
}

function isFinitePositive(x: number): boolean {
  return Number.isFinite(x) && x > 0;
}

/**
 * Validates a full strategy. Returns every violation found (never throws),
 * so the UI can attach each error to its field. Callers that want the
 * throw-on-invalid behavior (e.g. before starting a run) should check
 * `errors.length === 0` themselves or use `assertValidStrategy`.
 */
export function validateStrategy(strategy: Strategy): FieldError[] {
  const errors: FieldError[] = [];

  if (!isFinitePositive(strategy.bankrollUsd)) {
    errors.push({ path: "bankrollUsd", message: "must be a positive finite number" });
  }

  if (!strategy.assets.length) {
    errors.push({ path: "assets", message: "must have at least one asset" });
  }

  let enabledAllocationTotal = 0;
  const seenProductIds = new Set<string>();

  strategy.assets.forEach((asset, assetIndex) => {
    const base = `assets[${assetIndex}]`;

    if (seenProductIds.has(asset.productId)) {
      errors.push({ path: `${base}.productId`, message: `duplicate product ${asset.productId}` });
    }
    seenProductIds.add(asset.productId);

    if (!(PRODUCT_IDS as readonly string[]).includes(asset.productId)) {
      errors.push({ path: `${base}.productId`, message: `unsupported product_id (supported: ${PRODUCT_IDS.join(", ")})` });
    }

    if (!isFinitePositive(asset.allocationUsd)) {
      errors.push({ path: `${base}.allocationUsd`, message: "must be a positive finite number" });
    } else if (asset.enabled) {
      enabledAllocationTotal += asset.allocationUsd;
    }

    if (!isFinitePositive(asset.stopPrice)) {
      errors.push({ path: `${base}.stopPrice`, message: "must be a positive finite number" });
    }

    const tp = asset.takeProfit;
    if (!isFinitePositive(tp.tp1Price)) {
      errors.push({ path: `${base}.takeProfit.tp1Price`, message: "must be a positive finite number" });
    }
    if (!isFinitePositive(tp.tp2Price)) {
      errors.push({ path: `${base}.takeProfit.tp2Price`, message: "must be a positive finite number" });
    }
    if (!Number.isFinite(tp.tp1Fraction) || !(tp.tp1Fraction > 0 && tp.tp1Fraction <= 1)) {
      errors.push({ path: `${base}.takeProfit.tp1Fraction`, message: "must satisfy 0 < fraction <= 1" });
    }
    if (!Number.isFinite(tp.tp2Fraction) || !(tp.tp2Fraction > 0 && tp.tp2Fraction <= 1)) {
      errors.push({ path: `${base}.takeProfit.tp2Fraction`, message: "must satisfy 0 < fraction <= 1" });
    }
    if (Number.isFinite(tp.tp1Fraction) && Number.isFinite(tp.tp2Fraction)) {
      const total = tp.tp1Fraction + tp.tp2Fraction;
      if (total > 1 + 1e-9) {
        errors.push({ path: `${base}.takeProfit`, message: "tp1Fraction + tp2Fraction must be <= 1.0" });
      }
    }
    if (isFinitePositive(tp.tp1Price) && isFinitePositive(tp.tp2Price) && tp.tp1Price >= tp.tp2Price) {
      errors.push({ path: `${base}.takeProfit.tp1Price`, message: "must be < tp2Price" });
    }
    if (isFinitePositive(asset.stopPrice) && isFinitePositive(tp.tp1Price) && asset.stopPrice >= tp.tp1Price) {
      errors.push({ path: `${base}.stopPrice`, message: "must be < takeProfit.tp1Price" });
    }

    if (!asset.entries.length) {
      errors.push({ path: `${base}.entries`, message: "must have at least one entry rule" });
    }

    const seenEntryIds = new Set<string>();
    let entriesTotal = 0;
    asset.entries.forEach((entry, entryIndex) => {
      const entryBase = `${base}.entries[${entryIndex}]`;
      if (seenEntryIds.has(entry.id)) {
        errors.push({ path: `${entryBase}.id`, message: `duplicate entry id ${entry.id}` });
      }
      seenEntryIds.add(entry.id);

      if (!isFinitePositive(entry.price)) {
        errors.push({ path: `${entryBase}.price`, message: "must be a positive finite number" });
      } else if (isFinitePositive(asset.stopPrice) && entry.price <= asset.stopPrice) {
        errors.push({ path: `${entryBase}.price`, message: "must be > stopPrice" });
      }

      if (!isFinitePositive(entry.quoteSizeUsd)) {
        errors.push({ path: `${entryBase}.quoteSizeUsd`, message: "must be a positive finite number" });
      } else {
        entriesTotal += entry.quoteSizeUsd;
      }
    });

    if (asset.enabled && isFinitePositive(asset.allocationUsd) && entriesTotal > asset.allocationUsd + 1e-9) {
      errors.push({
        path: `${base}.entries`,
        message: `entries total ($${entriesTotal.toFixed(2)}) exceeds allocationUsd ($${asset.allocationUsd.toFixed(2)})`,
      });
    }
  });

  if (isFinitePositive(strategy.bankrollUsd) && enabledAllocationTotal > strategy.bankrollUsd + 1e-9) {
    errors.push({
      path: "bankrollUsd",
      message: `total enabled allocations ($${enabledAllocationTotal.toFixed(2)}) exceed bankrollUsd ($${strategy.bankrollUsd.toFixed(2)})`,
    });
  }

  return errors;
}

export function assertValidStrategy(strategy: Strategy): void {
  const errors = validateStrategy(strategy);
  if (errors.length) {
    throw new StrategyValidationError(errors.map((e) => `${e.path}: ${e.message}`));
  }
}

export function isValidAssetStrategy(asset: AssetStrategy): boolean {
  return (PRODUCT_IDS as readonly string[]).includes(asset.productId);
}
