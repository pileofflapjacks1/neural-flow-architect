type Props = {
  text: string;
  because?: Array<Record<string, unknown>>;
  toolId?: string;
  onClose: () => void;
  onNever?: () => void;
  onAlways?: () => void;
};

export function ExplainDrawer({
  text,
  because = [],
  toolId,
  onClose,
  onNever,
  onAlways,
}: Props) {
  return (
    <div className="drawer-backdrop" role="presentation" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="explain-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="explain-title">Why did this happen?</h2>
        {toolId && <p className="meta-line">Action: {toolId}</p>}
        <p>{text}</p>
        {because.length > 0 && (
          <ul>
            {because.map((c, i) => (
              <li key={i}>
                {String(c.signal ?? c.reason ?? "signal")}:{" "}
                {String(c.value ?? c.trend ?? "")}
              </li>
            ))}
          </ul>
        )}
        <div className="action-row">
          {onAlways && (
            <button type="button" className="target-btn secondary" onClick={onAlways}>
              Allow always
            </button>
          )}
          {onNever && (
            <button type="button" className="target-btn secondary" onClick={onNever}>
              Never
            </button>
          )}
          <button type="button" className="target-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </aside>
    </div>
  );
}
