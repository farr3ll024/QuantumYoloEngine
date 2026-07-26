export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <p>
          QuantumYoloEngine is an experimental educational project by{" "}
          <a href="https://reintslabs.com" target="_blank" rel="noopener noreferrer">
            Reints Labs LLC
          </a>
          .
        </p>
        <nav aria-label="Footer">
          <a href="https://reintslabs.com" target="_blank" rel="noopener noreferrer">
            Reints Labs
          </a>
          <a href="/methodology">Methodology</a>
          <a href="/privacy">Privacy</a>
        </nav>
      </div>
    </footer>
  );
}
