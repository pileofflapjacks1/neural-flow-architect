import { useState } from "react";
import { FlowRing } from "./components/FlowRing";
import { ExplainDrawer } from "./components/ExplainDrawer";
import { OverrideBar } from "./components/OverrideBar";
import { InsightsPanel } from "./components/InsightsPanel";
import { RecipePicker } from "./components/RecipePicker";
import { CoachingPanel } from "./components/CoachingPanel";
import { Onboarding } from "./components/Onboarding";
import { PresetPicker } from "./components/PresetPicker";
import { useNfaSession } from "./hooks/useNfaSession";

function architectLabel(mode: string, paused: boolean, running: boolean): string {
  if (!running) return "Ready — start when you want";
  if (paused) return "Paused — you are in control";
  switch (mode) {
    case "protect":
      return "Protecting your focus";
    case "re_enter":
      return "Helping you re-enter";
    case "transition":
      return "Easing transition";
    case "idle_degraded":
      return "Waiting (signal weak)";
    default:
      return "Monitoring quietly";
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
    setSimpleMode,
    refresh,
  } = useNfaSession();
  const [showWhy, setShowWhy] = useState(false);
  const [tab, setTab] = useState<"live" | "insights" | "coaching">("live");
  const [onboardingDone, setOnboardingDone] = useState(false);

  const simple = state.simple_mode !== false;
  const explanationText =
    state.explanation?.text ??
    (state.running
      ? "No change yet — Architect is watching quietly."
      : "Start a session when ready. Pause and Undo always work.");

  const because = (state.explanation?.because as Array<Record<string, unknown>>) ?? [];
  const recipe = state.recipe ?? "study";
  const showOnboarding = !onboardingDone && state.onboarding_completed === false;

  return (
    <div className={`app-shell ${simple ? "simple" : ""}`}>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>

      <header className="top-bar">
        <div>
          <h1>Neural Flow Architect</h1>
          <p className="signal-chip" aria-live="polite">
            {connected ? `Signal ${state.signal}` : "Connecting…"}
            {state.running ? " · live" : " · idle"}
            {simple ? " · simple mode" : " · full mode"}
          </p>
        </div>
        <OverrideBar
          paused={state.agent_paused}
          onToggle={() => setPaused(!state.agent_paused)}
        />
      </header>

      {/* Always-visible emergency controls */}
      <div className="sticky-controls" role="toolbar" aria-label="Primary controls">
        <button
          type="button"
          className="target-btn override"
          onClick={() => setPaused(!state.agent_paused)}
          aria-pressed={state.agent_paused}
        >
          {state.agent_paused ? "Resume" : "Pause"}
        </button>
        <button
          type="button"
          className="target-btn"
          onClick={() => undo()}
          disabled={!state.can_undo}
        >
          Undo
        </button>
        <button type="button" className="target-btn secondary" onClick={() => restMode()}>
          Rest
        </button>
      </div>

      {error && (
        <div className="banner warn" role="alert">
          {error}
          <p className="meta-line">Tip: run <code>nfa start</code> in a terminal.</p>
        </div>
      )}

      {state.learning?.message && (
        <div className="banner info" role="status">
          {state.learning.message}
        </div>
      )}

      {state.last_intent?.type && (
        <div className="banner info" role="status">
          Intent: {String(state.last_intent.type)}
          {state.last_intent.result
            ? ` — ${String((state.last_intent.result as { message?: string }).message ?? "")}`
            : ""}
        </div>
      )}

      {showOnboarding ? (
        <main id="main" className="main-panel">
          <Onboarding
            onDone={() => {
              setOnboardingDone(true);
              refresh();
            }}
          />
        </main>
      ) : (
        <>
          {!simple && (
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
          )}

          <main id="main" className="main-panel">
            {(simple || tab === "live") && (
              <>
                <PresetPicker
                  activeId={state.active_preset}
                  onApplied={() => refresh()}
                />

                <div className="session-controls action-row">
                  {!state.running ? (
                    <button
                      type="button"
                      className="target-btn target-xl"
                      onClick={() => start("simulator")}
                    >
                      Start session
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="target-btn secondary target-xl"
                      onClick={() => stop()}
                    >
                      Stop session
                    </button>
                  )}
                </div>

                {!simple && (
                  <>
                    <div className="action-row">
                      <button
                        type="button"
                        className="target-btn secondary"
                        onClick={() => start("replay")}
                      >
                        Replay demo
                      </button>
                      <button
                        type="button"
                        className="target-btn secondary"
                        onClick={() => start("neuralink_stub")}
                      >
                        Intent stub
                      </button>
                    </div>
                    <RecipePicker value={recipe} onChange={setRecipe} />
                    <div className="action-row">
                      <button
                        type="button"
                        className={
                          state.predictive_enabled
                            ? "target-btn recipe active"
                            : "target-btn secondary recipe"
                        }
                        onClick={() => setPredictive(!state.predictive_enabled)}
                      >
                        Predictive {state.predictive_enabled ? "on" : "off"}
                      </button>
                    </div>
                  </>
                )}

                {state.precursors && state.precursors.length > 0 && (
                  <p className="meta-line" aria-live="polite">
                    Precursor:{" "}
                    {state.precursors
                      .map(
                        (p) =>
                          `${String(p.kind)} (${Number(p.confidence).toFixed(2)})`
                      )
                      .join(", ")}
                  </p>
                )}

                <FlowRing
                  state={state.flow.state}
                  engagement={state.flow.engagement}
                  minutes={Number(
                    state.flow.minutes_in_state?.toFixed?.(1) ??
                      state.flow.minutes_in_state
                  )}
                />

                <section className="status-block" aria-live="polite">
                  <h2>
                    {architectLabel(state.mode, state.agent_paused, state.running)}
                  </h2>
                  <p className="explanation">{explanationText}</p>
                  {!simple && (
                    <p className="meta-line">
                      conf {state.flow.confidence?.toFixed?.(2) ?? "—"} · {recipe}
                      {state.thresholds
                        ? ` · thr ${state.thresholds.protect?.toFixed?.(2)}/${state.thresholds.deep?.toFixed?.(2)}`
                        : ""}
                    </p>
                  )}
                  <div className="action-row">
                    <button
                      type="button"
                      className="target-btn"
                      onClick={() => setShowWhy(true)}
                    >
                      Why?
                    </button>
                  </div>
                  <div className="action-row label-row">
                    <button
                      type="button"
                      className="target-btn secondary"
                      onClick={() => label(true)}
                      disabled={!state.running}
                    >
                      Felt in flow
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

                <div className="action-row" style={{ marginTop: "1rem" }}>
                  <button
                    type="button"
                    className="target-btn secondary"
                    onClick={() => setSimpleMode(!simple)}
                  >
                    {simple ? "Show more options" : "Simple mode"}
                  </button>
                </div>
              </>
            )}

            {!simple && tab === "insights" && (
              <InsightsPanel session={state.session} />
            )}
            {!simple && tab === "coaching" && <CoachingPanel />}
          </main>
        </>
      )}

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
          Local · Not a medical device · Built for BCI users ·{" "}
          <span className="dim">Pause is always available</span>
        </p>
      </footer>
    </div>
  );
}
