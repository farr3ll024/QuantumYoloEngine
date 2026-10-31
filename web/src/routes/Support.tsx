import { Link } from "react-router-dom";
import { MAX_CSV_BYTES } from "../data/csv";
import { PRODUCT_IDS } from "../engine/model";

const SUPPORT_EMAIL = "sales@reintslabs.com";
const SUPPORT_MAILTO = `mailto:${SUPPORT_EMAIL}?subject=QuantumYoloEngine%20support`;
const MAX_CSV_MB = MAX_CSV_BYTES / 1024 / 1024;

export default function Support() {
  return (
    <div className="page page--prose page--support">
      <h1>Support</h1>
      <p>Questions or problems with QuantumYoloEngine? Email Reints Labs LLC at the address below.</p>

      <section aria-labelledby="support-contact">
        <h2 id="support-contact">Contact</h2>
        <p>
          Email <a href={SUPPORT_MAILTO}>{SUPPORT_EMAIL}</a> with &ldquo;QuantumYoloEngine support&rdquo; in the
          subject. It helps to include:
        </p>
        <ul>
          <li>The page you were on and what you were doing.</li>
          <li>Whether you used the bundled sample or your own CSV, and any error message shown.</li>
          <li>For a CSV problem, the first few lines of the file.</li>
          <li>For a question about results, your strategy from the Simulator&rsquo;s YAML tab.</li>
          <li>Your browser and device, and a screenshot if you can.</li>
        </ul>
        <p>Never send exchange API keys or passwords. QuantumYoloEngine never asks for them.</p>
      </section>

      <section aria-labelledby="support-faq">
        <h2 id="support-faq">Common questions</h2>

        <div className="faq-item">
          <h3>Where are my runs and strategies saved?</h3>
          <p>
            A run is saved only when you choose &ldquo;Save run locally&rdquo; after it finishes or is canceled.
            Saved runs, with the strategy they used, live in this browser&rsquo;s IndexedDB storage and appear on{" "}
            <Link to="/runs">Runs</Link>. Nothing is uploaded and there are no accounts, so runs don&rsquo;t follow
            you to another browser or device. The strategy you are editing and the dataset you loaded stay on the
            Simulator page only: reloading or leaving it starts over. To keep a strategy, copy it from the YAML
            tab, or export a run&rsquo;s report as a .zip.
          </p>
        </div>

        <div className="faq-item">
          <h3>How do I delete runs or start fresh?</h3>
          <p>
            Delete a saved run with its Delete button on <Link to="/runs">Runs</Link>. In the Simulator,
            &ldquo;Reset to default&rdquo; restores the default strategy and Reset clears the current run. To
            remove everything, clear this site&rsquo;s data in your browser settings.
          </p>
        </div>

        <div className="faq-item">
          <h3>What CSV files can I import?</h3>
          <p>
            A CSV of up to {MAX_CSV_MB} MB with a header row containing <code>ts</code>, <code>product_id</code>{" "}
            and <code>price</code> (other columns are ignored), for example{" "}
            <code>2024-01-01T00:00:00Z,BTC-USD,42000.5</code>.
          </p>
          <ul>
            <li>
              <code>product_id</code> must be {PRODUCT_IDS.join(" or ")}, and <code>price</code> a positive number;
              otherwise the file is rejected and the first problem rows are listed.
            </li>
            <li>
              <code>ts</code> is an ISO 8601 date or date-time. Times without an offset are read as UTC.
            </li>
            <li>
              Rows with an invalid timestamp, missing columns, or a repeated timestamp and product are skipped, and
              out-of-order rows are sorted. Each is listed as a warning.
            </li>
          </ul>
        </div>

        <div className="faq-item">
          <h3>Are the results what I would have made trading?</h3>
          <p>
            No. Every result is simulated against price data, with no fees, slippage, spread or liquidity limits.
            The <Link to="/methodology">methodology</Link> lists exactly how fills are modeled and what is left
            out.
          </p>
        </div>

        <div className="faq-item">
          <h3>Which browsers work?</h3>
          <p>
            The simulation runs in your browser in a Web Worker, and saved runs use IndexedDB, so you need a
            current browser with JavaScript on. Automated tests run in Chromium at desktop and phone sizes. A
            private window forgets saved runs when it closes, and clearing site data removes them.
          </p>
        </div>
      </section>

      <section aria-labelledby="support-notes">
        <h2 id="support-notes">Good to know</h2>
        <p>
          QuantumYoloEngine is paper trading only. It never connects to an exchange or places a real order, and it
          is not financial advice. See <Link to="/privacy">Privacy</Link> for what stays in your browser.
        </p>
      </section>
    </div>
  );
}
