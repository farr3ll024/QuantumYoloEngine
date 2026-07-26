import { useId, useMemo, useState } from "react";
import type { AssetStrategy, EntryRule, Strategy } from "../../engine/model";
import { defaultStrategy, strategyFromYaml, strategyToYaml, StrategyImportError } from "../../engine/strategy";
import { validateStrategy, type FieldError } from "../../engine/validate";

interface Props {
  strategy: Strategy;
  onChange: (strategy: Strategy) => void;
}

function fieldErrorsFor(errors: FieldError[], prefix: string): string[] {
  return errors.filter((e) => e.path === prefix).map((e) => e.message);
}

export default function StrategyPanel({ strategy, onChange }: Props) {
  const [mode, setMode] = useState<"form" | "yaml">("form");
  const [yamlText, setYamlText] = useState(() => strategyToYaml(strategy));
  const [yamlError, setYamlError] = useState<string | null>(null);
  const bankrollId = useId();

  const errors = useMemo(() => validateStrategy(strategy), [strategy]);

  const update = (patch: Partial<Strategy>) => onChange({ ...strategy, ...patch, updatedAt: new Date().toISOString() });

  const updateAsset = (index: number, patch: Partial<AssetStrategy>) => {
    const assets = strategy.assets.slice();
    assets[index] = { ...assets[index], ...patch };
    update({ assets });
  };

  const updateEntry = (assetIndex: number, entryIndex: number, patch: Partial<EntryRule>) => {
    const asset = strategy.assets[assetIndex];
    const entries = asset.entries.slice();
    entries[entryIndex] = { ...entries[entryIndex], ...patch };
    updateAsset(assetIndex, { entries });
  };

  const addEntry = (assetIndex: number) => {
    const asset = strategy.assets[assetIndex];
    const nextNum = asset.entries.length + 1;
    const entries = [...asset.entries, { id: `${asset.productId.split("-")[0].toLowerCase()}_e${nextNum}`, price: 0, quoteSizeUsd: 0 }];
    updateAsset(assetIndex, { entries });
  };

  const removeEntry = (assetIndex: number, entryIndex: number) => {
    const asset = strategy.assets[assetIndex];
    updateAsset(assetIndex, { entries: asset.entries.filter((_, i) => i !== entryIndex) });
  };

  const applyYaml = () => {
    try {
      const parsed = strategyFromYaml(yamlText, strategy);
      onChange(parsed);
      setYamlError(null);
    } catch (err) {
      setYamlError(err instanceof StrategyImportError ? err.message : (err as Error).message);
    }
  };

  const switchToYaml = () => {
    setYamlText(strategyToYaml(strategy));
    setMode("yaml");
  };

  const totalAllocation = strategy.assets.reduce((sum, a) => (a.enabled ? sum + a.allocationUsd : sum), 0);

  return (
    <section className="panel" aria-labelledby="strategy-heading">
      <div className="panel__header">
        <h2 id="strategy-heading">2. Strategy</h2>
        <div className="panel__actions">
          <div role="tablist" aria-label="Strategy editor mode" className="mode-tabs">
            <button type="button" role="tab" aria-selected={mode === "form"} onClick={() => setMode("form")}>
              Form
            </button>
            <button type="button" role="tab" aria-selected={mode === "yaml"} onClick={switchToYaml}>
              YAML
            </button>
          </div>
          <button type="button" className="button button--ghost" onClick={() => onChange(defaultStrategy())}>
            Reset to default
          </button>
        </div>
      </div>

      {errors.length > 0 && (
        <div role="alert" className="validation-summary">
          <strong>
            {errors.length} validation {errors.length === 1 ? "issue" : "issues"}
          </strong>
          <ul>
            {errors.slice(0, 8).map((e, i) => (
              <li key={i}>
                {e.path}: {e.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {mode === "yaml" ? (
        <div className="yaml-editor">
          <label htmlFor="strategy-yaml">Strategy YAML</label>
          <textarea
            id="strategy-yaml"
            value={yamlText}
            onChange={(e) => setYamlText(e.target.value)}
            rows={20}
            spellCheck={false}
            aria-describedby={yamlError ? "yaml-error" : undefined}
          />
          {yamlError && (
            <p id="yaml-error" role="alert" className="field-error">
              {yamlError}
            </p>
          )}
          <button type="button" className="button button--primary" onClick={applyYaml}>
            Apply YAML
          </button>
        </div>
      ) : (
        <div className="strategy-form">
          <div className="field-row">
            <label htmlFor={bankrollId}>Bankroll (USD)</label>
            <input
              id={bankrollId}
              type="number"
              min={0}
              value={strategy.bankrollUsd}
              onChange={(e) => update({ bankrollUsd: Number(e.target.value) })}
              aria-describedby="bankroll-errors"
            />
          </div>
          <div id="bankroll-errors">
            {fieldErrorsFor(errors, "bankrollUsd").map((m, i) => (
              <p key={i} role="alert" className="field-error">
                {m}
              </p>
            ))}
          </div>

          <div className="allocation-bar" aria-hidden="true">
            <div
              className="allocation-bar__fill"
              style={{ width: `${Math.min(100, (totalAllocation / Math.max(1, strategy.bankrollUsd)) * 100)}%` }}
            />
          </div>
          <p className="allocation-caption">
            ${totalAllocation.toLocaleString()} of ${strategy.bankrollUsd.toLocaleString()} bankroll allocated
          </p>

          {strategy.assets.map((asset, assetIndex) => (
            <fieldset key={asset.productId} className="asset-fieldset">
              <legend>
                <label>
                  <input
                    type="checkbox"
                    checked={asset.enabled}
                    onChange={(e) => updateAsset(assetIndex, { enabled: e.target.checked })}
                  />{" "}
                  {asset.productId}
                </label>
              </legend>

              <div className="field-row">
                <label htmlFor={`${asset.productId}-alloc`}>Allocation (USD)</label>
                <input
                  id={`${asset.productId}-alloc`}
                  type="number"
                  min={0}
                  value={asset.allocationUsd}
                  onChange={(e) => updateAsset(assetIndex, { allocationUsd: Number(e.target.value) })}
                />
              </div>
              <div className="field-row">
                <label htmlFor={`${asset.productId}-stop`}>Stop price</label>
                <input
                  id={`${asset.productId}-stop`}
                  type="number"
                  min={0}
                  value={asset.stopPrice}
                  onChange={(e) => updateAsset(assetIndex, { stopPrice: Number(e.target.value) })}
                />
              </div>
              <div className="field-row field-row--pair">
                <div>
                  <label htmlFor={`${asset.productId}-tp1`}>TP1 price</label>
                  <input
                    id={`${asset.productId}-tp1`}
                    type="number"
                    min={0}
                    value={asset.takeProfit.tp1Price}
                    onChange={(e) =>
                      updateAsset(assetIndex, { takeProfit: { ...asset.takeProfit, tp1Price: Number(e.target.value) } })
                    }
                  />
                </div>
                <div>
                  <label htmlFor={`${asset.productId}-tp1frac`}>TP1 fraction</label>
                  <input
                    id={`${asset.productId}-tp1frac`}
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={asset.takeProfit.tp1Fraction}
                    onChange={(e) =>
                      updateAsset(assetIndex, { takeProfit: { ...asset.takeProfit, tp1Fraction: Number(e.target.value) } })
                    }
                  />
                </div>
              </div>
              <div className="field-row field-row--pair">
                <div>
                  <label htmlFor={`${asset.productId}-tp2`}>TP2 price</label>
                  <input
                    id={`${asset.productId}-tp2`}
                    type="number"
                    min={0}
                    value={asset.takeProfit.tp2Price}
                    onChange={(e) =>
                      updateAsset(assetIndex, { takeProfit: { ...asset.takeProfit, tp2Price: Number(e.target.value) } })
                    }
                  />
                </div>
                <div>
                  <label htmlFor={`${asset.productId}-tp2frac`}>TP2 fraction</label>
                  <input
                    id={`${asset.productId}-tp2frac`}
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={asset.takeProfit.tp2Fraction}
                    onChange={(e) =>
                      updateAsset(assetIndex, { takeProfit: { ...asset.takeProfit, tp2Fraction: Number(e.target.value) } })
                    }
                  />
                </div>
              </div>

              <table className="entries-table">
                <caption>Entry ladder</caption>
                <thead>
                  <tr>
                    <th scope="col">ID</th>
                    <th scope="col">Price</th>
                    <th scope="col">Size (USD)</th>
                    <th scope="col">
                      <span className="visually-hidden">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {asset.entries.map((entry, entryIndex) => (
                    <tr key={entryIndex}>
                      <td>
                        <input
                          aria-label={`Entry ${entryIndex + 1} id`}
                          type="text"
                          value={entry.id}
                          onChange={(e) => updateEntry(assetIndex, entryIndex, { id: e.target.value })}
                        />
                      </td>
                      <td>
                        <input
                          aria-label={`Entry ${entryIndex + 1} price`}
                          type="number"
                          min={0}
                          value={entry.price}
                          onChange={(e) => updateEntry(assetIndex, entryIndex, { price: Number(e.target.value) })}
                        />
                      </td>
                      <td>
                        <input
                          aria-label={`Entry ${entryIndex + 1} size in USD`}
                          type="number"
                          min={0}
                          value={entry.quoteSizeUsd}
                          onChange={(e) => updateEntry(assetIndex, entryIndex, { quoteSizeUsd: Number(e.target.value) })}
                        />
                      </td>
                      <td>
                        <button
                          type="button"
                          className="button button--ghost button--small"
                          onClick={() => removeEntry(assetIndex, entryIndex)}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button type="button" className="button button--small" onClick={() => addEntry(assetIndex)}>
                Add entry
              </button>
            </fieldset>
          ))}
        </div>
      )}
    </section>
  );
}
