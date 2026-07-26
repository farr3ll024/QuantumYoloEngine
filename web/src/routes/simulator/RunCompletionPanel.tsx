import { Link } from "react-router-dom";

interface Props {
  runId: string;
  status: "completed" | "canceled";
  saved: boolean;
  onSaveLocally: () => void;
  onExportReport: () => void;
  exporting: boolean;
}

export default function RunCompletionPanel({ runId, status, saved, onSaveLocally, onExportReport, exporting }: Props) {
  return (
    <section className="panel panel--highlight" aria-labelledby="completion-heading">
      <h2 id="completion-heading">7. Run {status}</h2>
      <p>
        Run <code>{runId}</code> {status === "completed" ? "finished replaying the full dataset." : "was canceled before completion."}
      </p>
      <div className="panel__row">
        <button type="button" className="button button--primary" onClick={onSaveLocally} disabled={saved}>
          {saved ? "Saved locally" : "Save run locally"}
        </button>
        <button type="button" className="button" onClick={onExportReport} disabled={exporting}>
          {exporting ? "Building report…" : "Export report (.zip)"}
        </button>
        <Link className="button button--ghost" to="/runs">
          View saved runs
        </Link>
        <Link className="button button--ghost" to="/simulator">
          Compare another strategy
        </Link>
      </div>
    </section>
  );
}
