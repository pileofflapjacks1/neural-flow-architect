type Props = {
  paused: boolean;
  onToggle: () => void;
};

export function OverrideBar({ paused, onToggle }: Props) {
  return (
    <button
      type="button"
      className={`target-btn override ${paused ? "paused" : ""}`}
      onClick={onToggle}
      aria-pressed={paused}
    >
      {paused ? "Resume Architect" : "Pause Architect"}
    </button>
  );
}
