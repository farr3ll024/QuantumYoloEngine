import { useState } from "react";
import DataTable, { type Column } from "../../components/DataTable";
import { reconstructTrades, type TradeRound } from "../../engine/reports";
import type { EngineEvent, Order, Position } from "../../engine/model";

interface Props {
  positions: Position[];
  orders: Order[];
  events: EngineEvent[];
}

type TabKey = "positions" | "orders" | "events" | "trades";
const TABS: { key: TabKey; label: string }[] = [
  { key: "positions", label: "Positions" },
  { key: "orders", label: "Orders" },
  { key: "events", label: "Events" },
  { key: "trades", label: "Trades" },
];

const positionColumns: Column<Position>[] = [
  { key: "productId", header: "Asset", render: (r) => r.productId },
  { key: "state", header: "State", render: (r) => r.state },
  { key: "baseQty", header: "Qty", render: (r) => r.baseQty.toFixed(8), sortValue: (r) => r.baseQty },
  { key: "avgEntry", header: "Avg entry", render: (r) => r.avgEntry.toFixed(2), sortValue: (r) => r.avgEntry },
  { key: "realizedPnl", header: "Realized P&L", render: (r) => r.realizedPnl.toFixed(2), sortValue: (r) => r.realizedPnl },
  { key: "activeStopPrice", header: "Active stop", render: (r) => r.activeStopPrice.toFixed(2) },
];

const orderColumns: Column<Order>[] = [
  { key: "productId", header: "Asset", render: (r) => r.productId },
  { key: "orderType", header: "Type", render: (r) => r.orderType },
  { key: "side", header: "Side", render: (r) => r.side },
  { key: "status", header: "Status", render: (r) => r.status },
  { key: "limitOrTriggerPrice", header: "Price", render: (r) => r.limitOrTriggerPrice.toFixed(2), sortValue: (r) => r.limitOrTriggerPrice },
  { key: "createdAt", header: "Created", render: (r) => r.createdAt },
  { key: "filledAt", header: "Filled", render: (r) => r.filledAt ?? "—" },
];

const eventColumns: Column<EngineEvent>[] = [
  { key: "sequence", header: "#", render: (r) => r.sequence, sortValue: (r) => r.sequence },
  { key: "ts", header: "Time", render: (r) => r.ts },
  { key: "level", header: "Level", render: (r) => r.level },
  { key: "productId", header: "Asset", render: (r) => r.productId ?? "—" },
  { key: "eventType", header: "Type", render: (r) => r.eventType },
  { key: "message", header: "Message", render: (r) => r.message },
];

const tradeColumns: Column<TradeRound>[] = [
  { key: "productId", header: "Asset", render: (r) => r.productId },
  { key: "entryTs", header: "Entry time", render: (r) => r.entryTs },
  { key: "exitTs", header: "Exit time", render: (r) => r.exitTs ?? "open" },
  { key: "exitReason", header: "Exit reason", render: (r) => r.exitReason },
  { key: "entryQty", header: "Qty", render: (r) => r.entryQty.toFixed(8), sortValue: (r) => r.entryQty },
  { key: "realizedPnl", header: "Realized P&L", render: (r) => r.realizedPnl.toFixed(2), sortValue: (r) => r.realizedPnl },
  {
    key: "durationSeconds",
    header: "Duration",
    render: (r) => (r.durationSeconds === null ? "—" : `${(r.durationSeconds / 3600).toFixed(1)}h`),
    sortValue: (r) => r.durationSeconds ?? -1,
  },
];

export default function TablesPanel({ positions, orders, events }: Props) {
  const [tab, setTab] = useState<TabKey>("positions");
  const trades = reconstructTrades(events);

  return (
    <section className="panel" aria-labelledby="tables-heading">
      <h2 id="tables-heading">6. Tables</h2>
      <div role="tablist" aria-label="Data tables" className="mode-tabs">
        {TABS.map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "positions" && (
        <DataTable
          caption="Positions"
          columns={positionColumns}
          rows={positions}
          emptyMessage="No positions yet. Start a run to see positions here."
          getRowKey={(r) => r.productId}
        />
      )}
      {tab === "orders" && (
        <DataTable
          caption="Orders"
          columns={orderColumns}
          rows={orders}
          emptyMessage="No orders yet."
          getRowKey={(r) => r.orderId}
        />
      )}
      {tab === "events" && (
        <DataTable
          caption="Events"
          columns={eventColumns}
          rows={events}
          emptyMessage="No events yet."
          getRowKey={(r) => String(r.sequence)}
        />
      )}
      {tab === "trades" && (
        <DataTable
          caption="Trades"
          columns={tradeColumns}
          rows={trades}
          emptyMessage="No completed trades yet."
          getRowKey={(r, i) => `${r.productId}-${r.entryTs}-${i}`}
        />
      )}
    </section>
  );
}
