import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Scoreboard = {
  sessions?: number;
  score?: number | null;
  interpretation?: string;
  totals?: {
    actions?: number;
    undos?: number;
    block_reviews?: number;
    helpful_blocks?: number;
    architect_noisy_reviews?: number;
  };
  by_recipe?: Record<
    string,
    { sessions?: number; flow_minutes?: number; helpful_review_rate?: number }
  >;
  trust?: { trust_score?: number };
};

export function ScoreboardPanel() {
  const [sb, setSb] = useState<Scoreboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/scoreboard`)
      .then((r) => r.json())
      .then((d) => setSb(d.scoreboard || null))
      .catch(() => setError("Could not load policy scoreboard"));
  }, []);

  if (error) return <p className="explanation">{error}</p>;
  if (!sb) return <p className="explanation">Loading scoreboard…</p>;

  const score = sb.score;
  const pct = score == null ? 0 : Math.round(Number(score));

  return (
    <section className="insights" aria-labelledby="scoreboard-title">
      <h2 id="scoreboard-title">Policy scoreboard</h2>
      <p className="explanation">{sb.interpretation}</p>
      <ul className="insight-stats">
        <li>
          <strong>Policy score</strong>{" "}
          {score == null ? "—" : Number(score).toFixed(1)} / 100
        </li>
        <li>
          <strong>Sessions</strong> {sb.sessions ?? 0}
        </li>
        <li>
          <strong>Actions / undos</strong> {sb.totals?.actions ?? 0} /{" "}
          {sb.totals?.undos ?? 0}
        </li>
        <li>
          <strong>Helpful blocks</strong> {sb.totals?.helpful_blocks ?? 0} /{" "}
          {sb.totals?.block_reviews ?? 0} reviews
        </li>
      </ul>
      <div
        className="bar"
        style={{ maxWidth: 360, marginTop: "0.75rem" }}
        aria-label={`Policy score ${pct}`}
      >
        <div style={{ width: `${pct}%` }} />
      </div>
      {sb.by_recipe && Object.keys(sb.by_recipe).length > 0 && (
        <>
          <h3>By recipe</h3>
          <ul className="exp-list">
            {Object.entries(sb.by_recipe).map(([name, row]) => (
              <li key={name}>
                <strong>{name}</strong> · {row.sessions ?? 0} sessions ·{" "}
                {Number(row.flow_minutes ?? 0).toFixed(1)} flow min · helpful{" "}
                {Math.round((row.helpful_review_rate ?? 0) * 100)}%
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="dim">
        Local composite from undos, block reviews, and trust — not a clinical
        score. Also available via <code>nfa report --json</code>.
      </p>
    </section>
  );
}
