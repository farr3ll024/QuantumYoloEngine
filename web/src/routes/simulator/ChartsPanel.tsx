import { useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EquitySample, ProductId, Tick } from "../../engine/model";

interface Props {
  equitySamples: EquitySample[];
  ticks: Tick[];
  products: ProductId[];
}

function fmtTs(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString();
}

export default function ChartsPanel({ equitySamples, ticks, products }: Props) {
  const [selectedProductOverride, setSelectedProductOverride] = useState<ProductId | undefined>(undefined);
  const [showEquityTable, setShowEquityTable] = useState(false);
  const [showPriceTable, setShowPriceTable] = useState(false);

  // products arrives asynchronously (after a dataset is loaded), so the
  // selection can't be captured once via useState(products[0]) -- fall back
  // to the first available product whenever there's no explicit user pick.
  const selectedProduct = selectedProductOverride && products.includes(selectedProductOverride)
    ? selectedProductOverride
    : products[0];

  const priceSeries = useMemo(
    () => ticks.filter((t) => t.productId === selectedProduct).map((t) => ({ ts: t.ts, price: t.price })),
    [ticks, selectedProduct],
  );

  const equityChartData = useMemo(() => equitySamples.map((s) => ({ ts: s.ts, equity: s.equity, drawdown: s.drawdown })), [equitySamples]);

  return (
    <section className="panel" aria-labelledby="charts-heading">
      <h2 id="charts-heading">5. Charts</h2>

      <div className="chart-block">
        <h3>Equity curve</h3>
        {equityChartData.length ? (
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <AreaChart data={equityChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="ts" tickFormatter={fmtTs} minTickGap={60} stroke="var(--color-text-muted)" />
                <YAxis stroke="var(--color-text-muted)" domain={["auto", "auto"]} />
                <Tooltip labelFormatter={(v) => fmtTs(String(v))} formatter={(v) => Number(v).toFixed(2)} />
                <Area type="monotone" dataKey="equity" stroke="var(--color-accent)" fill="var(--color-accent-fill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p>No equity data yet. Start a run to see the curve.</p>
        )}
        <button type="button" className="button button--small" onClick={() => setShowEquityTable((v) => !v)}>
          {showEquityTable ? "Hide" : "Show"} equity data table
        </button>
        {showEquityTable && (
          <div className="table-scroll">
            <table>
              <caption className="visually-hidden">Equity curve data</caption>
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Equity</th>
                  <th scope="col">Drawdown</th>
                </tr>
              </thead>
              <tbody>
                {equityChartData.map((row, i) => (
                  <tr key={i}>
                    <td>{fmtTs(row.ts)}</td>
                    <td>{row.equity.toFixed(2)}</td>
                    <td>{row.drawdown.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="chart-block">
        <div className="chart-block__header">
          <h3>Price</h3>
          {products.length > 1 && (
            <label>
              Asset
              <select value={selectedProduct} onChange={(e) => setSelectedProductOverride(e.target.value as ProductId)}>
                {products.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        {priceSeries.length ? (
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={priceSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="ts" tickFormatter={fmtTs} minTickGap={60} stroke="var(--color-text-muted)" />
                <YAxis stroke="var(--color-text-muted)" domain={["auto", "auto"]} />
                <Tooltip labelFormatter={(v) => fmtTs(String(v))} formatter={(v) => Number(v).toFixed(2)} />
                <Line type="monotone" dataKey="price" stroke="var(--color-accent-2)" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p>No price data loaded yet.</p>
        )}
        <button type="button" className="button button--small" onClick={() => setShowPriceTable((v) => !v)}>
          {showPriceTable ? "Hide" : "Show"} price data table
        </button>
        {showPriceTable && (
          <div className="table-scroll">
            <table>
              <caption className="visually-hidden">Price series for {selectedProduct}</caption>
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Price</th>
                </tr>
              </thead>
              <tbody>
                {priceSeries.slice(0, 500).map((row, i) => (
                  <tr key={i}>
                    <td>{fmtTs(row.ts)}</td>
                    <td>{row.price.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {priceSeries.length > 500 && <p>Showing first 500 of {priceSeries.length} rows.</p>}
          </div>
        )}
      </div>
    </section>
  );
}
