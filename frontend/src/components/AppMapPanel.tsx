import { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

const CATEGORIES = ["study", "create", "social", "system", "unknown"] as const;

type OsFocus = {
  enabled?: boolean;
  force_dry_run?: boolean;
  active?: boolean;
  mode?: string;
  platform?: string;
  history?: string[];
};

export function AppMapPanel() {
  const [map, setMap] = useState<Record<string, string>>({});
  const [categories, setCategories] = useState<string[]>([...CATEGORIES]);
  const [key, setKey] = useState("");
  const [category, setCategory] = useState<string>("study");
  const [osFocus, setOsFocus] = useState<OsFocus | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const loadMap = useCallback(() => {
    fetch(`${API_BASE}/app_map`)
      .then((r) => r.json())
      .then((d) => {
        setMap(d.map || {});
        if (Array.isArray(d.categories)) setCategories(d.categories);
      })
      .catch(() => setMsg("Could not load app map"));
  }, []);

  const loadOsFocus = useCallback(() => {
    fetch(`${API_BASE}/os_focus`)
      .then((r) => r.json())
      .then((d) => setOsFocus(d.os_focus || null))
      .catch(() => setOsFocus(null));
  }, []);

  useEffect(() => {
    loadMap();
    loadOsFocus();
  }, [loadMap, loadOsFocus]);

  const saveEntry = async () => {
    const k = key.trim();
    if (!k) return;
    setMsg(null);
    try {
      const res = await fetch(`${API_BASE}/app_map`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: k, category }),
      });
      const d = await res.json();
      if (d.map) setMap(d.map);
      if (Array.isArray(d.categories)) setCategories(d.categories);
      setKey("");
      setMsg(`Mapped “${k}” → ${category}`);
    } catch {
      setMsg("Save failed");
    }
  };

  const removeEntry = async (k: string) => {
    setMsg(null);
    try {
      await fetch(`${API_BASE}/app_map/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: k }),
      });
      loadMap();
      setMsg(`Removed “${k}”`);
    } catch {
      setMsg("Remove failed");
    }
  };

  const setFocus = async (patch: {
    enabled?: boolean;
    force_dry_run?: boolean;
  }) => {
    try {
      const res = await fetch(`${API_BASE}/os_focus`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      const d = await res.json();
      setOsFocus(d.os_focus || null);
    } catch {
      setMsg("OS Focus update failed");
    }
  };

  const entries = Object.entries(map).sort(([a], [b]) => a.localeCompare(b));

  return (
    <section className="insights" aria-labelledby="appmap-title">
      <h2 id="appmap-title">App → category map</h2>
      <p className="dim">
        Substring match on the frontmost app name (case-insensitive). Used to
        soft-tune recipes when active-app detection is on. Stored locally.
      </p>

      <div className="action-row" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
        <label className="field-label">
          App substring
          <input
            type="text"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="e.g. vscode"
            aria-label="App name substring"
          />
        </label>
        <label className="field-label">
          Category
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            aria-label="Category"
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="target-btn" onClick={() => saveEntry()}>
          Add / update
        </button>
      </div>
      {msg && (
        <p className="meta-line" role="status">
          {msg}
        </p>
      )}

      <ul className="app-map-list exp-list">
        {entries.length === 0 && <li>No mappings yet</li>}
        {entries.map(([k, cat]) => (
          <li key={k} className="app-map-row">
            <span>
              <strong>{k}</strong> → {cat}
            </span>
            <button
              type="button"
              className="target-btn secondary"
              onClick={() => removeEntry(k)}
              aria-label={`Remove ${k}`}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>

      <h3 id="osfocus-title">OS Focus / DND</h3>
      <p className="dim">
        Best-effort companion when protect tools fire. Defaults to dry-run (no
        system change). macOS: create Shortcuts named{" "}
        <code>NFA Focus On</code> / <code>NFA Focus Off</code>.
      </p>
      {osFocus && (
        <ul className="insight-stats">
          <li>
            <strong>Mode</strong> {osFocus.mode ?? "—"}
          </li>
          <li>
            <strong>Platform</strong> {osFocus.platform ?? "—"}
          </li>
          <li>
            <strong>Active</strong> {osFocus.active ? "yes" : "no"}
          </li>
        </ul>
      )}
      <div className="action-row">
        <button
          type="button"
          className={
            osFocus?.enabled ? "target-btn recipe active" : "target-btn secondary"
          }
          onClick={() => setFocus({ enabled: !osFocus?.enabled })}
          aria-pressed={!!osFocus?.enabled}
        >
          Integration {osFocus?.enabled ? "on" : "off"}
        </button>
        <button
          type="button"
          className={
            osFocus?.force_dry_run !== false
              ? "target-btn recipe active"
              : "target-btn secondary"
          }
          onClick={() =>
            setFocus({ force_dry_run: osFocus?.force_dry_run === false })
          }
          aria-pressed={osFocus?.force_dry_run !== false}
        >
          Dry-run {osFocus?.force_dry_run !== false ? "on" : "off"}
        </button>
      </div>
    </section>
  );
}
