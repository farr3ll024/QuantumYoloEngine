import type { RunPhase } from "./useSimulationWorker";

interface Props {
  phase: RunPhase;
  progressLabel: string;
  progressPct: number;
  speed: number;
  canStart: boolean;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStep: () => void;
  onCancel: () => void;
  onReset: () => void;
  onSpeedChange: (speed: number) => void;
}

export default function RunControlsPanel({
  phase,
  progressLabel,
  progressPct,
  speed,
  canStart,
  onStart,
  onPause,
  onResume,
  onStep,
  onCancel,
  onReset,
  onSpeedChange,
}: Props) {
  return (
    <section className="panel" aria-labelledby="run-controls-heading">
      <h2 id="run-controls-heading">3. Run controls</h2>
      <div className="run-controls">
        <button type="button" className="button button--primary" onClick={onStart} disabled={!canStart || phase === "running"}>
          Start
        </button>
        <button type="button" className="button" onClick={onPause} disabled={phase !== "running"}>
          Pause
        </button>
        <button type="button" className="button" onClick={onResume} disabled={phase !== "paused"}>
          Resume
        </button>
        <button type="button" className="button" onClick={onStep} disabled={phase === "running" || phase === "idle"}>
          Step
        </button>
        <button
          type="button"
          className="button"
          onClick={onCancel}
          disabled={phase !== "running" && phase !== "paused"}
        >
          Cancel
        </button>
        <button type="button" className="button button--ghost" onClick={onReset}>
          Reset
        </button>

        <label className="speed-control">
          Speed
          <input
            type="range"
            min={0.25}
            max={20}
            step={0.25}
            value={speed}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            aria-valuetext={`${speed}x`}
          />
          <span>{speed}x</span>
        </label>
      </div>

      <div className="run-status" role="status" aria-live="polite">
        <span className={`status-pill status-pill--${phase}`}>{phase}</span>
        <span>{progressLabel}</span>
      </div>
      <div className="progress-bar" role="progressbar" aria-valuenow={Math.round(progressPct)} aria-valuemin={0} aria-valuemax={100}>
        <div className="progress-bar__fill" style={{ width: `${progressPct}%` }} />
      </div>
    </section>
  );
}
