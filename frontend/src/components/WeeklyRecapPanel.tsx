import { useEffect, useState } from "react";
import { Sparkline } from "./Sparkline";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Recap = {
  window_days?: number;
  sessions?: number;
  score?: number | null;
  interpretation?: string;
  trend?: string;
  totals?: {
    flow_minutes?: number;
    actions?: number;
    undos?: number;
    avg_peak_engagement?: number;
    undo_rate?: number;
  };
  top_recipe?: string | null;
  by_recipe?: Record<
    string,
    { sessions?: number; flow_minutes?: number; helpful_review_rate?: number }
  >;
  sparkline?: Array<{
    session_id?: string;
    started_at?: string;
    score?: number;
    flow_minutes?: number;
    recipe?: string;
  }>;
  highlights?: string[];
  disclaimer?: string;
};

const WINDOWS = [7, 14, 30] as const;

export function WeeklyRecapPanel() {
  const [days, setDays] = useState<number>(7);
  const [recap, setRecap] = useState<Recap | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    fetch(`${API_BASE}/weekly?days=${days}`)
      .then((r) => r.json())
      .then((d) => setRecap(d.recap || null))
      .catch(() => setError("Could not load weekly recap"));
  }, [days]);

  if (error) return <p className="explanation">{error}</p>;
  if (!recap) return <p className="explanation">Loading this week…</p>;

  const score = recap.score;
  const pct = score == null ? 0 : Math.round(Number(score));
  const trend = recap.trend || "flat";

  return (
    <section className="insights weekly-recap" aria-labelledby="weekly-title">
      <h2 id="weekly-title">This week</h2>
      <p className="dim">{recap.disclaimer}</p>

      <div
        className="preset-chips action-row"
        role="group"
        aria-label="Recap window"
      >
        {WINDOWS.map((d) => (
          <button
            key={d}
            type="button"
            className={
              days === d ? "target-btn recipe active" : "target-btn secondary recipe"
            }
            aria-pressed={days === d}
            onClick={() => setDays(d)}
          >
            {d}d
          </button>
        ))}
      </div>

      <ul className="insight-stats">
        <li>
          <strong>Policy score</strong>{" "}
          {score == null ? "—" : `${Number(score).toFixed(1)} / 100`}
          {trend !== "flat" ? ` · ${trend}` : ""}
        </li>
        <li>
          <strong>Sessions</strong> {recap.sessions ?? 0}
        </li>
        <li>
          <strong>Flow-ish minutes</strong>{" "}
          {Number(recap.totals?.flow_minutes ?? 0).toFixed(1)}
        </li>
        <li>
          <strong>Actions / undos</strong> {recap.totals?.actions ?? 0} /{" "}
          {recap.totals?.undos ?? 0}
          {typeof recap.totals?.undo_rate === "number"
            ? ` (${Math.round(recap.totals.undo_rate * 100)}%)`
            : ""}
        </li>
        {recap.top_recipe && (
          <li>
            <strong>Top recipe</strong> {recap.top_recipe}
          </li>
        )}
      </ul>

      <div
        className="bar"
        style={{ maxWidth: 360, marginTop: "0.5rem" }}
        aria-label={`Weekly score ${pct}`}
      >
        <div style={{ width: `${pct}%` }} />
      </div>

      <h3>Score trail</h3>
      <Sparkline
        points={recap.sparkline || []}
        label={`Policy scores last ${recap.window_days} days`}
      />

      {recap.interpretation && (
        <p className="explanation">{recap.interpretation}</p>
      )}

      <h3>Highlights</h3>
      <ul className="exp-list">
        {(recap.highlights || []).map((h, i) => (
          <li key={i}>{h}</li>
        ))}
      </ul>

      {recap.by_recipe && Object.keys(recap.by_recipe).length > 0 && (
        <>
          <h3>By recipe</h3>
          <ul className="exp-list">
            {Object.entries(recap.by_recipe).map(([name, row]) => (
              <li key={name}>
                <strong>{name}</strong> · {row.sessions ?? 0} sessions ·{" "}
                {Number(row.flow_minutes ?? 0).toFixed(1)} flow min
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="dim">
        Also: <code>nfa report</code> / <code>nfa report --json --days {days}</code>
      </p>
    </section>
  );
}
