import { useEffect, useState } from "react";
import { FlowRing } from "./components/FlowRing";
import { ExplainDrawer } from "./components/ExplainDrawer";
import { OverrideBar } from "./components/OverrideBar";
import { InsightsPanel } from "./components/InsightsPanel";
import { RecipePicker } from "./components/RecipePicker";
import { CoachingPanel } from "./components/CoachingPanel";
import { Onboarding } from "./components/Onboarding";
import { PresetPicker } from "./components/PresetPicker";
import { VoiceCommandBar } from "./components/VoiceCommandBar";
import { A11yPanel } from "./components/A11yPanel";
import { BlockReviewModal } from "./components/BlockReviewModal";
import { ScanMode } from "./components/ScanMode";
import { DwellButton } from "./components/DwellButton";
import { CaregiverChecklist } from "./components/CaregiverChecklist";
import { SignaturePanel } from "./components/SignaturePanel";
import { useNfaSession } from "./hooks/useNfaSession";
import { useKeyboardIntents } from "./hooks/useKeyboardIntents";

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
    feedback,
    clearFailsafe,
    refresh,
    acceptRecipeSuggestion,
    submitBlockReview,
  } = useNfaSession();
  const [showWhy, setShowWhy] = useState(false);
  const [tab, setTab] = useState<
    "live" | "insights" | "coaching" | "access" | "setup"
  >("live");
  const [onboardingDone, setOnboardingDone] = useState(false);

  const simple = state.simple_mode !== false;
  const a11y = state.a11y;
  const scanOn = !!(state.scan_mode || a11y?.scan_mode);
  const dwellMs = a11y?.dwell_ms ?? state.a11y?.dwell_ms ?? 1200;
  const dwellOn = true; // always available for low-precision; click still instant
  const keyboardOn = a11y?.keyboard_enabled !== false && !scanOn;
  useKeyboardIntents(keyboardOn);

  const scanActions = [
    {
      id: "pause",
      label: state.agent_paused ? "Resume" : "Pause",
      run: () => setPaused(!state.agent_paused),
    },
    { id: "undo", label: "Undo", run: () => undo() },
    { id: "rest", label: "Rest", run: () => restMode() },
    {
      id: "session",
      label: state.running ? "Stop" : "Start",
      run: () => (state.running ? stop() : start("simulator")),
    },
    { id: "why", label: "Why?", run: () => setShowWhy(true) },
  ];

  useEffect(() => {
    const root = document.documentElement;
    if (a11y?.css) {
      Object.entries(a11y.css).forEach(([k, v]) => root.style.setProperty(k, String(v)));
    }
    root.classList.toggle("nfa-high-contrast", !!a11y?.high_contrast);
    root.classList.toggle("nfa-reduced-motion", a11y?.reduced_motion !== false);
  }, [a11y]);

  const explanationText =
    state.explanation?.text ??
    (state.running
      ? "No change yet — Architect is watching quietly."
      : "Start a session when ready. Pause and Undo always work.");

  const because = (state.explanation?.because as Array<Record<string, unknown>>) ?? [];
  const recipe = state.recipe ?? "study";
  const showOnboarding = !onboardingDone && state.onboarding_completed === false;
  const uptime = state.session_health?.uptime_sec;

  return (
    <div
      className={`app-shell ${simple ? "simple" : ""} ${a11y?.high_contrast ? "high-contrast" : ""}`}
    >
      <a className="skip-link" href="#main">
        Skip to main content
      </a>

      <header className="top-bar">
        <div>
          <h1>Neural Flow Architect</h1>
          <p className="signal-chip" aria-live="polite">
            {connected ? `Signal ${state.signal}` : "Connecting…"}
            {state.running ? " · live" : " · idle"}
            {state.adapter ? ` · ${state.adapter}` : ""}
            {typeof state.quality?.overall === "number" && state.running
              ? ` · q ${Number(state.quality.overall).toFixed(2)}`
              : ""}
            {simple ? " · simple mode" : " · full mode"}
            {typeof uptime === "number" && state.running
              ? ` · ${Math.floor(uptime / 60)}m`
              : ""}
          </p>
        </div>
        <OverrideBar
          paused={state.agent_paused}
          onToggle={() => setPaused(!state.agent_paused)}
        />
      </header>

      {/* Always-visible emergency controls OR scan mode */}
      {scanOn ? (
        <ScanMode
          enabled
          intervalMs={state.scan_interval_ms || a11y?.scan_interval_ms || 1400}
          dwellMs={dwellMs}
          dwellEnabled={dwellOn}
          actions={scanActions}
        />
      ) : (
        <div className="sticky-controls" role="toolbar" aria-label="Primary controls">
          <DwellButton
            label={state.agent_paused ? "Resume" : "Pause"}
            onActivate={() => setPaused(!state.agent_paused)}
            dwellMs={dwellMs}
            dwellEnabled={dwellOn}
            variant="override"
            aria-pressed={state.agent_paused}
          />
          <DwellButton
            label="Undo"
            onActivate={() => undo()}
            dwellMs={dwellMs}
            dwellEnabled={dwellOn}
            disabled={!state.can_undo}
            variant="primary"
          />
          <DwellButton
            label="Rest"
            onActivate={() => restMode()}
            dwellMs={dwellMs}
            dwellEnabled={dwellOn}
            variant="secondary"
          />
        </div>
      )}

      {error && (
        <div className="banner warn" role="alert">
          {error}
          <p className="meta-line">Tip: run <code>nfa start</code> in a terminal.</p>
        </div>
      )}

      {state.failsafe?.active && (
        <div className="banner warn" role="alert">
          <strong>Fail-safe:</strong> {state.failsafe.message || state.failsafe.reason}
          <div className="action-row" style={{ marginTop: "0.5rem" }}>
            <button
              type="button"
              className="target-btn override"
              onClick={() => setPaused(true)}
            >
              Pause now
            </button>
            {state.failsafe.reason !== "user_pause" && (
              <button
                type="button"
                className="target-btn secondary"
                onClick={() => clearFailsafe()}
              >
                Clear fail-safe
              </button>
            )}
          </div>
        </div>
      )}

      {state.quiet_hours?.active_now && (
        <div className="banner info" role="status">
          Quiet hours active — proactive protect is softened.
        </div>
      )}

      {state.recipe_suggestion && simple && (
        <div className="banner info" role="status">
          {String(state.recipe_suggestion.message)}
          <div className="action-row" style={{ marginTop: "0.5rem" }}>
            <button
              type="button"
              className="target-btn"
              onClick={() => acceptRecipeSuggestion()}
            >
              Switch recipe
            </button>
          </div>
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
              <button
                type="button"
                className={tab === "access" ? "tab active" : "tab"}
                onClick={() => setTab("access")}
              >
                Access
              </button>
              <button
                type="button"
                className={tab === "setup" ? "tab active" : "tab"}
                onClick={() => setTab("setup")}
              >
                Setup
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

                <VoiceCommandBar enabled={a11y?.voice_command_bar !== false} />

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
              <InsightsPanel
                session={state.session}
                context={state.context}
                quietHours={state.quiet_hours}
                recipeSuggestion={state.recipe_suggestion}
                auditRecent={state.audit_recent}
                onAcceptRecipe={() => acceptRecipeSuggestion()}
              />
            )}
            {!simple && tab === "coaching" && (
              <>
                <CoachingPanel />
                <SignaturePanel />
              </>
            )}
            {!simple && tab === "access" && <A11yPanel />}
            {!simple && tab === "setup" && <CaregiverChecklist />}
          </main>
        </>
      )}

      {state.pending_block_review && (
        <BlockReviewModal
          prompt={state.pending_block_review.prompt}
          flowMinutes={state.pending_block_review.flow_minutes}
          actions={state.pending_block_review.actions_count}
          undos={state.pending_block_review.undos_count}
          onSubmit={(p) => submitBlockReview(p)}
          onSkip={() => submitBlockReview({ helpful_block: null, architect_helpful: null, skip: true })}
        />
      )}

      {showWhy && (
        <ExplainDrawer
          text={explanationText}
          because={because}
          toolId={state.explanation?.action}
          onClose={() => setShowWhy(false)}
          onHelpful={
            state.explanation?.action
              ? () => {
                  feedback(state.explanation!.action, "helpful");
                  setShowWhy(false);
                }
              : undefined
          }
          onUnhelpful={
            state.explanation?.action
              ? () => {
                  feedback(state.explanation!.action, "unhelpful");
                  setShowWhy(false);
                }
              : undefined
          }
          onNever={
            state.explanation?.action
              ? () => {
                  feedback(state.explanation!.action, "never");
                  setShowWhy(false);
                }
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
          <span className="dim">P pause · U undo · R rest · F resume</span>
        </p>
      </footer>
    </div>
  );
}
