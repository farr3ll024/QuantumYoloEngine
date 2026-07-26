import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import Footer from "../components/Footer";
import DisclaimerBanner from "../components/DisclaimerBanner";

const NAV_ITEMS: { to: string; label: string }[] = [
  { to: "/", label: "Home" },
  { to: "/simulator", label: "Simulator" },
  { to: "/runs", label: "Runs" },
  { to: "/compare", label: "Compare" },
  { to: "/methodology", label: "Methodology" },
];

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="site-header">
        <div className="site-header__inner">
          <NavLink to="/" className="brand" aria-label="QuantumYoloEngine home">
            <span className="brand__mark" aria-hidden="true">
              ⚡
            </span>
            QuantumYoloEngine
          </NavLink>
          <nav aria-label="Primary">
            {NAV_ITEMS.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.to === "/"}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <DisclaimerBanner compact />
      <main id="main-content" className="site-main">
        {children}
      </main>
      <Footer />
    </div>
  );
}
