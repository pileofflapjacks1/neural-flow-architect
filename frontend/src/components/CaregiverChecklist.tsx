import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Item = { id: string; label: string; done: boolean };

export function CaregiverChecklist() {
  const [items, setItems] = useState<Item[]>([]);
  const [completed, setCompleted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(6);

  const load = () => {
    fetch(`${API_BASE}/caregiver`)
      .then((r) => r.json())
      .then((d) => {
        setItems(d.checklist?.items || []);
        setCompleted(!!d.checklist?.completed);
        setProgress(d.checklist?.progress || 0);
        setTotal(d.checklist?.total || 6);
      })
      .catch(() => setItems([]));
  };

  useEffect(() => {
    load();
  }, []);

  const toggle = async (id: string, done: boolean) => {
    await fetch(`${API_BASE}/caregiver`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: id, done }),
    });
    load();
  };

  return (
    <section className="insights" aria-labelledby="caregiver-title">
      <h2 id="caregiver-title">Caregiver checklist</h2>
      <p className="explanation">
        Setup once, then step back. Progress {progress}/{total}
        {completed ? " — complete!" : ""}
      </p>
      <ul className="caregiver-list">
        {items.map((it) => (
          <li key={it.id}>
            <label className="a11y-row">
              <input
                type="checkbox"
                checked={it.done}
                onChange={(e) => toggle(it.id, e.target.checked)}
              />
              {it.label}
            </label>
          </li>
        ))}
      </ul>
      <p className="dim">
        Helpers should not take permanent control of Pause/Undo. See
        docs/ux/CAREGIVER_SETUP.md.
      </p>
    </section>
  );
}
