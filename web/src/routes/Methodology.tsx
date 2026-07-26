export default function Methodology() {
  return (
    <div className="page page--prose">
      <h1>Methodology</h1>

      <h2>Fill assumptions</h2>
      <ul>
        <li>Buy-limit entries fill when market price is at or below the limit, at <code>min(market, limit)</code>.</li>
        <li>The sell stop fills when market price is at or below the stop, at <code>min(market, stop)</code>.</li>
        <li>
          Take-profit levels fill when market price is at or above the trigger, at{" "}
          <code>max(market, trigger)</code>.
        </li>
        <li>A stop can never fill on the exact same tick as a fresh entry fill on that position.</li>
        <li>TP1 sells its configured fraction of the position; TP2 sells whatever remains.</li>
        <li>The stop can optionally move to breakeven (average entry) once TP1 fills.</li>
      </ul>

      <h2>What is not modeled</h2>
      <ul>
        <li><strong>No slippage or spread.</strong> Fills use the exact simulated tick price.</li>
        <li><strong>No fees.</strong> Realized P&amp;L does not deduct trading fees.</li>
        <li><strong>No order-book depth or liquidity constraints.</strong> Any order size fills fully at its trigger price.</li>
        <li><strong>No live execution.</strong> This software never connects to an exchange or places a real order.</li>
      </ul>

      <h2>How P&amp;L, equity, and drawdown are calculated</h2>
      <p>
        Equity is reconstructed <strong>event-by-event</strong> from the run's ordered event ledger, not
        projected backward from the final position. At every price tick:
      </p>
      <p>
        <code>equity = bankroll + Σ(realized P&amp;L so far) + Σ(unrealized P&amp;L on open positions, marked
        to the latest tick price)</code>
      </p>
      <p>
        Drawdown at a given tick is <code>equity − running peak equity so far</code>; max drawdown is the most
        negative drawdown observed across the run. All values are rounded to 8 decimal places, matching the
        precision used internally for base-asset quantities.
      </p>

      <h2>Why simulated performance differs from live trading</h2>
      <p>
        Real markets have slippage, partial fills, fees, latency, and liquidity limits that this simulator
        does not model. A strategy that performs well here is not a prediction of how it would perform with
        real capital on a real exchange. Treat every result as a learning exercise, not a forecast.
      </p>
    </div>
  );
}
