import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Preset = {
  id: string;
  label: string;
  description: string;
};

type Props = {
  activeId?: string | null;
  onApplied?: () => void;
};

export function PresetPicker({ activeId, onApplied }: Props) {
  const [presets, setPresets] = useState<Preset[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/presets`)
      .then((r) => r.json())
      .then((d) => setPresets(d.presets || []))
      .catch(() => setPresets([]));
  }, []);

  const apply = async (id: string) => {
    await fetch(`${API_BASE}/presets/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset_id: id }),
    });
    onApplied?.();
  };

  if (!presets.length) return null;

  return (
    <section className="preset-picker" aria-label="Daily presets">
      <p className="meta-line">Daily preset</p>
      <div className="action-row">
        {presets.map((p) => (
          <button
            key={p.id}
            type="button"
            title={p.description}
            className={
              activeId === p.id
                ? "target-btn recipe active"
                : "target-btn secondary recipe"
            }
            onClick={() => apply(p.id)}
            aria-pressed={activeId === p.id}
          >
            {p.label}
          </button>
        ))}
      </div>
    </section>
  );
}
