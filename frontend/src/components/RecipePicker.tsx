const RECIPES = [
  { id: "study", label: "Study" },
  { id: "create", label: "Create" },
  { id: "rest", label: "Rest" },
  { id: "social", label: "Social" },
] as const;

type Props = {
  value: string;
  onChange: (recipe: string) => void;
  disabled?: boolean;
};

export function RecipePicker({ value, onChange, disabled }: Props) {
  return (
    <div className="recipe-picker" role="group" aria-label="Environment recipe">
      {RECIPES.map((r) => (
        <button
          key={r.id}
          type="button"
          className={value === r.id ? "target-btn recipe active" : "target-btn secondary recipe"}
          onClick={() => onChange(r.id)}
          disabled={disabled}
          aria-pressed={value === r.id}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
