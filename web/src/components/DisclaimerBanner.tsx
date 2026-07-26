import { DISCLAIMER } from "../engine/model";

export default function DisclaimerBanner({ compact = false }: { compact?: boolean }) {
  return (
    <div className="disclaimer-banner" role="note" aria-label="Disclaimer">
      <strong>{compact ? "Paper trading only." : "Educational paper trading simulator."}</strong>{" "}
      <span>{DISCLAIMER}</span>
    </div>
  );
}
