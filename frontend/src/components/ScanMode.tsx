import { useEffect, useState } from "react";

export type ScanAction = {
  id: string;
  label: string;
  run: () => void;
};

type Props = {
  enabled: boolean;
  intervalMs?: number;
  actions: ScanAction[];
};

/**
 * Sequential highlight scanning for zero-precision input.
 * Space / Enter selects the highlighted action (dwell alternative).
 */
export function ScanMode({ enabled, intervalMs = 1400, actions }: Props) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!enabled || actions.length === 0) return;
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % actions.length);
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [enabled, intervalMs, actions.length]);

  useEffect(() => {
    if (!enabled) return;
    const onKey = (ev: KeyboardEvent) => {
      if (ev.code === "Space" || ev.code === "Enter") {
        const t = ev.target as HTMLElement | null;
        if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
        ev.preventDefault();
        actions[index]?.run();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled, index, actions]);

  if (!enabled || actions.length === 0) return null;

  return (
    <section className="scan-mode" aria-label="Scan mode controls">
      <p className="meta-line">
        Scan mode — Space/Enter selects highlighted action
      </p>
      <div className="action-row">
        {actions.map((a, i) => (
          <button
            key={a.id}
            type="button"
            className={
              i === index ? "target-btn target-xl scan-active" : "target-btn secondary"
            }
            onClick={() => a.run()}
            aria-current={i === index ? "true" : undefined}
          >
            {a.label}
          </button>
        ))}
      </div>
    </section>
  );
}
