import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type TimelineEvent = {
  t_sec?: number;
  kind?: string;
  detail?: Record<string, unknown>;
};

type Filter = "all" | "state" | "action" | "undo";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "state", label: "State" },
  { id: "action", label: "Action" },
  { id: "undo", label: "Undo" },
];

function formatEvent(ev: TimelineEvent): string {
  const t = typeof ev.t_sec === "number" ? `${Math.floor(ev.t_sec)}s` : "—";
  const kind = ev.kind || "event";
  const d = ev.detail || {};
  if (kind === "state") {
    return `${t} · state → ${String(d.state ?? "?")} (eng ${Number(d.engagement ?? 0).toFixed(2)})`;
  }
  if (kind === "action") {
    const tool = d.tool_id ? String(d.tool_id) : "action";
    const text = d.text ? ` — ${String(d.text).slice(0, 80)}` : "";
    return `${t} · ${tool}${text}`;
  }
  if (kind === "undo") {
    return `${t} · undo`;
  }
  return `${t} · ${kind}`;
}

export function TimelinePanel() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");

  const load = () => {
    fetch(`${API_BASE}/timeline`)
      .then((r) => r.json())
      .then((d) => {
        setEvents(d.timeline || []);
        setSessionId(d.session_id ? String(d.session_id) : null);
        setLive(!!d.live);
        if (!d.ok && d.message) setError(String(d.message));
        else setError(null);
      })
      .catch(() => setError("Could not load session timeline"));
  };

  useEffect(() => {
    load();
    const id = window.setInterval(load, 4000);
    return () => window.clearInterval(id);
  }, []);

  const filtered = useMemo(() => {
    if (filter === "all") return events;
    return events.filter((e) => (e.kind || "") === filter);
  }, [events, filter]);

  const counts = useMemo(() => {
    const c = { all: events.length, state: 0, action: 0, undo: 0 };
    for (const e of events) {
      const k = e.kind || "";
      if (k === "state") c.state += 1;
      else if (k === "action") c.action += 1;
      else if (k === "undo") c.undo += 1;
    }
    return c;
  }, [events]);

  return (
    <section className="insights" aria-labelledby="timeline-title">
      <h2 id="timeline-title">Session timeline</h2>
      <p className="meta-line">
        {sessionId ? `Session ${sessionId.slice(0, 8)}…` : "No session yet"}
        {live ? " · live" : " · last saved"}
      </p>

      <div
        className="preset-chips action-row"
        role="group"
        aria-label="Timeline filters"
      >
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            className={
              filter === f.id
                ? "target-btn recipe active"
                : "target-btn secondary recipe"
            }
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
            <span className="dim"> ({counts[f.id]})</span>
          </button>
        ))}
      </div>

      {error && <p className="explanation">{error}</p>}
      <ul className="timeline-list exp-list" aria-live="polite">
        {filtered.length === 0 && (
          <li>
            {events.length === 0
              ? "No events yet — start a session."
              : `No ${filter} events in this session.`}
          </li>
        )}
        {filtered
          .slice()
          .reverse()
          .slice(0, 40)
          .map((ev, i) => (
            <li key={`${ev.t_sec}-${ev.kind}-${i}`}>{formatEvent(ev)}</li>
          ))}
      </ul>
      <p className="dim">
        Compact log of state changes, agent actions, and undos. Stays on this
        device.
      </p>
    </section>
  );
}
