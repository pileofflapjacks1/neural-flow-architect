import { useState } from "react";
import { FlowRing } from "./components/FlowRing";
import { ExplainDrawer } from "./components/ExplainDrawer";
import { OverrideBar } from "./components/OverrideBar";
import { InsightsPanel } from "./components/InsightsPanel";
import { RecipePicker } from "./components/RecipePicker";
import { CoachingPanel } from "./components/CoachingPanel";
import { useNfaSession } from "./hooks/useNfaSession";

function architectLabel(mode: string, paused: boolean, running: boolean): string {
  if (!running) return "Idle — start a session";
  if (paused) return "Paused";
  switch (mode) {
    case "protect":
      return "Protecting focus";
    case "re_enter":
      return "Helping re-entry";
    case "transition":
      return "Supporting transition";
    case "idle_degraded":
      return "Idle (signal degraded)";
    default:
      return "Monitoring";
  }
}

export function App() {
  const {
    state,
    connected,
    error,
    start,
    stop,
    setPaused,
    undo,
    restMode,
    label,
    toolPref,
    setRecipe,
    setPredictive,
  } = useNfaSession();
  const [showWhy, setShowWhy] = useState(false);
  const [tab, setTab] = useState<"live" | "insights" | "coaching">("live");

  const explanationText =
    state.explanation?.text ??
    (state.running
      ? "No proactive action yet — Architect is monitoring."
      : "Start a session to stream estimated flow-related state.");

  const because = (state.explanation?.because as Array<Record<string, unknown>>) ?? [];
  const recipe = state.recipe ?? "study";

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <header className="top-bar">
        <h1>Neural Flow Architect</h1>
        <p className="signal-chip" aria-live="polite">
          {connected ? `Signal ${state.signal}` : "Disconnected"}
          {state.running ? " · live" : ""}
          {" · "}
          {state.adapter}
          {state.quality?.overall != null
            ? ` · q=${Number(state.quality.overall).toFixed(2)}`
            : ""}
        </p>
        <OverrideBar
          paused={state.agent_paused}
          onToggle={() => setPaused(!state.agent_paused)}
        />
      </header>

      {error && (
        <div className="banner warn" role="alert">
          {error}
        </div>
      )}

      {state.learning?.message && (
        <div className="banner info" role="status">
          {state.learning.message}
        </div>
      )}

      <nav className="tabs" aria-label="Primary">
        <button
          type="button"
          className={tab === "live" ? "tab active" : "tab"}
          onClick={() => setTab("live")}
        >
          Live
        </button>
        <button
          type="button"
          className={tab === "insights" ? "tab active" : "tab"}
          onClick={() => setTab("insights")}
        >
          Insights
        </button>
        <button
          type="button"
          className={tab === "coaching" ? "tab active" : "tab"}
          onClick={() => setTab("coaching")}
        >
          Coaching
        </button>
      </nav>

      <main id="main" className="main-panel">
        {tab === "live" && (
          <>
            <div className="session-controls action-row">
              {!state.running ? (
                <>
                  <button
                    type="button"
                    className="target-btn"
                    onClick={() => start("simulator")}
                  >
                    Start simulator
                  </button>
                  <button
                    type="button"
                    className="target-btn secondary"
                    onClick={() => start("replay")}
                  >
                    Start replay
                  </button>
                </>
              ) : (
                <button type="button" className="target-btn secondary" onClick={() => stop()}>
                  Stop session
                </button>
              )}
            </div>

            <RecipePicker value={recipe} onChange={setRecipe} />

            <div className="action-row" style={{ marginBottom: "0.5rem" }}>
              <button
                type="button"
                className={
                  state.predictive_enabled
                    ? "target-btn recipe active"
                    : "target-btn secondary recipe"
                }
                onClick={() => setPredictive(!state.predictive_enabled)}
                aria-pressed={!!state.predictive_enabled}
              >
                Predictive {state.predictive_enabled ? "on" : "off"}
              </button>
            </div>

            {state.precursors && state.precursors.length > 0 && (
              <p className="meta-line" aria-live="polite">
                Precursor:{" "}
                {state.precursors
                  .map((p) => `${String(p.kind)} (${Number(p.confidence).toFixed(2)})`)
                  .join(", ")}
              </p>
            )}

            <FlowRing
              state={state.flow.state}
              engagement={state.flow.engagement}
              minutes={Number(
                state.flow.minutes_in_state?.toFixed?.(1) ?? state.flow.minutes_in_state
              )}
            />

            <section className="status-block" aria-live="polite">
              <h2>
                Architect:{" "}
                {architectLabel(state.mode, state.agent_paused, state.running)}
              </h2>
              <p className="explanation">{explanationText}</p>
              <p className="meta-line">
                conf {state.flow.confidence?.toFixed?.(2) ?? "—"} · mode {state.mode} ·
                recipe {recipe}
                {state.thresholds
                  ? ` · thr ${state.thresholds.protect?.toFixed?.(2)}/${state.thresholds.deep?.toFixed?.(2)}`
                  : ""}
                {state.digital?.focus_enabled ? " · focus on" : ""}
                {state.digital?.notifications_suppressed ? " · notices quiet" : ""}
              </p>
              <div className="action-row">
                <button
                  type="button"
                  className="target-btn"
                  onClick={() => undo()}
                  disabled={!state.can_undo}
                >
                  Undo last
                </button>
                <button
                  type="button"
                  className="target-btn"
                  onClick={() => setShowWhy(true)}
                >
                  Why?
                </button>
                <button type="button" className="target-btn secondary" onClick={() => restMode()}>
                  Rest mode
                </button>
              </div>
              <div className="action-row label-row">
                <button
                  type="button"
                  className="target-btn secondary"
                  onClick={() => label(true)}
                  disabled={!state.running}
                >
                  I felt in flow
                </button>
                <button
                  type="button"
                  className="target-btn secondary"
                  onClick={() => label(false)}
                  disabled={!state.running}
                >
                  Not really
                </button>
              </div>
            </section>
          </>
        )}

        {tab === "insights" && <InsightsPanel session={state.session} />}
        {tab === "coaching" && <CoachingPanel />}
      </main>

      {showWhy && (
        <ExplainDrawer
          text={explanationText}
          because={because}
          toolId={state.explanation?.action}
          onClose={() => setShowWhy(false)}
          onNever={
            state.explanation?.action
              ? () => toolPref(state.explanation!.action, "never")
              : undefined
          }
          onAlways={
            state.explanation?.action
              ? () => toolPref(state.explanation!.action, "always")
              : undefined
          }
        />
      )}

      <footer className="footer">
        <p>
          Local companion UI · Not a medical device · Predictive layer opt-in · No cloud by default
        </p>
      </footer>
    </div>
  );
}
