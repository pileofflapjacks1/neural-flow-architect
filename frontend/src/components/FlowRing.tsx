type Props = {
  state: string;
  engagement: number;
  minutes: number;
};

export function FlowRing({ state, engagement, minutes }: Props) {
  const pct = Math.round(engagement * 100);
  return (
    <section className="flow-ring" aria-label="Estimated flow state">
      <div
        className="ring"
        style={{ ["--pct" as string]: String(pct) }}
        role="img"
        aria-label={`Engagement ${pct} percent, state ${state}`}
      >
        <div className="ring-inner">
          <p className="ring-state">{state.replace("_", " ")}</p>
          <p className="ring-score">{engagement.toFixed(2)}</p>
          <p className="ring-meta">{minutes} min in state</p>
        </div>
      </div>
      <div className="dims" aria-label="Flow dimensions">
        <div className="dim">
          <span>Engagement</span>
          <div className="bar">
            <div style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>
    </section>
  );
}
