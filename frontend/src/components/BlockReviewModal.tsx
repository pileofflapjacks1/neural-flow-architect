type Props = {
  prompt?: string;
  flowMinutes?: number;
  actions?: number;
  undos?: number;
  onSubmit: (payload: {
    helpful_block: boolean;
    architect_helpful: boolean | null;
    note: string;
  }) => void;
  onSkip: () => void;
};

export function BlockReviewModal({
  prompt = "Was this work block helpful?",
  flowMinutes,
  actions,
  undos,
  onSubmit,
  onSkip,
}: Props) {
  return (
    <div className="drawer-backdrop" role="presentation">
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="block-review-title"
      >
        <h2 id="block-review-title">End of block</h2>
        <p className="explanation">{prompt}</p>
        {(flowMinutes != null || actions != null) && (
          <p className="meta-line">
            {flowMinutes != null ? `~${Number(flowMinutes).toFixed(1)} flow-ish min` : ""}
            {actions != null ? ` · ${actions} actions` : ""}
            {undos != null ? ` · ${undos} undos` : ""}
          </p>
        )}
        <div className="action-row">
          <button
            type="button"
            className="target-btn target-xl"
            onClick={() =>
              onSubmit({ helpful_block: true, architect_helpful: true, note: "" })
            }
          >
            Yes, helpful
          </button>
          <button
            type="button"
            className="target-btn secondary target-xl"
            onClick={() =>
              onSubmit({ helpful_block: false, architect_helpful: false, note: "" })
            }
          >
            Not really
          </button>
        </div>
        <div className="action-row" style={{ marginTop: "0.75rem" }}>
          <button
            type="button"
            className="target-btn secondary"
            onClick={() =>
              onSubmit({ helpful_block: true, architect_helpful: false, note: "" })
            }
          >
            Block OK, co-pilot noisy
          </button>
          <button type="button" className="target-btn secondary" onClick={onSkip}>
            Skip
          </button>
        </div>
      </aside>
    </div>
  );
}
