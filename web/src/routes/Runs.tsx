import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteRun, listRuns, type StoredRun } from "../storage/db";
import { buildReportZip } from "../engine/reports";

export default function Runs() {
  const [runs, setRuns] = useState<StoredRun[]>([]);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    setRuns(await listRuns());
    setLoading(false);
  };

  useEffect(() => {
    // fetch-on-mount from IndexedDB; setLoading/setRuns land after the async
    // gap in refresh(), not synchronously within the effect body.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, []);

  const handleDelete = async (runId: string) => {
    if (!confirm(`Delete run ${runId}? This cannot be undone.`)) return;
    await deleteRun(runId);
    await refresh();
  };

  const handleExport = async (stored: StoredRun) => {
    const blob = await buildReportZip({
      run: stored.run,
      strategy: stored.run.strategySnapshot,
      dataset: stored.run.datasetSnapshot,
      orders: stored.orders,
      positions: stored.positions,
      events: stored.events,
      equitySamples: stored.equitySamples,
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `quantum-yolo-engine-report-${stored.run.runId.slice(0, 8)}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const toggleSelected = (runId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else if (next.size < 4) next.add(runId);
      return next;
    });
  };

  const filtered = runs.filter((r) => {
    const needle = filter.toLowerCase();
    return (
      !needle ||
      r.run.runId.toLowerCase().includes(needle) ||
      r.run.strategySnapshot.name.toLowerCase().includes(needle) ||
      r.run.strategyHash.toLowerCase().includes(needle)
    );
  });

  return (
    <div className="page">
      <h1>Saved runs</h1>
      <div className="panel__row">
        <label>
          Search
          <input type="search" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Run id, strategy name, or hash…" />
        </label>
        {selected.size >= 2 && (
          <Link className="button button--primary" to={`/compare?runs=${Array.from(selected).join(",")}`}>
            Compare {selected.size} runs
          </Link>
        )}
      </div>

      {loading && <p role="status">Loading runs…</p>}
      {!loading && filtered.length === 0 && (
        <p className="empty-state">
          No saved runs yet. <Link to="/simulator">Start a simulation</Link> and save it locally to see it here.
        </p>
      )}

      <ul className="run-list">
        {filtered.map((stored) => (
          <li key={stored.run.runId} className="run-card">
            <label className="run-card__select">
              <input
                type="checkbox"
                checked={selected.has(stored.run.runId)}
                onChange={() => toggleSelected(stored.run.runId)}
                aria-label={`Select run ${stored.run.runId} for comparison`}
              />
            </label>
            <div className="run-card__body">
              <h2>{stored.run.strategySnapshot.name}</h2>
              <p className="run-card__meta">
                <code>{stored.run.runId.slice(0, 8)}</code> · strategy <code>{stored.run.strategyHash.slice(0, 8)}</code> ·
                dataset <code>{stored.run.datasetHash.slice(0, 8)}</code> · {stored.run.status}
              </p>
              {stored.run.summary && (
                <p className="run-card__stats">
                  Equity ${stored.run.summary.endingEquity.toFixed(2)} · Total P&L $
                  {(stored.run.summary.totalRealizedPnl + stored.run.summary.totalUnrealizedPnl).toFixed(2)} · Max DD $
                  {stored.run.summary.maxDrawdown.toFixed(2)}
                </p>
              )}
            </div>
            <div className="run-card__actions">
              <button type="button" className="button button--small" onClick={() => void handleExport(stored)}>
                Export
              </button>
              <button type="button" className="button button--ghost button--small" onClick={() => void handleDelete(stored.run.runId)}>
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
