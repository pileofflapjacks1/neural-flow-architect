import { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type HybridMl = {
  enabled?: boolean;
  trained?: boolean;
  n_samples?: number;
  n_positive?: number;
  model?: string;
  message?: string;
};

type Props = {
  /** When learning message changes after a label, refresh status */
  learningHint?: string | null;
};

export function HybridMlPanel({ learningHint }: Props) {
  const [ml, setMl] = useState<HybridMl | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetch(`${API_BASE}/flow/ml`)
      .then((r) => r.json())
      .then((d) => setMl(d.hybrid_ml || null))
      .catch(() => setError("Could not load hybrid ML status"));
  }, []);

  useEffect(() => {
    load();
  }, [load, learningHint]);

  if (error) return <p className="explanation">{error}</p>;
  if (!ml) return <p className="explanation">Loading hybrid ML status…</p>;

  const trained = !!ml.trained;
  const enabled = ml.enabled !== false;
  const samples = Number(ml.n_samples ?? 0);
  const positive = Number(ml.n_positive ?? 0);
  const negative = Math.max(0, samples - positive);
  const need = 8;
  const progress = Math.min(100, Math.round((samples / need) * 100));

  return (
    <section className="insights hybrid-ml-panel" aria-labelledby="hybrid-ml-title">
      <h2 id="hybrid-ml-title">Hybrid flow ML</h2>
      <p className="dim">
        Optional sklearn calibrator trained only on your local “Felt in flow”
        labels — never raw neural samples. Blends into engagement when both
        classes have enough labels.
      </p>

      <ul className="insight-stats">
        <li>
          <strong>Status</strong>{" "}
          {!enabled
            ? "Disabled"
            : trained
              ? "Active (blending)"
              : "Rules only (learning)"}
        </li>
        <li>
          <strong>Model</strong> {ml.model || "none"}
        </li>
        <li>
          <strong>Samples</strong> {samples}{" "}
          <span className="dim">
            ({positive} in-flow · {negative} not)
          </span>
        </li>
      </ul>

      {!trained && enabled && (
        <>
          <p className="meta-line">
            Progress toward training (≥{need} samples, both classes)
          </p>
          <div
            className="bar"
            style={{ maxWidth: 360 }}
            aria-label={`Label progress ${progress}%`}
          >
            <div style={{ width: `${progress}%` }} />
          </div>
        </>
      )}

      {trained && (
        <div
          className="bar"
          style={{ maxWidth: 360 }}
          aria-label="Hybrid ML trained"
        >
          <div style={{ width: "100%", background: "var(--good)" }} />
        </div>
      )}

      <p className="explanation" role="status">
        {ml.message || "—"}
      </p>

      <div className="action-row">
        <button type="button" className="target-btn secondary" onClick={() => load()}>
          Refresh status
        </button>
      </div>
      <p className="dim">
        During a live session, use <strong>Felt in flow</strong> /{" "}
        <strong>Not really</strong> to add samples. API:{" "}
        <code>GET /flow/ml</code>
      </p>
    </section>
  );
}
