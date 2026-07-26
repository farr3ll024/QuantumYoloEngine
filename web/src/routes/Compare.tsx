import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getRun, listRuns, type StoredRun } from "../storage/db";

const SERIES_COLORS = ["var(--color-accent)", "var(--color-accent-2)", "var(--color-warning)", "var(--color-danger)"];

export default function Compare() {
  const [searchParams] = useSearchParams();
  const requestedIds = useMemo(() => (searchParams.get("runs") ?? "").split(",").filter(Boolean), [searchParams]);

  const [allRuns, setAllRuns] = useState<StoredRun[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>(requestedIds);
  const [runs, setRuns] = useState<StoredRun[]>([]);

  useEffect(() => {
    void listRuns().then(setAllRuns);
  }, []);

  useEffect(() => {
    void Promise.all(selectedIds.slice(0, 4).map((id) => getRun(id))).then((results) =>
      setRuns(results.filter((r): r is StoredRun => !!r)),
    );
  }, [selectedIds]);

  const toggle = (runId: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(runId)) return prev.filter((id) => id !== runId);
      if (prev.length >= 4) return prev;
      return [...prev, runId];
    });
  };

  const overlayData = useMemo(() => {
    const byTs = new Map<string, Record<string, number | string>>();
    runs.forEach((stored, idx) => {
      const key = `run${idx}`;
      for (const sample of stored.equitySamples) {
        if (!byTs.has(sample.ts)) byTs.set(sample.ts, { ts: sample.ts });
        byTs.get(sample.ts)![key] = sample.equity;
      }
    });
    return Array.from(byTs.values()).sort((a, b) => String(a.ts).localeCompare(String(b.ts)));
  }, [runs]);

  return (
    <div className="page">
      <h1>Compare runs</h1>
      <p>Select 2–4 saved runs to compare side by side.</p>

      <div className="compare-picker">
        {allRuns.map((r) => (
          <label key={r.run.runId} className="compare-picker__item">
            <input
              type="checkbox"
              checked={selectedIds.includes(r.run.runId)}
              onChange={() => toggle(r.run.runId)}
              disabled={!selectedIds.includes(r.run.runId) && selectedIds.length >= 4}
            />
            {r.run.strategySnapshot.name} <code>{r.run.runId.slice(0, 8)}</code>
          </label>
        ))}
        {allRuns.length === 0 && <p>No saved runs yet.</p>}
      </div>

      {runs.length < 2 ? (
        <p className="empty-state">Select at least two runs above to compare.</p>
      ) : (
        <>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <LineChart data={overlayData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="ts" tickFormatter={(v) => new Date(String(v)).toLocaleDateString()} stroke="var(--color-text-muted)" />
                <YAxis stroke="var(--color-text-muted)" domain={["auto", "auto"]} />
                <Tooltip labelFormatter={(v) => new Date(String(v)).toLocaleString()} />
                <Legend />
                {runs.map((r, idx) => (
                  <Line
                    key={r.run.runId}
                    type="monotone"
                    dataKey={`run${idx}`}
                    name={`${r.run.strategySnapshot.name} (${r.run.runId.slice(0, 6)})`}
                    stroke={SERIES_COLORS[idx % SERIES_COLORS.length]}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="table-scroll">
            <table className="compare-table">
              <caption className="visually-hidden">Run comparison metrics</caption>
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  {runs.map((r) => (
                    <th key={r.run.runId} scope="col">
                      {r.run.strategySnapshot.name}
                      <br />
                      <code>{r.run.runId.slice(0, 8)}</code>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <MetricRow label="Total P&L" runs={runs} get={(r) => (r.run.summary!.totalRealizedPnl + r.run.summary!.totalUnrealizedPnl).toFixed(2)} />
                <MetricRow label="Realized P&L" runs={runs} get={(r) => r.run.summary!.totalRealizedPnl.toFixed(2)} />
                <MetricRow label="Max drawdown" runs={runs} get={(r) => r.run.summary!.maxDrawdown.toFixed(2)} />
                <MetricRow
                  label="Stop rate"
                  runs={runs}
                  get={(r) => `${r.run.summary!.stopCount} / ${r.positions.length || 1} positions`}
                />
                <MetricRow
                  label="TP completion"
                  runs={runs}
                  get={(r) => `TP1 ${r.run.summary!.tp1Count} · TP2 ${r.run.summary!.tp2Count}`}
                />
                <MetricRow label="Entries filled" runs={runs} get={(r) => String(r.run.summary!.entriesFilledCount)} />
                <MetricRow label="Bankroll" runs={runs} get={(r) => `$${r.run.strategySnapshot.bankrollUsd.toLocaleString()}`} />
                <MetricRow label="Strategy hash" runs={runs} get={(r) => r.run.strategyHash.slice(0, 12)} />
                <MetricRow label="Dataset hash" runs={runs} get={(r) => r.run.datasetHash.slice(0, 12)} />
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function MetricRow({
  label,
  runs,
  get,
}: {
  label: string;
  runs: StoredRun[];
  get: (r: StoredRun) => string;
}) {
  return (
    <tr>
      <th scope="row">{label}</th>
      {runs.map((r) => (
        <td key={r.run.runId}>{get(r)}</td>
      ))}
    </tr>
  );
}
