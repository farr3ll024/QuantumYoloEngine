import { useMemo, useState } from "react";
import DatasetPanel, { type LoadedDataset } from "./simulator/DatasetPanel";
import StrategyPanel from "./simulator/StrategyPanel";
import RunControlsPanel from "./simulator/RunControlsPanel";
import OverviewPanel from "./simulator/OverviewPanel";
import ChartsPanel from "./simulator/ChartsPanel";
import TablesPanel from "./simulator/TablesPanel";
import RunCompletionPanel from "./simulator/RunCompletionPanel";
import { useSimulationWorker } from "./simulator/useSimulationWorker";
import { defaultStrategy, strategyHash as computeStrategyHash } from "../engine/strategy";
import { validateStrategy } from "../engine/validate";
import { buildReportZip } from "../engine/reports";
import { saveRun } from "../storage/db";
import type { Dataset, ProductId, Run } from "../engine/model";
import DisclaimerBanner from "../components/DisclaimerBanner";

async function sha256Hex(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export default function Simulator() {
  const [strategy, setStrategy] = useState(defaultStrategy());
  const [dataset, setDataset] = useState<LoadedDataset | null>(null);
  const [speed, setSpeed] = useState(4);
  const [runId, setRunId] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [exporting, setExporting] = useState(false);

  const sim = useSimulationWorker();

  const strategyErrors = useMemo(() => validateStrategy(strategy), [strategy]);
  const canStart = strategyErrors.length === 0 && !!dataset && dataset.ticks.length > 0;

  const positions = sim.result?.positions ?? sim.progress?.positions ?? [];
  const equity = sim.result?.endingEquity ?? sim.progress?.latestEquity ?? strategy.bankrollUsd;
  const realizedPnl = positions.reduce((s, p) => s + p.realizedPnl, 0);
  const unrealizedPnl = equity - strategy.bankrollUsd - realizedPnl;
  const maxDrawdown = sim.result?.maxDrawdown ?? 0;
  const orders = sim.result?.orders ?? [];
  const events = sim.result?.events ?? [];
  const equitySamples = sim.result?.equitySamples ?? [];

  const entriesFilled = orders.filter((o) => o.orderType === "entry" && o.status === "filled").length;
  const tp1Count = positions.filter((p) => p.tp1Done).length;
  const tp2Count = positions.filter((p) => p.tp2Done).length;
  const stopCount = positions.filter((p) => p.stopDone).length;

  const progressPct = sim.progress ? (sim.progress.cursor / Math.max(1, sim.progress.totalTicks)) * 100 : sim.result ? 100 : 0;
  const progressLabel = sim.progress
    ? `Tick ${sim.progress.cursor.toLocaleString()} / ${sim.progress.totalTicks.toLocaleString()}${sim.progress.currentTs ? ` — ${new Date(sim.progress.currentTs).toLocaleString()}` : ""}`
    : sim.result
      ? "Finished"
      : "Not started";

  const handleStart = () => {
    if (!dataset || !canStart) return;
    const id = crypto.randomUUID();
    setRunId(id);
    setSaved(false);
    sim.start(id, strategy, dataset.ticks, speed);
  };

  const buildRunAndDataset = async (): Promise<{ run: Run; dataset: Dataset } | null> => {
    if (!dataset || !sim.result || !runId) return null;
    const datasetHash = await sha256Hex(JSON.stringify(dataset.ticks));
    const strategyHashHex = await computeStrategyHash(strategy);
    const datasetRecord: Dataset = {
      datasetId: datasetHash.slice(0, 16),
      name: dataset.name,
      source: dataset.source,
      createdAt: new Date().toISOString(),
      startTs: dataset.startTs,
      endTs: dataset.endTs,
      products: dataset.products as ProductId[],
      rowCount: dataset.rowCount,
      sha256: datasetHash,
      schemaVersion: 1,
    };
    const run: Run = {
      runId,
      status: sim.phase === "completed" ? "completed" : "canceled",
      strategySnapshot: strategy,
      strategyHash: strategyHashHex,
      datasetSnapshot: datasetRecord,
      datasetHash,
      engineVersion: "0.2.0",
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      cursor: sim.progress?.cursor ?? 0,
      eventSequence: events.length,
      summary: {
        endingEquity: equity,
        maxDrawdown,
        totalRealizedPnl: realizedPnl,
        totalUnrealizedPnl: unrealizedPnl,
        stopCount,
        tp1Count,
        tp2Count,
        entriesFilledCount: entriesFilled,
        durationTicks: sim.progress?.totalTicks ?? 0,
      },
    };
    return { run, dataset: datasetRecord };
  };

  const handleSaveLocally = async () => {
    const built = await buildRunAndDataset();
    if (!built) return;
    await saveRun({ run: built.run, orders, positions, events, equitySamples });
    setSaved(true);
  };

  const handleExportReport = async () => {
    const built = await buildRunAndDataset();
    if (!built) return;
    setExporting(true);
    try {
      const blob = await buildReportZip({
        run: built.run,
        strategy,
        dataset: built.dataset,
        orders,
        positions,
        events,
        equitySamples,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `quantum-yolo-engine-report-${built.run.runId.slice(0, 8)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="page page--simulator">
      <h1>Simulator</h1>
      <DisclaimerBanner />

      <DatasetPanel dataset={dataset} onDatasetLoaded={setDataset} />
      <StrategyPanel strategy={strategy} onChange={setStrategy} />
      <RunControlsPanel
        phase={sim.phase}
        progressLabel={progressLabel}
        progressPct={progressPct}
        speed={speed}
        canStart={canStart}
        onStart={handleStart}
        onPause={sim.pause}
        onResume={sim.resume}
        onStep={sim.step}
        onCancel={sim.cancel}
        onReset={() => {
          sim.reset();
          setRunId(null);
          setSaved(false);
        }}
        onSpeedChange={(s) => {
          setSpeed(s);
          sim.setSpeed(s);
        }}
      />
      {sim.error && (
        <p role="alert" className="field-error">
          {sim.error}
        </p>
      )}

      <OverviewPanel
        bankrollUsd={strategy.bankrollUsd}
        equity={equity}
        realizedPnl={realizedPnl}
        unrealizedPnl={unrealizedPnl}
        maxDrawdown={maxDrawdown}
        positions={positions}
        entriesFilled={entriesFilled}
        tp1Count={tp1Count}
        tp2Count={tp2Count}
        stopCount={stopCount}
      />
      <ChartsPanel equitySamples={equitySamples} ticks={dataset?.ticks ?? []} products={(dataset?.products ?? []) as ProductId[]} />
      <TablesPanel positions={positions} orders={orders} events={events} />

      {runId && sim.result && (sim.phase === "completed" || sim.phase === "canceled") && (
        <RunCompletionPanel
          runId={runId}
          status={sim.phase}
          saved={saved}
          onSaveLocally={() => void handleSaveLocally()}
          onExportReport={() => void handleExportReport()}
          exporting={exporting}
        />
      )}
    </div>
  );
}
