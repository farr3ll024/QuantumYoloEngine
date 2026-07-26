// Deterministic paper-trading state machine. A direct behavioral port of
// quantum_yolo_engine/engine.py — see tests/parity fixtures for the shared
// contract both engines must satisfy. Never reads wall-clock time; every
// timestamp comes from the caller (a tick ts, or an explicit startedAt).

import type {
  AssetStrategy,
  EngineEvent,
  EventLevel,
  Order,
  OrderType,
  Position,
  ProductId,
  Strategy,
} from "./model";
import { ENGINE_VERSION } from "./model";

export interface SimState {
  runId: string;
  bankrollUsd: number;
  strategies: Map<ProductId, AssetStrategy>;
  moveStopToBreakevenAfterTp1: boolean;
  positions: Map<ProductId, Position>;
  orders: Order[];
  events: EngineEvent[];
  nextSequence: number;
  lastEntryTsByProduct: Map<ProductId, string>;
  strategyHash: string;
  engineVersion: string;
}

function orderId(runId: string, productId: ProductId, ruleId: string): string {
  return `${runId}:${productId}:${ruleId}`;
}

function logEvent(
  state: SimState,
  level: EventLevel,
  eventType: string,
  message: string,
  productId: ProductId | null,
  ts: string,
  payload: Record<string, unknown> | null = null,
): void {
  const sequence = state.nextSequence++;
  state.events.push({ runId: state.runId, sequence, ts, level, eventType, productId, message, payload });
}

function openOrdersByType(state: SimState, productId: ProductId, orderType: OrderType): Order[] {
  return state.orders.filter((o) => o.productId === productId && o.orderType === orderType && o.status === "open");
}

function ordersByType(state: SimState, productId: ProductId, orderType: OrderType): Order[] {
  return state.orders.filter((o) => o.productId === productId && o.orderType === orderType);
}

function insertOrder(
  state: SimState,
  productId: ProductId,
  orderType: OrderType,
  ruleId: string,
  side: "buy" | "sell",
  price: number,
  quoteSizeUsd: number | null,
  ts: string,
): void {
  const id = orderId(state.runId, productId, ruleId);
  if (state.orders.some((o) => o.orderId === id)) return;
  state.orders.push({
    runId: state.runId,
    orderId: id,
    ruleId,
    productId,
    orderType,
    side,
    status: "open",
    limitOrTriggerPrice: price,
    quoteSizeUsd,
    baseSize: null,
    createdAt: ts,
    filledAt: null,
  });
}

function markOrderFilled(state: SimState, id: string, ts: string): void {
  const order = state.orders.find((o) => o.orderId === id);
  if (order) {
    order.status = "filled";
    order.filledAt = ts;
  }
}

function cancelOpenOrders(state: SimState, productId: ProductId, orderType?: OrderType): void {
  for (const o of state.orders) {
    if (o.productId === productId && o.status === "open" && (!orderType || o.orderType === orderType)) {
      o.status = "canceled";
    }
  }
}

/**
 * strategyHashHex must be computed by the caller via strategy.ts's
 * `strategyHash()` (async, real SHA-256) before calling createRun --
 * createRun itself stays synchronous so it can run inside a plain reducer
 * or the worker's message handler without an extra microtask hop per tick.
 */
export function createRun(strategy: Strategy, runId: string, startedAt: string, strategyHashHex: string): SimState {
  const strategies = new Map<ProductId, AssetStrategy>();
  for (const asset of strategy.assets) strategies.set(asset.productId, asset);

  const state: SimState = {
    runId,
    bankrollUsd: strategy.bankrollUsd,
    strategies,
    moveStopToBreakevenAfterTp1: strategy.moveStopToBreakevenAfterTp1,
    positions: new Map(),
    orders: [],
    events: [],
    nextSequence: 1,
    lastEntryTsByProduct: new Map(),
    strategyHash: strategyHashHex,
    engineVersion: ENGINE_VERSION,
  };

  logEvent(state, "info", "strategy_loaded", `strategy loaded (sha256=${state.strategyHash.slice(0, 12)}…)`, null, startedAt, {
    sha256: state.strategyHash,
  });

  for (const asset of strategy.assets) {
    if (!asset.enabled) continue;

    state.positions.set(asset.productId, {
      runId,
      productId: asset.productId,
      baseQty: 0,
      avgEntry: 0,
      investedQuote: 0,
      realizedPnl: 0,
      state: "waiting_for_entry",
      tp1Done: false,
      tp2Done: false,
      stopDone: false,
      activeStopPrice: asset.stopPrice,
    });
    logEvent(state, "info", "bootstrap_position", "created initial position state", asset.productId, startedAt);

    for (const entry of asset.entries) {
      insertOrder(state, asset.productId, "entry", entry.id, "buy", entry.price, entry.quoteSizeUsd, startedAt);
    }
    logEvent(state, "info", "seed_entries", "seeded entry ladder orders", asset.productId, startedAt);
  }

  return state;
}

export function applyTick(state: SimState, ts: string, prices: Partial<Record<ProductId, number>>): void {
  for (const [productId, price] of Object.entries(prices) as [ProductId, number][]) {
    const strat = state.strategies.get(productId);
    if (!strat || !strat.enabled) continue;

    let pos = state.positions.get(productId);
    if (!pos) continue;

    if (pos.baseQty > 0 && pos.state === "waiting_for_entry") {
      pos.state = "active";
    }

    fillEntries(state, strat, pos, price, ts);
    pos = state.positions.get(productId)!;

    if (pos.baseQty > 0 && !pos.stopDone) {
      ensureExitOrders(state, strat, pos, ts);
    }

    fillStopIfHit(state, strat, productId, price, ts);
    pos = state.positions.get(productId)!;

    if (pos.stopDone || pos.baseQty <= 0) continue;

    fillTpsIfHit(state, strat, productId, price, ts);
  }
}

function fillEntries(state: SimState, strat: AssetStrategy, pos: Position, marketPrice: number, ts: string): void {
  const openEntries = openOrdersByType(state, strat.productId, "entry");
  for (const order of openEntries) {
    const limitPrice = order.limitOrTriggerPrice;
    if (marketPrice > limitPrice) continue;

    const quoteSize = order.quoteSizeUsd!;
    const fillPrice = Math.min(limitPrice, marketPrice);
    const baseQty = quoteSize / fillPrice;

    const newBase = pos.baseQty + baseQty;
    if (newBase <= 0) continue;

    const newAvg = pos.baseQty <= 0 ? fillPrice : (pos.avgEntry * pos.baseQty + fillPrice * baseQty) / newBase;

    pos.baseQty = newBase;
    pos.avgEntry = newAvg;
    pos.investedQuote += quoteSize;
    pos.state = "active";

    if (pos.activeStopPrice <= 0) pos.activeStopPrice = strat.stopPrice;

    if (pos.activeStopPrice >= newAvg) {
      const originalStop = pos.activeStopPrice;
      const adjustedStop = Math.round(newAvg * 0.995 * 100) / 100;
      pos.activeStopPrice = adjustedStop;
      logEvent(
        state,
        "warn",
        "stop_adjusted",
        `adjusted stop from ${originalStop.toFixed(2)} to ${adjustedStop.toFixed(2)} (stop must be below avg entry)`,
        strat.productId,
        ts,
        { original_stop: originalStop, adjusted_stop: adjustedStop, avg_entry: newAvg, fill_price: fillPrice },
      );
    }

    state.lastEntryTsByProduct.set(strat.productId, ts);
    markOrderFilled(state, order.orderId, ts);

    logEvent(state, "info", "entry_filled", `filled entry ${order.ruleId} at ${fillPrice.toFixed(2)}`, strat.productId, ts, {
      order_id: order.orderId,
      rule_id: order.ruleId,
      quote_size: quoteSize,
      base_qty: baseQty,
      fill_price: fillPrice,
      new_avg_entry: newAvg,
      market_price: marketPrice,
      limit_price: limitPrice,
    });
  }
}

function ensureExitOrders(state: SimState, strat: AssetStrategy, pos: Position, ts: string): void {
  const stopPrice = pos.activeStopPrice > 0 ? pos.activeStopPrice : strat.stopPrice;

  if (!openOrdersByType(state, strat.productId, "stop").length) {
    insertOrder(state, strat.productId, "stop", "stop", "sell", stopPrice, null, ts);
  }
  if (!pos.tp1Done && !openOrdersByType(state, strat.productId, "tp1").length) {
    insertOrder(state, strat.productId, "tp1", "tp1", "sell", strat.takeProfit.tp1Price, null, ts);
  }
  if (!pos.tp2Done && !openOrdersByType(state, strat.productId, "tp2").length) {
    insertOrder(state, strat.productId, "tp2", "tp2", "sell", strat.takeProfit.tp2Price, null, ts);
  }
}

function fillStopIfHit(state: SimState, strat: AssetStrategy, productId: ProductId, marketPrice: number, ts: string): void {
  const pos = state.positions.get(productId);
  if (!pos || pos.baseQty <= 0 || pos.stopDone) return;

  const stopPrice = pos.activeStopPrice > 0 ? pos.activeStopPrice : strat.stopPrice;
  if (state.lastEntryTsByProduct.get(productId) === ts) return;
  if (marketPrice > stopPrice) return;

  const qty = pos.baseQty;
  const fillPrice = Math.min(marketPrice, stopPrice);
  const realized = (fillPrice - pos.avgEntry) * qty;

  pos.realizedPnl += realized;
  pos.baseQty = 0;
  pos.state = "stopped_out";
  pos.stopDone = true;

  cancelOpenOrders(state, productId, "tp1");
  cancelOpenOrders(state, productId, "tp2");

  const openStops = openOrdersByType(state, productId, "stop");
  if (openStops.length) markOrderFilled(state, openStops[0].orderId, ts);

  logEvent(state, "warn", "stop_filled", `stop filled at ${fillPrice.toFixed(2)}`, productId, ts, {
    qty,
    realized_pnl: realized,
    market_price: marketPrice,
    stop_price: stopPrice,
  });
}

function fillTpsIfHit(state: SimState, strat: AssetStrategy, productId: ProductId, marketPrice: number, ts: string): void {
  let pos = state.positions.get(productId);
  if (!pos || pos.baseQty <= 0) return;

  if (!pos.tp1Done && marketPrice >= strat.takeProfit.tp1Price) {
    const qty = pos.baseQty * strat.takeProfit.tp1Fraction;
    const fillPrice = Math.max(marketPrice, strat.takeProfit.tp1Price);
    const realized = (fillPrice - pos.avgEntry) * qty;

    pos.baseQty -= qty;
    pos.realizedPnl += realized;
    pos.tp1Done = true;
    pos.state = "tp1_hit";

    const openTp1 = openOrdersByType(state, productId, "tp1");
    if (openTp1.length) markOrderFilled(state, openTp1[0].orderId, ts);

    if (state.moveStopToBreakevenAfterTp1) {
      const oldStop = pos.activeStopPrice;
      pos.activeStopPrice = Math.round(pos.avgEntry * 100) / 100;
      cancelOpenOrders(state, productId, "stop");
      logEvent(
        state,
        "info",
        "stop_moved",
        `moved stop to breakeven from ${oldStop.toFixed(2)} to ${pos.activeStopPrice.toFixed(2)}`,
        productId,
        ts,
      );
    }

    logEvent(state, "info", "tp1_filled", `tp1 filled at ${fillPrice.toFixed(2)}`, productId, ts, {
      qty,
      realized_pnl: realized,
      market_price: marketPrice,
      tp1_price: strat.takeProfit.tp1Price,
    });
  }

  pos = state.positions.get(productId);
  if (!pos || pos.baseQty <= 0) return;

  if (!pos.tp2Done && marketPrice >= strat.takeProfit.tp2Price) {
    const qty = pos.baseQty;
    const fillPrice = Math.max(marketPrice, strat.takeProfit.tp2Price);
    const realized = (fillPrice - pos.avgEntry) * qty;

    pos.baseQty = 0;
    pos.realizedPnl += realized;
    pos.tp2Done = true;
    pos.state = "completed";

    const openTp2 = openOrdersByType(state, productId, "tp2");
    if (openTp2.length) markOrderFilled(state, openTp2[0].orderId, ts);

    cancelOpenOrders(state, productId, "stop");

    logEvent(state, "info", "tp2_filled", `tp2 filled at ${fillPrice.toFixed(2)}`, productId, ts, {
      qty,
      realized_pnl: realized,
      market_price: marketPrice,
      tp2_price: strat.takeProfit.tp2Price,
    });
  }
}

export { ordersByType };
