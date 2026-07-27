import { useCallback, useEffect, useRef, useState } from "react";
import { createDemoController, shouldUseDemoMode } from "../demo/simulator";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";
const WS_URL = import.meta.env.VITE_NFA_WS ?? "ws://127.0.0.1:8741/ws/state";

export type FlowStatePayload = {
  state: string;
  engagement: number;
  arousal_balance?: number;
  self_ref_proxy?: number;
  effort_ease?: number;
  confidence: number;
  minutes_in_state: number;
  reasons?: string[];
};

export type NfaState = {
  running: boolean;
  agent_paused: boolean;
  can_undo: boolean;
  mode: string;
  flow: FlowStatePayload;
  digital: Record<string, unknown>;
  explanation: { action: string; text: string; because?: unknown[] } | null;
  explanations?: unknown[];
  actions?: unknown[];
  session: Record<string, unknown> | null;
  adapter: string;
  signal: string;
  recipe?: string;
  quality?: { overall?: number };
  thresholds?: { protect?: number; deep?: number };
  learning?: { message?: string };
  precursors?: Array<Record<string, unknown>>;
  predictive_enabled?: boolean;
  llm_enabled?: boolean;
  simple_mode?: boolean;
  active_preset?: string | null;
  onboarding_completed?: boolean;
  last_intent?: {
    type?: string;
    confidence?: number;
    result?: Record<string, unknown>;
  } | null;
  a11y?: {
    ui_scale?: number;
    high_contrast?: boolean;
    reduced_motion?: boolean;
    dwell_ms?: number;
    sticky_controls?: boolean;
    keyboard_enabled?: boolean;
    voice_command_bar?: boolean;
    auto_start_on_preset?: boolean;
    scan_mode?: boolean;
    scan_interval_ms?: number;
    announce_actions?: boolean;
    keyboard_map?: Array<{
      code?: string;
      key?: string;
      label?: string;
      intent?: string;
    }>;
    scan_presets_ms?: number[];
    dwell_presets_ms?: number[];
    css?: Record<string, string>;
  };
  session_health?: {
    tick_count?: number;
    uptime_sec?: number;
    heartbeat_ok?: boolean;
  };
  failsafe?: {
    active?: boolean;
    reason?: string;
    message?: string;
  };
  recent_actions?: Array<{ tool_id?: string; explanation?: string }>;
  quiet_hours?: {
    enabled?: boolean;
    start_hour?: number;
    end_hour?: number;
    active_now?: boolean;
  };
  recipe_suggestion?: {
    suggested_recipe?: string;
    message?: string;
    from_category?: string;
  } | null;
  audit_recent?: Array<Record<string, unknown>>;
  pending_block_review?: {
    session_id?: string;
    prompt?: string;
    flow_minutes?: number;
    actions_count?: number;
    undos_count?: number;
  } | null;
  caregiver_checklist?: {
    completed?: boolean;
    progress?: number;
    total?: number;
    items?: Array<{ id: string; label: string; done: boolean }>;
  };
  scan_mode?: boolean;
  scan_interval_ms?: number;
  preferences?: Record<string, unknown>;
  context?: Record<string, unknown>;
  ts?: string;
  error?: string;
};

const defaultState: NfaState = {
  running: false,
  agent_paused: false,
  can_undo: false,
  mode: "idle",
  flow: {
    state: "unknown",
    engagement: 0,
    confidence: 0,
    minutes_in_state: 0,
  },
  digital: {},
  explanation: null,
  session: null,
  adapter: "simulator",
  signal: "idle",
  simple_mode: true,
  onboarding_completed: true,
};

async function post(path: string, body?: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json();
}

export function useNfaSession() {
  const demoMode = shouldUseDemoMode();
  const [state, setState] = useState<NfaState>(defaultState);
  const [connected, setConnected] = useState(demoMode);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const demoRef = useRef<ReturnType<typeof createDemoController> | null>(null);

  // —— Browser research demo (hosted / ?demo=1) ——
  useEffect(() => {
    if (!demoMode) return;
    const demo = createDemoController();
    demoRef.current = demo;
    const unsub = demo.subscribe((s) => {
      setState(s);
      setConnected(true);
      setError(null);
    });
    // Auto-start so Beach "Open live demo" visitors see motion immediately
    const t = window.setTimeout(() => {
      demo.start("demo_simulator");
    }, 400);
    return () => {
      window.clearTimeout(t);
      unsub();
      demo.dispose();
      demoRef.current = null;
    };
  }, [demoMode]);

  const refresh = useCallback(() => {
    if (demoMode) {
      const s = demoRef.current?.getState();
      if (s) setState(s);
      return;
    }
    fetch(`${API_BASE}/state`)
      .then((r) => r.json())
      .then((data) => setState((s) => ({ ...s, ...data })))
      .catch(() => setError("API unreachable — run `nfa start` on port 8741"));
  }, [demoMode]);

  useEffect(() => {
    if (demoMode) return;
    let closed = false;
    let retry: number | undefined;

    const connect = () => {
      if (closed) return;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => {
        setConnected(true);
        setError(null);
        ws.send("hello");
      };
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === "pong" && data.state) {
            setState((s) => ({ ...s, ...data.state }));
            return;
          }
          setState((s) => ({ ...s, ...data }));
        } catch {
          /* ignore malformed */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) {
          retry = window.setTimeout(connect, 1500);
        }
      };
      ws.onerror = () => {
        setError("WebSocket error — is `nfa start` running?");
      };
    };

    connect();
    refresh();

    return () => {
      closed = true;
      if (retry) window.clearTimeout(retry);
      wsRef.current?.close();
    };
  }, [demoMode, refresh]);

  const start = useCallback(
    async (adapter?: string) => {
      setError(null);
      if (demoMode) {
        demoRef.current?.start(adapter);
        return;
      }
      try {
        const res = await post("/session/start", { adapter: adapter ?? null });
        if (res.state) setState((s) => ({ ...s, ...res.state }));
      } catch (e) {
        setError(e instanceof Error ? e.message : "start failed");
      }
    },
    [demoMode]
  );

  const stop = useCallback(async () => {
    if (demoMode) {
      demoRef.current?.stop();
      return;
    }
    try {
      const res = await post("/session/stop");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "stop failed");
    }
  }, [demoMode]);

  const setPaused = useCallback(
    async (paused: boolean) => {
      if (demoMode) {
        demoRef.current?.setPaused(paused);
        return;
      }
      try {
        const res = await post("/agent/pause", { paused });
        if (res.state) setState((s) => ({ ...s, ...res.state }));
      } catch (e) {
        setError(e instanceof Error ? e.message : "pause failed");
      }
    },
    [demoMode]
  );

  const undo = useCallback(async () => {
    if (demoMode) {
      demoRef.current?.undo();
      return;
    }
    try {
      const res = await post("/agent/undo");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "undo failed");
    }
  }, [demoMode]);

  const restMode = useCallback(async () => {
    if (demoMode) {
      demoRef.current?.restMode();
      return;
    }
    try {
      const res = await post("/agent/rest");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "rest failed");
    }
  }, [demoMode]);

  const label = useCallback(
    async (felt_in_flow: boolean, note = "") => {
      if (demoMode) {
        demoRef.current?.label(felt_in_flow);
        return { ok: true };
      }
      try {
        const res = await post("/session/label", { felt_in_flow, note });
        if (res.state) setState((s) => ({ ...s, ...res.state }));
        return res;
      } catch (e) {
        setError(e instanceof Error ? e.message : "label failed");
        return null;
      }
    },
    [demoMode]
  );

  const toolPref = useCallback(
    async (tool_id: string, action: string) => {
      if (demoMode) {
        demoRef.current?.feedback(tool_id, action);
        return;
      }
      try {
        const res = await post("/prefs/tool", { tool_id, action });
        if (res.state) setState((s) => ({ ...s, ...res.state }));
      } catch (e) {
        setError(e instanceof Error ? e.message : "pref failed");
      }
    },
    [demoMode]
  );

  const setRecipe = useCallback(
    async (recipe: string) => {
      if (demoMode) {
        demoRef.current?.setRecipe(recipe);
        return;
      }
      try {
        const res = await post("/recipe", { recipe });
        if (res.state) setState((s) => ({ ...s, ...res.state }));
      } catch (e) {
        setError(e instanceof Error ? e.message : "recipe failed");
      }
    },
    [demoMode]
  );

  const setPredictive = useCallback(
    async (enabled: boolean) => {
      if (demoMode) {
        demoRef.current?.setPredictive(enabled);
        return;
      }
      try {
        const res = await post("/agent/predictive", { enabled });
        if (res.state) setState((s) => ({ ...s, ...res.state }));
      } catch (e) {
        setError(e instanceof Error ? e.message : "predictive toggle failed");
      }
    },
    [demoMode]
  );

  const setSimpleMode = useCallback(
    async (enabled: boolean) => {
      if (demoMode) {
        demoRef.current?.setSimpleMode(enabled);
        return;
      }
      try {
        const res = await post("/ui/simple_mode", { enabled });
        if (res.state) setState((s) => ({ ...s, ...res.state }));
      } catch (e) {
        setError(e instanceof Error ? e.message : "simple mode failed");
      }
    },
    [demoMode]
  );

  const feedback = useCallback(
    async (tool_id: string, rating: "helpful" | "unhelpful" | "never") => {
      if (demoMode) {
        demoRef.current?.feedback(tool_id, rating);
        return { ok: true };
      }
      try {
        const res = await post("/agent/feedback", { tool_id, rating });
        if (res.state) setState((s) => ({ ...s, ...res.state }));
        return res;
      } catch (e) {
        setError(e instanceof Error ? e.message : "feedback failed");
        return null;
      }
    },
    [demoMode]
  );

  const clearFailsafe = useCallback(async () => {
    if (demoMode) {
      demoRef.current?.clearFailsafe();
      return;
    }
    try {
      const res = await post("/agent/failsafe/clear");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "clear failsafe failed");
    }
  }, [demoMode]);

  const acceptRecipeSuggestion = useCallback(async () => {
    if (demoMode) {
      demoRef.current?.acceptRecipeSuggestion();
      return;
    }
    try {
      const res = await post("/recipe/accept_suggestion");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "accept recipe failed");
    }
  }, [demoMode]);

  const submitBlockReview = useCallback(
    async (_payload: {
      helpful_block: boolean | null;
      architect_helpful: boolean | null;
      note?: string;
      skip?: boolean;
    }) => {
      if (demoMode) {
        demoRef.current?.submitBlockReview();
        return;
      }
      try {
        const res = await post("/session/block_review", _payload);
        if (res.state) setState((s) => ({ ...s, ...res.state }));
      } catch (e) {
        setError(e instanceof Error ? e.message : "block review failed");
      }
    },
    [demoMode]
  );

  return {
    state,
    connected,
    error,
    apiBase: API_BASE,
    demoMode,
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
    acceptRecipeSuggestion,
    submitBlockReview,
    refresh,
  };
}
