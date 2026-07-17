import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Trust = {
  trust_score?: number;
  undo_rate?: number;
  helpful?: number;
  unhelpful?: number;
  never?: number;
  interpretation?: string;
};

export function TrustPanel() {
  const [trust, setTrust] = useState<Trust | null>(null);
  const [iot, setIot] = useState<string>("—");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/trust`)
      .then((r) => r.json())
      .then((d) => {
        setTrust(d.trust || null);
        setIot(d.iot?.mode || "—");
      })
      .catch(() => setError("Could not load trust metrics"));
  }, []);

  if (error) return <p className="explanation">{error}</p>;
  if (!trust) return <p className="explanation">Loading trust…</p>;

  const score = Number(trust.trust_score ?? 0);

  return (
    <section className="insights" aria-labelledby="trust-title">
      <h2 id="trust-title">Trust</h2>
      <p className="explanation">{trust.interpretation}</p>
      <ul className="insight-stats">
        <li>
          <strong>Trust score</strong> {score.toFixed(2)}
        </li>
        <li>
          <strong>Undo rate</strong> {Number(trust.undo_rate ?? 0).toFixed(2)}
        </li>
        <li>
          <strong>Helpful / Not / Never</strong> {trust.helpful ?? 0} /{" "}
          {trust.unhelpful ?? 0} / {trust.never ?? 0}
        </li>
        <li>
          <strong>IoT mode</strong> {iot}
        </li>
      </ul>
      <div
        className="bar"
        style={{ maxWidth: 360, marginTop: "0.75rem" }}
        aria-label={`Trust ${score}`}
      >
        <div style={{ width: `${Math.round(score * 100)}%` }} />
      </div>
      <p className="dim">
        Local metric from your undos and Why? feedback — not a medical score.
      </p>
    </section>
  );
}
