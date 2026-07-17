type Props = {
  text: string;
  onClose: () => void;
};

export function ExplainDrawer({ text, onClose }: Props) {
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
        <p>{text}</p>
        <ul>
          <li>engagement rising</li>
          <li>state: flow</li>
          <li>quality usable</li>
        </ul>
        <div className="action-row">
          <button type="button" className="target-btn secondary">
            Allow always
          </button>
          <button type="button" className="target-btn secondary">
            Never
          </button>
          <button type="button" className="target-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </aside>
    </div>
  );
}
