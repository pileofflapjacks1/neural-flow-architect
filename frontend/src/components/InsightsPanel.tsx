type Props = {
  session: Record<string, unknown> | null;
};

export function InsightsPanel({ session }: Props) {
  if (!session) {
    return (
      <section className="insights">
        <h2>Flow Insights</h2>
        <p className="explanation">
          No session data yet. Start a live session, then return here for a
          summary. Labels (“I felt in flow”) improve personalization later.
        </p>
      </section>
    );
  }

  const stateMinutes = (session.state_minutes as Record<string, number>) || {};
  const labels = (session.labels as Array<Record<string, unknown>>) || [];
  const explanations = (session.explanations as string[]) || [];

  return (
    <section className="insights">
      <h2>Flow Insights</h2>
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
        {Object.entries(stateMinutes).map(([k, v]) => (
          <li key={k}>
            {k}: {Number(v).toFixed(2)} min
          </li>
        ))}
        {Object.keys(stateMinutes).length === 0 && <li>Collecting…</li>}
      </ul>
      <h3>Self-report labels</h3>
      <ul>
        {labels.length === 0 && <li>None yet</li>}
        {labels.map((lab, i) => (
          <li key={i}>
            {lab.felt_in_flow ? "Felt in flow" : "Not really"}
            {lab.state_at_label ? ` @ ${String(lab.state_at_label)}` : ""}
          </li>
        ))}
      </ul>
      <h3>Recent explanations</h3>
      <ul className="exp-list">
        {explanations.slice(-5).map((e, i) => (
          <li key={i}>{e}</li>
        ))}
        {explanations.length === 0 && <li>None yet</li>}
      </ul>
      <p className="dim">
        Summaries stay on this device. Raw neural samples are not stored by
        default.
      </p>
    </section>
  );
}
