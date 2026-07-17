import { useCallback, useEffect, useRef, useState } from "react";

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
  const [state, setState] = useState<NfaState>(defaultState);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const refresh = useCallback(() => {
    fetch(`${API_BASE}/state`)
      .then((r) => r.json())
      .then((data) => setState((s) => ({ ...s, ...data })))
      .catch(() => setError("API unreachable — run `nfa start` on port 8741"));
  }, []);

  useEffect(() => {
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
  }, [refresh]);

  const start = useCallback(async (adapter?: string) => {
    setError(null);
    try {
      const res = await post("/session/start", { adapter: adapter ?? null });
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "start failed");
    }
  }, []);

  const stop = useCallback(async () => {
    try {
      const res = await post("/session/stop");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "stop failed");
    }
  }, []);

  const setPaused = useCallback(async (paused: boolean) => {
    try {
      const res = await post("/agent/pause", { paused });
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "pause failed");
    }
  }, []);

  const undo = useCallback(async () => {
    try {
      const res = await post("/agent/undo");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "undo failed");
    }
  }, []);

  const restMode = useCallback(async () => {
    try {
      const res = await post("/agent/rest");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "rest failed");
    }
  }, []);

  const label = useCallback(async (felt_in_flow: boolean, note = "") => {
    try {
      const res = await post("/session/label", { felt_in_flow, note });
      if (res.state) setState((s) => ({ ...s, ...res.state }));
      return res;
    } catch (e) {
      setError(e instanceof Error ? e.message : "label failed");
      return null;
    }
  }, []);

  const toolPref = useCallback(async (tool_id: string, action: string) => {
    try {
      const res = await post("/prefs/tool", { tool_id, action });
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "pref failed");
    }
  }, []);

  const setRecipe = useCallback(async (recipe: string) => {
    try {
      const res = await post("/recipe", { recipe });
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "recipe failed");
    }
  }, []);

  const setPredictive = useCallback(async (enabled: boolean) => {
    try {
      const res = await post("/agent/predictive", { enabled });
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "predictive toggle failed");
    }
  }, []);

  const setSimpleMode = useCallback(async (enabled: boolean) => {
    try {
      const res = await post("/ui/simple_mode", { enabled });
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "simple mode failed");
    }
  }, []);

  const feedback = useCallback(
    async (tool_id: string, rating: "helpful" | "unhelpful" | "never") => {
      try {
        const res = await post("/agent/feedback", { tool_id, rating });
        if (res.state) setState((s) => ({ ...s, ...res.state }));
        return res;
      } catch (e) {
        setError(e instanceof Error ? e.message : "feedback failed");
        return null;
      }
    },
    []
  );

  const clearFailsafe = useCallback(async () => {
    try {
      const res = await post("/agent/failsafe/clear");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "clear failsafe failed");
    }
  }, []);

  const acceptRecipeSuggestion = useCallback(async () => {
    try {
      const res = await post("/recipe/accept_suggestion");
      if (res.state) setState((s) => ({ ...s, ...res.state }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "accept recipe failed");
    }
  }, []);

  return {
    state,
    connected,
    error,
    apiBase: API_BASE,
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
    refresh,
  };
}
