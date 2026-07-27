/**
 * Browser-only research demo simulator.
 * No neural data, no implant APIs — synthetic engagement trajectory for NeuraBeach.
 * Not a medical device.
 */

import type { NfaState } from "../hooks/useNfaSession";

const DEMO_SESSION_ID = "demo-local-session";

const STATES = ["low", "pre_flow", "flow", "deep_flow", "post_flow", "flow"] as const;

export type DemoController = {
  getState: () => NfaState;
  start: (adapter?: string) => void;
  stop: () => void;
  setPaused: (paused: boolean) => void;
  undo: () => void;
  restMode: () => void;
  label: (felt: boolean) => void;
  setRecipe: (recipe: string) => void;
  setSimpleMode: (enabled: boolean) => void;
  setPredictive: (enabled: boolean) => void;
  feedback: (toolId: string, rating: string) => void;
  clearFailsafe: () => void;
  submitBlockReview: () => void;
  acceptRecipeSuggestion: () => void;
  subscribe: (fn: (s: NfaState) => void) => () => void;
  dispose: () => void;
};

function baseState(): NfaState {
  return {
    running: false,
    agent_paused: false,
    can_undo: false,
    mode: "idle",
    flow: {
      state: "unknown",
      engagement: 0.35,
      arousal_balance: 0.5,
      self_ref_proxy: 0.4,
      effort_ease: 0.45,
      confidence: 0.85,
      minutes_in_state: 0,
      reasons: ["demo_simulator"],
    },
    digital: { focus: false, suppress: false, density: "normal" },
    explanation: {
      action: "demo.idle",
      text: "Research demo — synthetic engagement only. Start a session to see the co-pilot protect focus.",
      because: [
        { signal: "source", value: "browser_demo" },
        { signal: "disclaimer", value: "not_a_medical_device" },
      ],
    },
    session: null,
    adapter: "demo_simulator",
    signal: "good",
    recipe: "study",
    quality: { overall: 0.92 },
    thresholds: { protect: 0.62, deep: 0.82 },
    simple_mode: true,
    onboarding_completed: true,
    active_preset: "morning_focus",
    a11y: {
      ui_scale: 1.15,
      high_contrast: false,
      reduced_motion: true,
      dwell_ms: 1200,
      sticky_controls: true,
      keyboard_enabled: true,
      voice_command_bar: true,
      scan_mode: false,
      scan_interval_ms: 1400,
      announce_actions: true,
      scan_presets_ms: [800, 1400, 2000],
      dwell_presets_ms: [800, 1200, 1800],
      css: { "--nfa-scale": "1.15", "--target-min": "74px" },
    },
    session_health: { tick_count: 0, uptime_sec: 0, heartbeat_ok: true },
    failsafe: { active: false },
    quiet_hours: { enabled: false, active_now: false },
    predictive_enabled: false,
    llm_enabled: false,
    preferences: { protect_style: "calm" },
    context: {
      recipe: "study",
      time_of_day: "morning",
      active_app: "Demo Browser",
      app_category: "study",
    },
    pending_block_review: null,
    recent_actions: [],
    audit_recent: [
      {
        event_type: "demo.boot",
        message: "Browser research demo (no neural stream, no cloud)",
      },
    ],
  };
}

export function createDemoController(): DemoController {
  let state = baseState();
  let tick = 0;
  let phase = 0;
  let eng = 0.4;
  let minutesIn = 0;
  let startedAt: number | null = null;
  let timer: number | null = null;
  const listeners = new Set<(s: NfaState) => void>();
  let undoStack: string[] = [];
  let labelsPos = 0;
  let labelsNeg = 0;

  const emit = () => {
    listeners.forEach((fn) => fn({ ...state, flow: { ...state.flow } }));
  };

  const explain = (action: string, text: string, because: unknown[] = []) => {
    state = {
      ...state,
      explanation: { action, text, because },
      recent_actions: [
        { tool_id: action, explanation: text },
        ...(state.recent_actions || []).slice(0, 8),
      ],
      can_undo: undoStack.length > 0,
    };
  };

  const applyProtect = () => {
    undoStack.push("protect");
    state = {
      ...state,
      mode: "protect",
      digital: { focus: true, suppress: true, density: "minimal" },
      can_undo: true,
    };
    explain(
      "notify.suppress_noncritical",
      "Demo: softened non-critical notifications because synthetic engagement is rising in study recipe.",
      [
        { signal: "engagement", value: eng.toFixed(2) },
        { signal: "recipe", value: state.recipe || "study" },
        { signal: "module", value: "protector" },
        { signal: "demo", value: true },
      ]
    );
  };

  const step = () => {
    if (!state.running || state.agent_paused) {
      if (state.running && startedAt) {
        const up = (Date.now() - startedAt) / 1000;
        state = {
          ...state,
          session_health: {
            tick_count: tick,
            uptime_sec: Math.floor(up),
            heartbeat_ok: true,
          },
        };
        emit();
      }
      return;
    }

    tick += 1;
    phase = (phase + 1) % 200;
    // Smooth synthetic engagement trajectory
    const target =
      0.45 +
      0.35 * Math.sin(phase / 28) +
      0.12 * Math.sin(phase / 9) +
      (phase > 60 && phase < 140 ? 0.15 : 0);
    eng = eng * 0.85 + target * 0.15;
    eng = Math.max(0.15, Math.min(0.95, eng));
    minutesIn += 0.5 / 60;

    let flowState = "low";
    if (eng >= 0.82) flowState = "deep_flow";
    else if (eng >= 0.62) flowState = "flow";
    else if (eng >= 0.5) flowState = "pre_flow";
    else if (eng < 0.3) flowState = "fatigued";

    let mode = "monitor";
    if (state.agent_paused) mode = "idle";
    else if (eng >= 0.62) mode = "protect";
    else if (eng < 0.4) mode = "re_enter";
    else mode = "monitor";

    const up = startedAt ? (Date.now() - startedAt) / 1000 : 0;

    state = {
      ...state,
      mode,
      signal: eng > 0.35 ? "good" : "degraded",
      quality: { overall: 0.88 + 0.1 * Math.random() * 0.1 },
      flow: {
        state: flowState,
        engagement: Number(eng.toFixed(3)),
        arousal_balance: Number((0.55 + 0.1 * Math.sin(phase / 20)).toFixed(3)),
        self_ref_proxy: Number((0.45 - eng * 0.15).toFixed(3)),
        effort_ease: Number((0.4 + eng * 0.35).toFixed(3)),
        confidence: 0.9,
        minutes_in_state: Number(minutesIn.toFixed(2)),
        reasons: ["demo_simulator", `phase=${phase}`],
      },
      session: {
        session_id: DEMO_SESSION_ID,
        adapter: "demo_simulator",
        recipe: state.recipe,
        peak_engagement: Math.max(
          Number((state.session as { peak_engagement?: number })?.peak_engagement || 0),
          eng
        ),
        flow_minutes: Number(
          ((up / 60) * (eng > 0.55 ? eng : 0.2)).toFixed(2)
        ),
        actions_count: undoStack.length + (state.recent_actions?.length || 0),
        undos_count: Math.max(0, (state.session as { undos_count?: number })?.undos_count || 0),
        labels: [],
        state_minutes: {
          [flowState]: Number((up / 60).toFixed(2)),
        },
      },
      session_health: {
        tick_count: tick,
        uptime_sec: Math.floor(up),
        heartbeat_ok: true,
      },
    };

    // Occasional protect action when entering flow
    if (eng > 0.7 && phase % 40 === 0 && !state.agent_paused) {
      applyProtect();
    } else if (eng < 0.4 && phase % 50 === 0) {
      explain(
        "ui.set_density",
        "Demo: easing interface density to help re-enter focus after engagement dipped.",
        [
          { signal: "engagement", value: eng.toFixed(2) },
          { signal: "module", value: "reentry" },
        ]
      );
      state = {
        ...state,
        mode: "re_enter",
        digital: { ...state.digital, density: "calm" },
      };
    }

    emit();
  };

  return {
    getState: () => state,
    subscribe: (fn) => {
      listeners.add(fn);
      fn(state);
      return () => listeners.delete(fn);
    },
    dispose: () => {
      if (timer != null) window.clearInterval(timer);
      timer = null;
      listeners.clear();
    },
    start: (adapter?: string) => {
      startedAt = Date.now();
      tick = 0;
      minutesIn = 0;
      eng = 0.42;
      undoStack = [];
      state = {
        ...baseState(),
        running: true,
        adapter: adapter || "demo_simulator",
        simple_mode: state.simple_mode,
        recipe: state.recipe || "study",
        onboarding_completed: true,
        signal: "good",
        mode: "monitor",
        session: {
          session_id: DEMO_SESSION_ID,
          adapter: "demo_simulator",
          recipe: state.recipe || "study",
          peak_engagement: 0.42,
          flow_minutes: 0,
          actions_count: 0,
          undos_count: 0,
        },
        explanation: {
          action: "session.start",
          text: "Demo session started with a synthetic engagement stream. Architect will protect focus when engagement rises.",
          because: [{ signal: "demo", value: true }],
        },
      };
      if (timer != null) window.clearInterval(timer);
      timer = window.setInterval(step, 500);
      emit();
    },
    stop: () => {
      if (timer != null) window.clearInterval(timer);
      timer = null;
      const up = startedAt ? (Date.now() - startedAt) / 1000 : 0;
      state = {
        ...state,
        running: false,
        mode: "idle",
        pending_block_review: {
          session_id: DEMO_SESSION_ID,
          prompt: "Did this demo block feel helpful?",
          flow_minutes: Number((up / 60).toFixed(1)),
          actions_count: state.recent_actions?.length || 0,
          undos_count: (state.session as { undos_count?: number })?.undos_count || 0,
        },
        explanation: {
          action: "session.stop",
          text: "Demo session stopped. This was a browser simulation — install the open-source CLI for a full local stack.",
          because: [{ signal: "demo", value: true }],
        },
      };
      startedAt = null;
      emit();
    },
    setPaused: (paused: boolean) => {
      state = {
        ...state,
        agent_paused: paused,
        mode: paused ? "idle" : eng >= 0.62 ? "protect" : "monitor",
        explanation: {
          action: paused ? "agent.pause" : "agent.resume",
          text: paused
            ? "Architect paused — you are fully in control."
            : "Architect resumed monitoring synthetic engagement.",
          because: [{ signal: "user_override", value: true }],
        },
      };
      emit();
    },
    undo: () => {
      if (!undoStack.length) {
        explain("undo.empty", "Nothing to undo in this demo yet.");
        emit();
        return;
      }
      undoStack.pop();
      const undos =
        ((state.session as { undos_count?: number })?.undos_count || 0) + 1;
      state = {
        ...state,
        digital: { focus: false, suppress: false, density: "normal" },
        can_undo: undoStack.length > 0,
        session: state.session
          ? { ...state.session, undos_count: undos }
          : state.session,
      };
      explain("undo", "Demo: reversed the last environment change.");
      emit();
    },
    restMode: () => {
      state = {
        ...state,
        recipe: "rest",
        mode: "transition",
        digital: { focus: false, suppress: false, density: "normal" },
        context: { ...state.context, recipe: "rest" },
      };
      explain(
        "recipe.apply",
        "Demo: switched to rest recipe — wind-down supports for a softer context.",
        [{ signal: "recipe", value: "rest" }]
      );
      emit();
    },
    label: (felt: boolean) => {
      if (felt) labelsPos += 1;
      else labelsNeg += 1;
      state = {
        ...state,
        learning: {
          message: felt
            ? `Demo label: felt in flow (local counter ${labelsPos}). Full hybrid ML trains on a local install.`
            : `Demo label: not really (local counter ${labelsNeg}). Thresholds would nudge on a real session.`,
        },
      };
      emit();
    },
    setRecipe: (recipe: string) => {
      state = {
        ...state,
        recipe,
        context: { ...state.context, recipe },
      };
      explain("recipe.apply", `Demo: recipe set to ${recipe}.`);
      emit();
    },
    setSimpleMode: (enabled: boolean) => {
      state = { ...state, simple_mode: enabled };
      emit();
    },
    setPredictive: (enabled: boolean) => {
      state = {
        ...state,
        predictive_enabled: enabled,
        precursors: enabled
          ? [{ kind: "rising_flow", confidence: 0.6 }]
          : [],
      };
      emit();
    },
    feedback: (_toolId: string, rating: string) => {
      explain(
        "feedback",
        `Demo feedback recorded: ${rating}. On a local install this updates tool affinity.`,
        [{ signal: "rating", value: rating }]
      );
      emit();
    },
    clearFailsafe: () => {
      state = {
        ...state,
        failsafe: { active: false },
      };
      emit();
    },
    submitBlockReview: () => {
      state = {
        ...state,
        pending_block_review: null,
        learning: {
          message: "Demo block review saved locally in this browser tab only.",
        },
      };
      emit();
    },
    acceptRecipeSuggestion: () => {
      state = {
        ...state,
        recipe: "create",
        recipe_suggestion: null,
      };
      emit();
    },
  };
}

/** Hosted static site or ?demo=1 → browser simulator (no Python API). */
export function shouldUseDemoMode(): boolean {
  if (import.meta.env.VITE_NFA_DEMO === "true" || import.meta.env.VITE_NFA_DEMO === "1") {
    return true;
  }
  if (typeof window === "undefined") return false;
  const q = new URLSearchParams(window.location.search);
  if (q.get("demo") === "1" || q.get("demo") === "true") return true;
  // Production static deploy without explicit API base → demo
  const host = window.location.hostname;
  const isLocal = host === "localhost" || host === "127.0.0.1";
  if (!isLocal && !import.meta.env.VITE_NFA_API) return true;
  return false;
}

// silence unused STATES lint if any
void STATES;
