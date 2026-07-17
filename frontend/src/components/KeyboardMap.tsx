import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type KeyEntry = {
  code?: string;
  key?: string;
  intent?: string;
  label?: string;
};

type Props = {
  /** Prefer entries from a11y payload when present */
  entries?: KeyEntry[] | null;
  compact?: boolean;
};

export function KeyboardMap({ entries: initial, compact = false }: Props) {
  const [entries, setEntries] = useState<KeyEntry[]>(initial || []);

  useEffect(() => {
    if (initial && initial.length > 0) {
      setEntries(initial);
      return;
    }
    fetch(`${API_BASE}/keymap`)
      .then((r) => r.json())
      .then((d) => setEntries(d.keys || []))
      .catch(() => setEntries([]));
  }, [initial]);

  if (entries.length === 0) {
    return (
      <p className="dim">
        Keyboard map loading… Defaults: P pause · F resume · U undo · R rest · S
        start · X stop · Y/N labels · 1–4 recipes · / why
      </p>
    );
  }

  return (
    <section
      className="keyboard-map"
      aria-labelledby={compact ? undefined : "keymap-title"}
    >
      {!compact && <h3 id="keymap-title">Keyboard map</h3>}
      <p className="dim">
        Active when focus is not in a text field. Disabled while Scan mode is on
        (use Space/Enter instead).
      </p>
      <table className="keymap-table">
        <caption className="sr-only">Keyboard shortcuts to Architect intents</caption>
        <thead>
          <tr>
            <th scope="col">Key</th>
            <th scope="col">Action</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.code || e.key}>
              <td>
                <kbd>{e.key}</kbd>
              </td>
              <td>{e.label || e.intent}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
