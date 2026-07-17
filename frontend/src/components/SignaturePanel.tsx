import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Sig = {
  best_hours?: number[];
  best_recipes?: string[];
  avg_peak_engagement?: number;
  avg_flow_minutes?: number;
  notes?: string[];
  disclaimer?: string;
  sessions_considered?: number;
};

export function SignaturePanel() {
  const [sig, setSig] = useState<Sig | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/signature`)
      .then((r) => r.json())
      .then((d) => setSig(d.signature || null))
      .catch(() => setSig(null));
  }, []);

  if (!sig) {
    return <p className="explanation">Personal signature loading…</p>;
  }

  return (
    <section className="insights" aria-labelledby="sig-title">
      <h2 id="sig-title">Your flow signature</h2>
      <p className="dim">{sig.disclaimer}</p>
      <ul className="insight-stats">
        <li>
          <strong>Sessions</strong> {sig.sessions_considered ?? 0}
        </li>
        <li>
          <strong>Avg peak engagement</strong>{" "}
          {Number(sig.avg_peak_engagement ?? 0).toFixed(2)}
        </li>
        <li>
          <strong>Avg flow-ish min</strong>{" "}
          {Number(sig.avg_flow_minutes ?? 0).toFixed(1)}
        </li>
        <li>
          <strong>Best hours</strong>{" "}
          {(sig.best_hours || []).map((h) => `${h}:00`).join(", ") || "—"}
        </li>
        <li>
          <strong>Best recipes</strong>{" "}
          {(sig.best_recipes || []).join(", ") || "—"}
        </li>
      </ul>
      <ul className="exp-list">
        {(sig.notes || []).map((n, i) => (
          <li key={i}>{n}</li>
        ))}
      </ul>
    </section>
  );
}
