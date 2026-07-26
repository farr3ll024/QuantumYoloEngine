import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import AppShell from "./app/AppShell";
import Home from "./routes/Home";

const Simulator = lazy(() => import("./routes/Simulator"));
const Runs = lazy(() => import("./routes/Runs"));
const Compare = lazy(() => import("./routes/Compare"));
const Methodology = lazy(() => import("./routes/Methodology"));
const Privacy = lazy(() => import("./routes/Privacy"));
const NotFound = lazy(() => import("./routes/NotFound"));

function RouteFallback() {
  return (
    <div className="route-fallback" role="status" aria-live="polite">
      Loading…
    </div>
  );
}

export default function App() {
  return (
    <AppShell>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </AppShell>
  );
}
