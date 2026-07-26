import type { Position } from "../../engine/model";

interface Props {
  bankrollUsd: number;
  equity: number;
  realizedPnl: number;
  unrealizedPnl: number;
  maxDrawdown: number;
  positions: Position[];
  entriesFilled: number;
  tp1Count: number;
  tp2Count: number;
  stopCount: number;
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "positive" | "negative" }) {
  return (
    <div className="stat-tile">
      <span className="stat-tile__label">{label}</span>
      <span className={`stat-tile__value${tone ? ` stat-tile__value--${tone}` : ""}`}>{value}</span>
    </div>
  );
}

function fmtUsd(n: number): string {
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

export default function OverviewPanel({
  bankrollUsd,
  equity,
  realizedPnl,
  unrealizedPnl,
  maxDrawdown,
  entriesFilled,
  tp1Count,
  tp2Count,
  stopCount,
}: Props) {
  const totalPnl = realizedPnl + unrealizedPnl;
  return (
    <section className="panel" aria-labelledby="overview-heading">
      <h2 id="overview-heading">4. Overview</h2>
      <div className="stat-grid">
        <Stat label="Bankroll" value={fmtUsd(bankrollUsd)} />
        <Stat label="Equity" value={fmtUsd(equity)} />
        <Stat label="Total P&L" value={fmtUsd(totalPnl)} tone={totalPnl >= 0 ? "positive" : "negative"} />
        <Stat label="Realized P&L" value={fmtUsd(realizedPnl)} tone={realizedPnl >= 0 ? "positive" : "negative"} />
        <Stat label="Unrealized P&L" value={fmtUsd(unrealizedPnl)} tone={unrealizedPnl >= 0 ? "positive" : "negative"} />
        <Stat label="Max drawdown" value={fmtUsd(maxDrawdown)} tone="negative" />
        <Stat label="Entries filled" value={String(entriesFilled)} />
        <Stat label="TP1 / TP2 hits" value={`${tp1Count} / ${tp2Count}`} />
        <Stat label="Stops hit" value={String(stopCount)} />
      </div>
    </section>
  );
}
