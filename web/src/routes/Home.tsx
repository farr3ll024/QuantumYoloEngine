import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="page page--home">
      <section className="hero">
        <h1>Test a trading idea without risking a dollar.</h1>
        <p className="hero__lede">
          QuantumYoloEngine is a browser-based lab for building BTC and ETH entry ladders, stop-loss and
          two-stage take-profit rules, then replaying them against deterministic demo data or your own
          historical CSV — entirely client-side.
        </p>
        <div className="hero__actions">
          <Link className="button button--primary" to="/simulator">
            Open simulator
          </Link>
          <Link className="button button--ghost" to="/methodology">
            How it works
          </Link>
        </div>
        <p className="hero__status">
          <span className="badge badge--experimental">Experimental</span> Paper trading only. No exchange
          connection, ever.
        </p>
      </section>

      <section className="feature-grid" aria-label="What you can do">
        <article>
          <h2>Build a strategy</h2>
          <p>Allocate a simulated bankroll across BTC and ETH, ladder in entries, and set stop/take-profit rules.</p>
        </article>
        <article>
          <h2>Replay history</h2>
          <p>Run against a bundled demo dataset or upload your own timestamped price CSV.</p>
        </article>
        <article>
          <h2>Inspect everything</h2>
          <p>Positions, orders, fills, events, equity, and drawdown update live as the run replays.</p>
        </article>
        <article>
          <h2>Compare runs</h2>
          <p>Save runs locally and compare strategies side by side across P&amp;L, drawdown, and exposure.</p>
        </article>
      </section>
    </div>
  );
}
