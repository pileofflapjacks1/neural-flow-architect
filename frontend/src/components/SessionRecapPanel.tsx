import { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Recap = {
  ok?: boolean;
  message?: string;
  session_id?: string;
  recipe?: string;
  adapter?: string;
  totals?: {
    flow_minutes?: number;
    peak_engagement?: number;
    actions?: number;
    undos?: number;
    undo_rate?: number;
    labels_positive?: number;
    labels_negative?: number;
    state_minutes?: Record<string, number>;
  };
  block_review?: Record<string, unknown> | null;
  helped?: string[];
  hurt?: string[];
  recommendations?: string[];
  disclaimer?: string;
};

type Props = {
  /** Refresh when session id or running flag changes */
  sessionId?: string | null;
  running?: boolean;
};

export function SessionRecapPanel({ sessionId, running }: Props) {
  const [recap, setRecap] = useState<Recap | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    const q =
      sessionId && !running
        ? `?session_id=${encodeURIComponent(sessionId)}`
        : "";
    fetch(`${API_BASE}/session/recap${q}`)
      .then((r) => r.json())
      .then((d) => setRecap(d.recap || null))
      .catch(() => setError("Could not load session recap"));
  }, [sessionId, running]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll lightly while live so labels/actions update the recap
  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(load, 8000);
    return () => window.clearInterval(id);
  }, [running, load]);

  if (error) return <p className="explanation">{error}</p>;
  if (!recap) return <p className="explanation">Loading session recap…</p>;

  if (recap.ok === false) {
    return (
      <section className="insights" aria-labelledby="session-recap-title">
        <h2 id="session-recap-title">Session recap</h2>
        <p className="explanation">
          {recap.message || "No session summary yet — start and stop a block."}
        </p>
        <button type="button" className="target-btn secondary" onClick={() => load()}>
          Refresh
        </button>
      </section>
    );
  }

  const t = recap.totals || {};
  const sid = recap.session_id
    ? String(recap.session_id).slice(0, 8)
    : sessionId
      ? String(sessionId).slice(0, 8)
      : "—";

  return (
    <section className="insights session-recap-panel" aria-labelledby="session-recap-title">
      <h2 id="session-recap-title">Session recap</h2>
      <p className="dim">{recap.disclaimer}</p>
      <p className="meta-line">
        Session {sid}… · {recap.recipe || "—"} · {recap.adapter || "—"}
        {running ? " · live" : " · last saved"}
      </p>

      <ul className="insight-stats">
        <li>
          <strong>Flow-ish minutes</strong>{" "}
          {Number(t.flow_minutes ?? 0).toFixed(1)}
        </li>
        <li>
          <strong>Peak engagement</strong>{" "}
          {Number(t.peak_engagement ?? 0).toFixed(2)}
        </li>
        <li>
          <strong>Actions / undos</strong> {t.actions ?? 0} / {t.undos ?? 0}
          {typeof t.undo_rate === "number"
            ? ` (${Math.round(t.undo_rate * 100)}%)`
            : ""}
        </li>
        <li>
          <strong>Labels</strong> +{t.labels_positive ?? 0} / −
          {t.labels_negative ?? 0}
        </li>
      </ul>

      <h3 className="recap-helped-title">What helped</h3>
      <ul className="exp-list recap-list helped">
        {(recap.helped || []).length === 0 && (
          <li className="dim">Nothing recorded yet.</li>
        )}
        {(recap.helped || []).map((h, i) => (
          <li key={`h-${i}`}>{h}</li>
        ))}
      </ul>

      <h3 className="recap-hurt-title">What may have hurt</h3>
      <ul className="exp-list recap-list hurt">
        {(recap.hurt || []).length === 0 && (
          <li className="dim">No clear friction signals.</li>
        )}
        {(recap.hurt || []).map((h, i) => (
          <li key={`x-${i}`}>{h}</li>
        ))}
      </ul>

      <h3>Recommendations</h3>
      <ul className="exp-list">
        {(recap.recommendations || []).map((r, i) => (
          <li key={`r-${i}`}>{r}</li>
        ))}
      </ul>

      {recap.block_review && (
        <>
          <h3>Block review</h3>
          <p className="meta-line">
            Block helpful: {String(recap.block_review.helpful_block ?? "—")} ·
            Architect: {String(recap.block_review.architect_helpful ?? "—")}
          </p>
        </>
      )}

      {t.state_minutes && Object.keys(t.state_minutes).length > 0 && (
        <>
          <h3>Time by state</h3>
          <ul className="exp-list">
            {Object.entries(t.state_minutes).map(([k, v]) => (
              <li key={k}>
                {k}: {Number(v).toFixed(2)} min
              </li>
            ))}
          </ul>
        </>
      )}

      <div className="action-row">
        <button type="button" className="target-btn secondary" onClick={() => load()}>
          Refresh recap
        </button>
      </div>
      <p className="dim">
        API: <code>GET /session/recap</code>
      </p>
    </section>
  );
}
