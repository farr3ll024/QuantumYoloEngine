import { useCallback, useId, useState } from "react";
import { parseAndValidateCsv, type CsvImportResult, MAX_CSV_BYTES } from "../../data/csv";
import type { Tick } from "../../engine/model";

export interface LoadedDataset {
  name: string;
  source: "bundled" | "upload";
  ticks: Tick[];
  products: string[];
  startTs: string;
  endTs: string;
  rowCount: number;
  warnings: { row?: number; message: string }[];
}

interface Props {
  dataset: LoadedDataset | null;
  onDatasetLoaded: (dataset: LoadedDataset) => void;
}

export default function DatasetPanel({ dataset, onDatasetLoaded }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputId = useId();

  const loadBundledSample = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/datasets/sample-btc-eth.csv");
      if (!res.ok) throw new Error(`failed to fetch sample dataset (${res.status})`);
      const text = await res.text();
      const parsed: CsvImportResult = parseAndValidateCsv(text);
      onDatasetLoaded({ name: "Sample BTC/ETH (bundled)", source: "bundled", ...parsed });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [onDatasetLoaded]);

  const handleFile = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      try {
        if (file.size > MAX_CSV_BYTES) {
          throw new Error(`file too large (${(file.size / 1024 / 1024).toFixed(1)}MB > ${MAX_CSV_BYTES / 1024 / 1024}MB)`);
        }
        const text = await file.text();
        const parsed = parseAndValidateCsv(text);
        onDatasetLoaded({ name: file.name, source: "upload", ...parsed });
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [onDatasetLoaded],
  );

  return (
    <section className="panel" aria-labelledby="dataset-heading">
      <h2 id="dataset-heading">1. Dataset</h2>
      <div className="panel__row">
        <button type="button" className="button" onClick={loadBundledSample} disabled={loading}>
          Use bundled sample
        </button>
        <div className="file-upload">
          <label htmlFor={fileInputId}>Upload CSV (ts,product_id,price)</label>
          <input
            id={fileInputId}
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleFile(file);
            }}
          />
        </div>
      </div>

      {loading && <p role="status">Loading dataset…</p>}
      {error && (
        <p role="alert" className="field-error">
          {error}
        </p>
      )}

      {dataset && (
        <dl className="dataset-summary">
          <div>
            <dt>Name</dt>
            <dd>{dataset.name}</dd>
          </div>
          <div>
            <dt>Products</dt>
            <dd>{dataset.products.join(", ")}</dd>
          </div>
          <div>
            <dt>Rows</dt>
            <dd>{dataset.rowCount.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Range</dt>
            <dd>
              {new Date(dataset.startTs).toLocaleString()} — {new Date(dataset.endTs).toLocaleString()}
            </dd>
          </div>
          {dataset.warnings.length > 0 && (
            <div>
              <dt>Warnings ({dataset.warnings.length})</dt>
              <dd>
                <ul className="warning-list">
                  {dataset.warnings.slice(0, 10).map((w, i) => (
                    <li key={i}>
                      {w.row ? `row ${w.row}: ` : ""}
                      {w.message}
                    </li>
                  ))}
                  {dataset.warnings.length > 10 && <li>…and {dataset.warnings.length - 10} more</li>}
                </ul>
              </dd>
            </div>
          )}
        </dl>
      )}
    </section>
  );
}
