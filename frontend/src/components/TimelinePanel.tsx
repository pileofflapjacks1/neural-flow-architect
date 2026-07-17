import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type TimelineEvent = {
  t_sec?: number;
  kind?: string;
  detail?: Record<string, unknown>;
};

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

  return (
    <section className="insights" aria-labelledby="timeline-title">
      <h2 id="timeline-title">Session timeline</h2>
      <p className="meta-line">
        {sessionId ? `Session ${sessionId.slice(0, 8)}…` : "No session yet"}
        {live ? " · live" : " · last saved"}
      </p>
      {error && <p className="explanation">{error}</p>}
      <ul className="timeline-list exp-list" aria-live="polite">
        {events.length === 0 && <li>No events yet — start a session.</li>}
        {events
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
