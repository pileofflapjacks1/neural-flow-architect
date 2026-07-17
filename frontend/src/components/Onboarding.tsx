import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type OnboardingData = {
  completed: boolean;
  current_step: string;
  steps: string[];
  copy: Record<string, { title: string; body: string }>;
};

type Props = {
  onDone: () => void;
};

export function Onboarding({ onDone }: Props) {
  const [data, setData] = useState<OnboardingData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    fetch(`${API_BASE}/onboarding`)
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        if (d.completed) onDone();
      })
      .catch(() => setError("Could not load onboarding — is nfa start running?"));
  };

  useEffect(() => {
    load();
  }, []);

  const advance = async (complete = false) => {
    const res = await fetch(`${API_BASE}/onboarding`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ complete }),
    });
    const d = await res.json();
    if (d.onboarding) setData(d.onboarding);
    if (d.onboarding?.completed || complete) onDone();
  };

  if (error) {
    return (
      <div className="banner warn" role="alert">
        {error}
      </div>
    );
  }
  if (!data || data.completed) return null;

  const step = data.current_step;
  const copy = data.copy?.[step] ?? {
    title: step,
    body: "Continue when ready.",
  };

  return (
    <section className="onboarding" aria-labelledby="onboard-title">
      <p className="meta-line">
        Setup {data.steps.indexOf(step) + 1} / {data.steps.length}
      </p>
      <h2 id="onboard-title">{copy.title}</h2>
      <p className="explanation">{copy.body}</p>
      <div className="action-row">
        <button type="button" className="target-btn" onClick={() => advance(false)}>
          Continue
        </button>
        <button
          type="button"
          className="target-btn secondary"
          onClick={() => advance(true)}
        >
          Skip to app
        </button>
      </div>
    </section>
  );
}
