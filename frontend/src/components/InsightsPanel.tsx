import { useEffect, useState } from "react";
import { TrustPanel } from "./TrustPanel";
import { WeeklyRecapPanel } from "./WeeklyRecapPanel";
import { ScoreboardPanel } from "./ScoreboardPanel";
import { TimelinePanel } from "./TimelinePanel";
import { AppMapPanel } from "./AppMapPanel";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Props = {
  session: Record<string, unknown> | null;
  context?: Record<string, unknown> | null;
  quietHours?: Record<string, unknown> | null;
  recipeSuggestion?: Record<string, unknown> | null;
  auditRecent?: Array<Record<string, unknown>>;
  onAcceptRecipe?: () => void;
};

export function InsightsPanel({
  session,
  context,
  quietHours,
  recipeSuggestion,
  auditRecent = [],
  onAcceptRecipe,
}: Props) {
  const [events, setEvents] = useState<Array<Record<string, unknown>>>(auditRecent);

  useEffect(() => {
    setEvents(auditRecent);
  }, [auditRecent]);

  useEffect(() => {
    fetch(`${API_BASE}/audit?limit=15`)
      .then((r) => r.json())
      .then((d) => setEvents(d.events || []))
      .catch(() => {
        /* optional */
      });
  }, [session?.session_id]);

  return (
    <section className="insights">
      <WeeklyRecapPanel />
      <TrustPanel />
      <ScoreboardPanel />
      <TimelinePanel />

      {recipeSuggestion && (
        <div className="banner info" role="status">
          <p>{String(recipeSuggestion.message || "Recipe suggestion")}</p>
          {onAcceptRecipe && (
            <button type="button" className="target-btn" onClick={onAcceptRecipe}>
              Switch to {String(recipeSuggestion.suggested_recipe)}
            </button>
          )}
        </div>
      )}

      {context && (
        <>
          <h3>Context</h3>
          <ul className="insight-stats">
            <li>
              <strong>App</strong> {String(context.active_app || "—")}
            </li>
            <li>
              <strong>Category</strong> {String(context.app_category || "—")}
            </li>
            <li>
              <strong>Time</strong> {String(context.time_of_day || "—")}
            </li>
            <li>
              <strong>Recipe</strong> {String(context.recipe || "—")}
            </li>
          </ul>
        </>
      )}

      {quietHours && (
        <>
          <h3>Quiet hours</h3>
          <p className="meta-line">
            {quietHours.enabled
              ? `${quietHours.start_hour}:00–${quietHours.end_hour}:00`
              : "Off"}
            {quietHours.active_now ? " · active now" : ""}
          </p>
        </>
      )}

      <h2>Flow Insights</h2>
      {!session ? (
        <p className="explanation">
          No session data yet. Start a live session for a summary. Labels and
          Why? feedback improve personalization.
        </p>
      ) : (
        <>
          <p className="meta-line">
            Session {String(session.session_id ?? "").slice(0, 8)}… · adapter{" "}
            {String(session.adapter ?? "—")}
          </p>
          <ul className="insight-stats">
            <li>
              <strong>Peak engagement</strong>{" "}
              {Number(session.peak_engagement ?? 0).toFixed(2)}
            </li>
            <li>
              <strong>Flow-ish minutes</strong>{" "}
              {Number(session.flow_minutes ?? 0).toFixed(2)}
            </li>
            <li>
              <strong>Actions</strong> {String(session.actions_count ?? 0)} ·{" "}
              <strong>Undos</strong> {String(session.undos_count ?? 0)}
            </li>
          </ul>
          <h3>Time by state</h3>
          <ul>
            {Object.entries(
              (session.state_minutes as Record<string, number>) || {}
            ).map(([k, v]) => (
              <li key={k}>
                {k}: {Number(v).toFixed(2)} min
              </li>
            ))}
          </ul>
        </>
      )}

      <h3>Recent audit</h3>
      <ul className="exp-list">
        {events.length === 0 && <li>No events yet</li>}
        {events
          .slice()
          .reverse()
          .slice(0, 12)
          .map((e, i) => (
            <li key={i}>
              <span className="dim">{String(e.event_type)}</span> —{" "}
              {String(e.message)}
            </li>
          ))}
      </ul>
      <p className="dim">
        Audit and summaries stay on this device. Raw neural samples are not
        logged.
      </p>

      <AppMapPanel />
    </section>
  );
}
