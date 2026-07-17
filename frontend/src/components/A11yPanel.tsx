import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type A11y = {
  ui_scale: number;
  high_contrast: boolean;
  reduced_motion: boolean;
  dwell_ms: number;
  keyboard_enabled: boolean;
  voice_command_bar: boolean;
  auto_start_on_preset: boolean;
  quiet_hours_enabled?: boolean;
  quiet_hours_start?: number;
  quiet_hours_end?: number;
  suggest_recipe_from_app?: boolean;
};

export function A11yPanel() {
  const [a11y, setA11y] = useState<A11y | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = () => {
    fetch(`${API_BASE}/a11y`)
      .then((r) => r.json())
      .then((d) => setA11y(d.a11y))
      .catch(() => setMsg("Could not load accessibility settings"));
  };

  useEffect(() => {
    load();
  }, []);

  const save = async (patch: Partial<A11y>) => {
    const res = await fetch(`${API_BASE}/a11y`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    const data = await res.json();
    if (data.a11y) setA11y(data.a11y);
    setMsg("Saved");
  };

  const exportProfile = async () => {
    const res = await fetch(`${API_BASE}/profile/export`);
    const data = await res.json();
    if (data.bundle) {
      const blob = new Blob([JSON.stringify(data.bundle, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "nfa-profile-backup.json";
      a.click();
      URL.revokeObjectURL(url);
      setMsg("Profile exported (preferences only — no raw neural data)");
    }
  };

  if (!a11y) {
    return <p className="explanation">{msg || "Loading accessibility…"}</p>;
  }

  return (
    <section className="a11y-panel" aria-labelledby="a11y-title">
      <h2 id="a11y-title">Accessibility</h2>
      <p className="dim">
        Tuned for low-precision control and long sessions. Changes save on this
        device.
      </p>
      <label className="a11y-row">
        UI scale ({a11y.ui_scale.toFixed(2)})
        <input
          type="range"
          min={1}
          max={1.75}
          step={0.05}
          value={a11y.ui_scale}
          onChange={(e) => save({ ui_scale: Number(e.target.value) })}
        />
      </label>
      <label className="a11y-row">
        <input
          type="checkbox"
          checked={a11y.high_contrast}
          onChange={(e) => save({ high_contrast: e.target.checked })}
        />
        High contrast
      </label>
      <label className="a11y-row">
        <input
          type="checkbox"
          checked={a11y.reduced_motion}
          onChange={(e) => save({ reduced_motion: e.target.checked })}
        />
        Reduced motion
      </label>
      <label className="a11y-row">
        <input
          type="checkbox"
          checked={a11y.keyboard_enabled}
          onChange={(e) => save({ keyboard_enabled: e.target.checked })}
        />
        Keyboard shortcuts
      </label>
      <label className="a11y-row">
        <input
          type="checkbox"
          checked={a11y.voice_command_bar}
          onChange={(e) => save({ voice_command_bar: e.target.checked })}
        />
        Command bar (voice/type)
      </label>
      <label className="a11y-row">
        Dwell ms
        <input
          type="number"
          min={400}
          max={3000}
          step={100}
          value={a11y.dwell_ms}
          onChange={(e) => save({ dwell_ms: Number(e.target.value) })}
        />
      </label>
      <label className="a11y-row">
        <input
          type="checkbox"
          checked={!!a11y.quiet_hours_enabled}
          onChange={(e) => save({ quiet_hours_enabled: e.target.checked })}
        />
        Quiet hours (soften protect at night)
      </label>
      <label className="a11y-row">
        Quiet start hour
        <input
          type="number"
          min={0}
          max={23}
          value={a11y.quiet_hours_start ?? 22}
          onChange={(e) => save({ quiet_hours_start: Number(e.target.value) })}
        />
      </label>
      <label className="a11y-row">
        Quiet end hour
        <input
          type="number"
          min={0}
          max={23}
          value={a11y.quiet_hours_end ?? 7}
          onChange={(e) => save({ quiet_hours_end: Number(e.target.value) })}
        />
      </label>
      <label className="a11y-row">
        <input
          type="checkbox"
          checked={a11y.suggest_recipe_from_app !== false}
          onChange={(e) => save({ suggest_recipe_from_app: e.target.checked })}
        />
        Suggest recipe from active app
      </label>
      <div className="action-row">
        <button type="button" className="target-btn secondary" onClick={exportProfile}>
          Export profile backup
        </button>
      </div>
      {msg && (
        <p className="meta-line" role="status">
          {msg}
        </p>
      )}
    </section>
  );
}
