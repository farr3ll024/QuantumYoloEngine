export default function Privacy() {
  return (
    <div className="page page--prose">
      <h1>Privacy</h1>
      <ul>
        <li>Any CSV you import stays in your browser. It is never uploaded anywhere.</li>
        <li>Saved runs, strategies, and imported dataset metadata live in your browser's local IndexedDB storage.</li>
        <li>Clearing your browser data (or using a different browser/device) removes your local runs and strategies.</li>
        <li>QuantumYoloEngine never asks for exchange API keys or credentials of any kind.</li>
        <li>
          The site is hosted on Netlify, which may keep standard web server access logs (e.g. IP address,
          requested path, timestamp) for operational and abuse-prevention purposes, independent of this
          application.
        </li>
        <li>There are no accounts, no analytics trackers, and no third-party ad scripts in this application.</li>
      </ul>
    </div>
  );
}
