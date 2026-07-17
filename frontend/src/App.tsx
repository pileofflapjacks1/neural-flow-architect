import { useMemo, useState } from "react";
import { FlowRing } from "./components/FlowRing";
import { ExplainDrawer } from "./components/ExplainDrawer";
import { OverrideBar } from "./components/OverrideBar";

/** Scaffold UI with mock state until local WebSocket API is wired (Phase 1). */
export function App() {
  const [paused, setPaused] = useState(false);
  const [showWhy, setShowWhy] = useState(false);

  const mock = useMemo(
    () => ({
      state: "flow",
      engagement: 0.78,
      minutes: 12,
      explanation:
        "I suppressed non-critical notifications because your engagement signature is high and you have been in flow for 12 minutes.",
      architectStatus: paused ? "Paused" : "Protecting",
      signal: "good" as const,
    }),
    [paused]
  );

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <header className="top-bar">
        <h1>Neural Flow Architect</h1>
        <p className="signal-chip" aria-live="polite">
          Signal {mock.signal}
        </p>
        <OverrideBar paused={paused} onToggle={() => setPaused((p) => !p)} />
      </header>

      <main id="main" className="main-panel">
        <FlowRing
          state={mock.state}
          engagement={mock.engagement}
          minutes={mock.minutes}
        />
        <section className="status-block" aria-live="polite">
          <h2>Architect: {mock.architectStatus}</h2>
          <p className="explanation">{mock.explanation}</p>
          <div className="action-row">
            <button type="button" className="target-btn">
              Undo last
            </button>
            <button
              type="button"
              className="target-btn"
              onClick={() => setShowWhy(true)}
            >
              Why?
            </button>
            <button type="button" className="target-btn secondary">
              Rest mode
            </button>
          </div>
        </section>
      </main>

      {showWhy && (
        <ExplainDrawer
          text={mock.explanation}
          onClose={() => setShowWhy(false)}
        />
      )}

      <footer className="footer">
        <p>
          Local companion UI scaffold · Not a medical device ·{" "}
          <span className="dim">WebSocket wiring in Phase 1</span>
        </p>
      </footer>
    </div>
  );
}
